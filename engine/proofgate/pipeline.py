"""Run the nine stages in order, cheapest first, streaming events as they happen."""

from __future__ import annotations

from .llm import BudgetExceeded
from .schema import Report, Run, StageEvent
from .stages import (
    adjudicate, card, claims, fix, grounding, intake, prior_art, repro, rules,
)
from .stages.base import Context, Emit, Options

STAGES = (intake, claims, grounding, prior_art, rules, repro, adjudicate, fix, card)
ALWAYS = (adjudicate, card)  # still run after a failure so the maintainer gets a card


async def _noop(_: StageEvent) -> None:
    return None


async def execute(report: Report, options: Options | None = None, emit: Emit | None = None) -> Run:
    run = Run(report=report)
    ctx = Context(run=run, emit=emit or _noop, options=options or Options())
    aborted = False
    for stage in STAGES:
        if aborted and stage not in ALWAYS:
            continue
        name = stage.__name__.rsplit(".", 1)[-1]
        try:
            await stage.run(ctx)
        except BudgetExceeded as exc:
            aborted = True
            run.flags.append("budget-exceeded")
            await ctx.event(name, "error", f"Stopped: per-report budget reached ({exc})")
        except Exception as exc:  # noqa: BLE001 - one stage failing must not lose the run
            await ctx.event(name, "error", f"{type(exc).__name__}: {exc}")
            if stage in ALWAYS and stage is adjudicate:
                ctx.run.decision = adjudicate.rule_table(ctx)
    return run
