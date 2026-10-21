"""Nebius Token Factory client with Nemotron model routing and cost accounting.

Every model call in ProofGate goes through here. Each Nemotron size has one job:

    omni  - Nemotron 3 Nano Omni: reads screenshots and terminal captures attached to a report
    nano  - Nemotron 3 Nano: fast, cheap structured extraction (claims as JSON)
    super - Nemotron 3 Super: long-context reasoning over the real source code
    ultra - Nemotron 3 Ultra: final adjudication and the adversarial challenge
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from .config import get_settings
from .schema import ModelCall

Role = str  # "nano" | "omni" | "super" | "ultra"

# Substrings used to pick the right id out of GET /v1/models, most specific first.
ROLE_HINTS: dict[Role, tuple[str, ...]] = {
    "omni": ("nemotron-3-nano-omni", "nano-omni", "nemotron-nano-vl", "nano-vl"),
    "nano": ("nemotron-3-nano-30b", "nemotron-3-nano", "nemotron-nano"),
    "super": ("nemotron-3-super", "nemotron-super"),
    "ultra": ("nemotron-3-ultra", "nemotron-ultra"),
}

# Fallback ids if the model list is unreachable (as listed by public Token Factory catalogs).
DEFAULT_IDS: dict[Role, str] = {
    "omni": "nvidia/Nemotron-3-Nano-Omni",
    "nano": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    "super": "nvidia/nemotron-3-super-120b-a12b",
    "ultra": "nvidia/Nemotron-3-Ultra-550b-a55b",
}

# USD per 1M tokens (input, output) used for the live cost counter. These are estimates;
# set PG_PRICES='{"nano": [0.06, 0.24], ...}' to match the current Token Factory price list.
PRICES: dict[Role, tuple[float, float]] = {
    "omni": (0.10, 0.40),
    "nano": (0.06, 0.24),
    "super": (0.30, 0.90),
    "ultra": (1.00, 3.00),
}
if _override := os.environ.get("PG_PRICES"):
    PRICES.update({k: (float(v[0]), float(v[1])) for k, v in json.loads(_override).items()})


class LLMUnavailable(RuntimeError):
    pass


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Budget:
    limit_usd: float
    spent_usd: float = 0.0

    def charge(self, amount: float) -> None:
        self.spent_usd += amount
        if self.spent_usd > self.limit_usd:
            raise BudgetExceeded(f"spent ${self.spent_usd:.4f} > cap ${self.limit_usd:.2f}")


_JSON_BLOCK = re.compile(r"\{.*\}", re.S)
_THINK = re.compile(r"<think>.*?</think>", re.S)


def _parse_json(text: str) -> Any:
    text = _THINK.sub("", text).strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("\n") + 1 :] if "\n" in text else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK.search(text)
        if not match:
            raise
        return json.loads(match.group(0))


class TokenFactory:
    """Thin async wrapper around the OpenAI-compatible Token Factory API."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: AsyncOpenAI | None = None
        self._models: dict[Role, str] = {}
        self._cache: dict[str, tuple[str, ModelCall]] = {}
        self._resolved = False

    @property
    def enabled(self) -> bool:
        return self.settings.llm_enabled

    @property
    def client(self) -> AsyncOpenAI:
        if not self.enabled:
            raise LLMUnavailable("NEBIUS_API_KEY is not set")
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self.settings.nebius_base_url,
                api_key=self.settings.nebius_api_key,
                timeout=120,
                max_retries=2,
            )
        return self._client

    async def resolve_models(self) -> dict[Role, str]:
        """Map each role to a concrete model id, preferring env overrides, then the live list."""
        if self._resolved:
            return self._models
        overrides = {
            "nano": self.settings.model_nano,
            "omni": self.settings.model_omni,
            "super": self.settings.model_super,
            "ultra": self.settings.model_ultra,
        }
        available: list[str] = []
        if self.enabled:
            try:
                listing = await self.client.models.list()
                available = [m.id for m in listing.data]
            except Exception:  # noqa: BLE001 - fall back to defaults when listing fails
                available = []
        for role, hints in ROLE_HINTS.items():
            if overrides[role]:
                self._models[role] = overrides[role]
                continue
            match = next(
                (mid for hint in hints for mid in available if hint in mid.lower()), None
            )
            self._models[role] = match or DEFAULT_IDS[role]
        self._resolved = True
        return self._models

    def model_for(self, role: Role) -> str:
        return self._models.get(role, DEFAULT_IDS[role])

    async def chat(
        self,
        *,
        stage: str,
        role: Role,
        system: str,
        user: str | list[dict[str, Any]],
        max_tokens: int = 1200,
        temperature: float = 0.1,
        reasoning: bool = False,
        budget: Budget | None = None,
    ) -> tuple[str, ModelCall]:
        await self.resolve_models()
        model = self.model_for(role)
        key = hashlib.sha256(
            json.dumps([model, system, user, max_tokens, reasoning], default=str).encode()
        ).hexdigest()
        if key in self._cache:
            text, call = self._cache[key]
            return text, call.model_copy(update={"cached": True, "cost_usd": 0.0, "ms": 0})

        # Nemotron reasoning toggle: '/think' or '/no_think' in the system prompt.
        sys_prompt = f"{'/think' if reasoning else '/no_think'}\n{system}"
        started = time.perf_counter()
        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        ms = int((time.perf_counter() - started) * 1000)
        text = response.choices[0].message.content or ""
        usage = response.usage
        p_in, p_out = PRICES.get(role, (0.0, 0.0))
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        cost = (prompt_tokens * p_in + completion_tokens * p_out) / 1_000_000
        call = ModelCall(
            stage=stage,
            role=role,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=round(cost, 6),
            ms=ms,
        )
        if budget:
            budget.charge(cost)
        self._cache[key] = (text, call)
        return text, call

    async def chat_json(self, *, retries: int = 1, **kwargs: Any) -> tuple[Any, list[ModelCall]]:
        """Ask for a JSON object; on a parse failure, retry once with the error fed back."""
        calls: list[ModelCall] = []
        last_error = ""
        for attempt in range(retries + 1):
            if attempt and last_error:
                kwargs["system"] = (
                    kwargs["system"] + f"\nYour previous reply was not valid JSON ({last_error})."
                    " Reply with one JSON object only."
                )
            text, call = await self.chat(**kwargs)
            calls.append(call)
            try:
                return _parse_json(text), calls
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = str(exc)[:120]
                await asyncio.sleep(0)
        raise ValueError(f"model did not return JSON: {last_error}")


_factory: TokenFactory | None = None


def get_llm() -> TokenFactory:
    global _factory
    if _factory is None:
        _factory = TokenFactory()
    return _factory
