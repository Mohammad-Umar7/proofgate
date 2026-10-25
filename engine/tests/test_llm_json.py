"""JSON replies: failed attempts still count toward the run's cost."""

import pytest

from proofgate.llm import JSONReplyError, TokenFactory
from proofgate.schema import ModelCall, Report, Run
from proofgate.stages.base import Context


class Scripted(TokenFactory):
    """A Token Factory stand-in that returns canned replies, each billed one cent."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)

    async def chat(self, **kwargs):  # noqa: ANN003 - same keywords as TokenFactory.chat
        return self.replies.pop(0), ModelCall(stage=kwargs["stage"], role=kwargs["role"],
                                              model="test", cost_usd=0.01)


async def _noop(_event) -> None:
    return None


def _ctx(llm: TokenFactory) -> Context:
    return Context(run=Run(report=Report(title="t", body="b" * 30)), emit=_noop, llm=llm)


@pytest.mark.asyncio
async def test_unparsed_attempts_are_recorded():
    ctx = _ctx(Scripted(["", "still not json"]))
    with pytest.raises(JSONReplyError):
        await ctx.ask_json(stage="claims", role="nano", system="s", user="u")
    assert len(ctx.run.calls) == 2
    assert ctx.run.cost_usd == pytest.approx(0.02)


@pytest.mark.asyncio
async def test_success_leaves_recording_to_the_caller():
    ctx = _ctx(Scripted(["nope", '{"ok": true}']))
    data, calls = await ctx.ask_json(stage="claims", role="nano", system="s", user="u")
    assert data == {"ok": True} and len(calls) == 2
    assert ctx.run.calls == []
