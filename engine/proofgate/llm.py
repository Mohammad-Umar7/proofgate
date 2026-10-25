"""Nebius Token Factory client with Nemotron model routing and cost accounting.

Every model call in ProofGate goes through here. Each Nemotron size has one job:

    omni  - Nemotron 3.5 Super VL: reads screenshots and terminal captures attached to a report
    nano  - Nemotron 3 Nano: fast, cheap structured extraction (claims as JSON)
    super - Nemotron 3 Super: long-context reasoning over the real source code
    ultra - Nemotron 3 Ultra: final adjudication and the adversarial challenge
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from .config import get_settings
from .schema import ModelCall

Role = str  # "nano" | "omni" | "super" | "ultra"
log = logging.getLogger("proofgate.llm")

# Substrings used to pick the right id out of GET /v1/models, most specific first.
ROLE_HINTS: dict[Role, tuple[str, ...]] = {
    "omni": ("nemotron-3-nano-omni", "nano-omni", "nemotron-3.5-super-vl", "super-vl",
             "nemotron-nano-vl", "nano-vl", "-vl"),
    "nano": ("nemotron-3-nano-30b", "nemotron-3-nano", "nemotron-nano"),
    "super": ("nemotron-3-super", "nemotron-super"),
    "ultra": ("nemotron-3-ultra", "nemotron-ultra"),
}

# Fallback ids if the model list is unreachable (as listed by public Token Factory catalogs).
DEFAULT_IDS: dict[Role, str] = {
    "omni": "nvidia/Nemotron-3.5-Super-VL",
    "nano": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    "super": "nvidia/nemotron-3-super-120b-a12b",
    "ultra": "nvidia/Nemotron-3-Ultra-550b-a55b",
}

# USD per 1M tokens (input, output) for the live cost counter, from the Token Factory price list
# (2026-10-24). Override with PG_PRICES='{"nano": [0.06, 0.24], ...}' if Nebius changes them.
PRICES: dict[Role, tuple[float, float]] = {
    "omni": (0.30, 0.90),   # Nemotron 3.5 Super VL
    "nano": (0.06, 0.24),   # Nemotron 3 Nano 30B-A3B
    "super": (0.30, 0.90),  # Nemotron 3 Super 120B-A12B
    "ultra": (1.00, 3.00),  # Nemotron 3 Ultra 550B-A55B
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

        text, call = await self.converse(
            stage=stage, role=role, system=system, messages=[{"role": "user", "content": user}],
            max_tokens=max_tokens, temperature=temperature, reasoning=reasoning, budget=budget,
        )
        self._cache[key] = (text, call)
        return text, call

    async def converse(
        self,
        *,
        stage: str,
        role: Role,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 1200,
        temperature: float = 0.1,
        reasoning: bool = False,
        budget: Budget | None = None,
    ) -> tuple[str, ModelCall]:
        """One completion over a multi-turn conversation."""
        message, call = await self.complete(
            stage=stage, role=role, messages=[{"role": "system", "content": system}, *messages],
            max_tokens=max_tokens, temperature=temperature, reasoning=reasoning, budget=budget)
        return message.content or "", call

    async def complete(
        self,
        *,
        stage: str,
        role: Role,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1200,
        temperature: float = 0.1,
        reasoning: bool | None = None,
        budget: Budget | None = None,
    ) -> tuple[Any, ModelCall]:
        """Raw chat completion, optionally with native tool calling (the FixBench agent loop).

        Returns the provider's message object (content, tool_calls, reasoning_content) and the
        cost record. `reasoning` None leaves the model's default (thinking on)."""
        await self.resolve_models()
        model = self.model_for(role)
        started = time.perf_counter()
        extra: dict[str, Any] = {"tools": tools, "tool_choice": "auto"} if tools else {}
        if reasoning is not None:
            # Nemotron 3 on Token Factory ignores a '/no_think' line in the system prompt and
            # reasons anyway, which can spend all of max_tokens before any content. The chat
            # template switch is what actually turns reasoning on or off.
            extra["extra_body"] = {"chat_template_kwargs": {"enable_thinking": reasoning}}
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **extra,
        )
        ms = int((time.perf_counter() - started) * 1000)
        message = response.choices[0].message
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
        log.info("token-factory %s %s in=%d out=%d $%.5f %d ms", stage, model, prompt_tokens,
                 completion_tokens, cost, ms)
        if budget:
            budget.charge(cost)
        return message, call

    async def chat_json(self, *, retries: int = 1, **kwargs: Any) -> tuple[Any, list[ModelCall]]:
        """Ask for a JSON object; on a parse failure, retry once with the error fed back.
        If no attempt parses, JSONReplyError carries the calls so their cost is still counted."""
        calls: list[ModelCall] = []
        last_error = ""
        for attempt in range(retries + 1):
            if attempt and last_error:
                kwargs["system"] = (
                    kwargs["system"] + f"\nYour previous reply was not valid JSON ({last_error})."
                    " Reply with one JSON object only."
                )
            try:
                text, call = await self.chat(**kwargs)
            except Exception as exc:
                if calls:
                    raise JSONReplyError(str(exc)[:200], calls) from exc
                raise
            calls.append(call)
            try:
                return _parse_json(text), calls
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = str(exc)[:120]
                await asyncio.sleep(0)
        raise JSONReplyError(f"model did not return JSON: {last_error}", calls)


class JSONReplyError(ValueError):
    """No attempt returned parseable JSON. The attempts were still billed: see `calls`."""

    def __init__(self, message: str, calls: list[ModelCall]) -> None:
        super().__init__(message)
        self.calls = calls


_factory: TokenFactory | None = None


def get_llm() -> TokenFactory:
    global _factory
    if _factory is None:
        _factory = TokenFactory()
    return _factory
