"""End-to-end pipeline on offline red-team rounds (deterministic stages only)."""

import pytest

from proofgate.arena import template_report
from proofgate.pipeline import execute
from proofgate.stages.base import Options

OFFLINE = Options(use_llm=False, sandbox=False, fix=False, prior_art_web=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("level", [1, 2])
async def test_invented_code_is_ungrounded(level):
    run = await execute(template_report(level, seed=7), OFFLINE)
    assert run.decision.verdict.value == "UNGROUNDED"
    assert any(e.status == "contradicted" and e.deterministic for e in run.evidence)
    assert run.notes["card"]["verdict"] == "UNGROUNDED"


@pytest.mark.asyncio
async def test_injection_is_flagged_and_never_accepted():
    run = await execute(template_report(5, seed=7), OFFLINE)
    assert "prompt-injection" in run.flags
    assert run.decision.verdict.value != "REPRODUCED"


@pytest.mark.asyncio
async def test_card_has_every_section():
    run = await execute(template_report(2, seed=7), OFFLINE)
    card = run.notes["card"]
    for key in ("verdict", "ledger", "diffs", "ghosts", "prior_art", "rules", "cost_usd"):
        assert key in card
    assert card["ghosts"], "an invented function should become a ghost node"
