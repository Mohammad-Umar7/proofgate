"""Shared stage plumbing: a context object carrying the run, the event emitter and the budget."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from ..config import get_settings
from ..llm import Budget, JSONReplyError, TokenFactory, get_llm
from ..repo import Repo, get_repo
from ..schema import ModelCall, Run, StageEvent, StageName

Emit = Callable[[StageEvent], Awaitable[None]]


@dataclass
class Options:
    grounding: bool = True  # ablation switch for SlopBench
    use_llm: bool = True
    routed: bool = True  # False = single model (Ultra) for every role
    sandbox: bool = True
    fix: bool = True
    prior_art_web: bool = True
    # Benchmark leakage control: advisory ids / URLs that must not count as prior art
    # (a CVE's own advisory, the report's own page, lists that label the report).
    exclude: frozenset[str] = frozenset()


@dataclass
class Context:
    run: Run
    emit: Emit
    options: Options = field(default_factory=Options)
    llm: TokenFactory = field(default_factory=get_llm)
    budget: Budget = field(
        default_factory=lambda: Budget(limit_usd=get_settings().max_cost_per_report)
    )
    _stage_started: dict[str, float] = field(default_factory=dict)

    @property
    def repo(self) -> Repo:
        return get_repo(self.run.report.project)

    @property
    def llm_on(self) -> bool:
        return self.options.use_llm and self.llm.enabled

    def role(self, role: str) -> str:
        return role if self.options.routed else "ultra"

    def record(self, calls: list[ModelCall] | ModelCall) -> None:
        for call in calls if isinstance(calls, list) else [calls]:
            self.run.calls.append(call)

    async def ask_json(self, **kwargs: object) -> tuple[object, list[ModelCall]]:
        """llm.chat_json, but attempts that never parsed are recorded before the error goes up,
        so the run's cost includes them. The caller records the calls of a success."""
        try:
            return await self.llm.chat_json(**kwargs)  # type: ignore[arg-type]
        except JSONReplyError as exc:
            self.record(exc.calls)
            raise

    async def event(
        self, stage: StageName, status: str, message: str, **data: object
    ) -> None:
        now = time.time()
        if status == "start":
            self._stage_started[stage] = now
        started = self._stage_started.get(stage, now)
        evt = StageEvent(
            run_id=self.run.id,
            stage=stage,
            status=status,  # type: ignore[arg-type]
            message=message,
            elapsed_ms=int((now - started) * 1000),
            cost_usd=self.run.cost_usd,
            data=dict(data),
        )
        self.run.events.append(evt)
        await self.emit(evt)
