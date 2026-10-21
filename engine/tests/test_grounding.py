"""Grounding against the real curl history (needs the curl clone in the cache)."""

import pytest

from proofgate.schema import Report, Run
from proofgate.stages import claims, grounding, intake
from proofgate.stages.base import Context, Options

FAKE = Report(
    title="Heap overflow in Curl_cookie_parse_header (curl 8.5.0)",
    body="""The function `Curl_cookie_parse_header()` in lib/cookie.c copies the cookie name
with strcpy into a fixed buffer. See lib/cookie.c:4021.

```c
  char namebuf[64];
  strcpy(namebuf, cookie_header_name_from_server);
  cookie_secure_flag_handler(namebuf, data->set.cookie_policy_flags);
```
""",
)

REAL = Report(
    title="Question about Curl_cookie_add in curl 8.5.0",
    body="In lib/cookie.c the function Curl_cookie_add() parses Set-Cookie headers.",
)


async def _run(report: Report) -> Run:
    run = Run(report=report)

    async def emit(_):
        return None

    ctx = Context(run=run, emit=emit, options=Options(use_llm=False))
    for stage in (intake, claims, grounding):
        await stage.run(ctx)
    return run


def _status(run: Run, kind: str) -> list[str]:
    ids = {c.id for c in run.claims if c.kind == kind}
    return [e.status for e in run.evidence if e.claim_id in ids]


@pytest.mark.asyncio
async def test_fabricated_report_is_contradicted():
    run = await _run(FAKE)
    assert run.resolved_rev == "curl-8_5_0"
    assert "contradicted" in _status(run, "function")  # function never existed
    assert "contradicted" in _status(run, "line")  # line past end of file
    assert "contradicted" in _status(run, "code")  # quoted code never existed
    ghost = [e for e in run.evidence if e.data.get("ghost")]
    assert ghost and ghost[0].data["commits_searched"] > 30000


@pytest.mark.asyncio
async def test_real_function_is_verified():
    run = await _run(REAL)
    assert "verified" in _status(run, "function")
    assert "verified" in _status(run, "file")
