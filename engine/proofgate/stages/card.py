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


def credibility(ctx: Context) -> tuple[int, list[str]]:
    """Order the NEEDS_INFO queue: a transparent 0-100 score, fixed weights (not fitted to any
    benchmark). Explains itself so a maintainer can see why one report ranks above another."""
    run = ctx.run
    score, why = 50, []
    verified = [e for e in run.evidence if e.deterministic and e.status == "verified"
                and e.method in ("tree-sitter", "git-show", "git-grep", "sandbox")]
    if verified:
        bump = min(32, 8 * len(verified))
        score += bump
        why.append(f"+{bump} {len(verified)} precise claims check out")
    contradicted = [e for e in run.evidence if e.deterministic and e.status == "contradicted"]
    if contradicted:
        hit = min(60, 15 * len(contradicted))
        score -= hit
        why.append(f"-{hit} {len(contradicted)} claims contradict the code")
    roles = {b.role for b in run.code_blocks}
    if "output" in roles:
        score += 15
        why.append("+15 includes sanitizer or crash output")
    if roles & {"poc", "shell"}:
        score += 10
        why.append("+10 includes reproduction steps")
    if run.rules_hit:
        score -= 10 * len(run.rules_hit)
        why.append(f"-{10 * len(run.rules_hit)} matches the project's 'not a security issue' policy")
    if "prompt-injection" in run.flags:
        score -= 10
        why.append("-10 tries to instruct the triage model")
    analysis = next((e for e in run.evidence if e.method == "llm-super"), None)
    if analysis is not None:
        delta = {"plausible": 20, "implausible": -20}.get(analysis.data.get("assessment"), 0)
        if delta:
            score += delta
            why.append(f"{delta:+d} Nemotron Super reading the real code: {analysis.data.get('assessment')}")
    return max(0, min(100, score)), why


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
    cred, cred_why = credibility(ctx)
    return {
        "credibility": cred,
        "credibility_why": cred_why,
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
