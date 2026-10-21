"""Stage 9 - evidence card: everything a maintainer needs on one screen, as JSON for the UI."""

from __future__ import annotations

import time

from ..schema import Verdict
from .base import Context

COLORS = {
    Verdict.UNGROUNDED: "red",
    Verdict.DUPLICATE: "blue",
    Verdict.NEEDS_INFO: "amber",
    Verdict.REPRODUCED: "green",
}


def build(ctx: Context) -> dict:
    run = ctx.run
    decision = run.decision
    claims = {c.id: c for c in run.claims}
    rows = []
    for e in run.evidence:
        claim = claims.get(e.claim_id)
        rows.append({
            "claim": claim.text if claim else e.claim_id,
            "kind": claim.kind if claim else e.claim_id,
            "status": e.status,
            "method": e.method,
            "deterministic": e.deterministic,
            "detail": e.detail,
            "url": e.url,
            "file": e.file,
            "line": e.line_start,
        })
    diffs = [
        {"claimed": e.claimed_code, "actual": e.actual_code, "file": e.file,
         "line": e.line_start, "status": e.status, "missing": e.data.get("missing", []),
         "url": e.url}
        for e in run.evidence if e.claimed_code
    ]
    ghosts = [
        {"name": claims[e.claim_id].function, "near": e.data.get("near", []),
         "commits_searched": e.data.get("commits_searched")}
        for e in run.evidence
        if e.data.get("ghost") and e.claim_id in claims and claims[e.claim_id].function
    ]
    paths = [
        {"function": claims[e.claim_id].function, "chain": e.data["reachable_via"]}
        for e in run.evidence
        if e.data.get("reachable_via") and e.claim_id in claims
    ]
    by_model: dict[str, dict] = {}
    for call in run.calls:
        slot = by_model.setdefault(call.role, {"model": call.model, "calls": 0, "tokens": 0,
                                               "cost_usd": 0.0, "ms": 0})
        slot["calls"] += 1
        slot["tokens"] += call.prompt_tokens + call.completion_tokens
        slot["cost_usd"] = round(slot["cost_usd"] + call.cost_usd, 6)
        slot["ms"] += call.ms
    finished = run.finished_at or time.time()
    return {
        "run_id": run.id,
        "report": {"id": run.report.id, "title": run.report.title,
                   "source_url": run.report.source_url, "project": run.report.project},
        "verdict": decision.verdict.value if decision else None,
        "color": COLORS.get(decision.verdict) if decision else None,
        "confidence": decision.confidence if decision else None,
        "headline": decision.headline if decision else None,
        "reasons": decision.reasons if decision else [],
        "challenge": decision.challenge if decision else None,
        "challenge_upheld": decision.challenge_upheld if decision else None,
        "reply_draft": decision.reply_draft if decision else None,
        "version": run.resolved_version,
        "rev": run.resolved_rev,
        "ledger": rows,
        "diffs": diffs,
        "ghosts": ghosts,
        "paths": paths,
        "prior_art": [p.model_dump() for p in run.prior_art[:6]],
        "rules": run.rules_hit,
        "sandbox": run.sandbox.model_dump() if run.sandbox else None,
        "fix": [f.model_dump() for f in run.fix],
        "flags": run.flags,
        "injection": run.notes.get("injection", []),
        "cost_usd": run.cost_usd,
        "cost_by_model": by_model,
        "seconds": round(finished - run.started_at, 1),
        "commits_searched": run.notes.get("commits_searched"),
    }


async def run(ctx: Context) -> None:
    await ctx.event("card", "start", "Assembling the evidence card")
    ctx.run.finished_at = time.time()
    card = build(ctx)
    ctx.run.notes["card"] = card
    await ctx.event("card", "done", card["headline"] or "Done", card=card)
