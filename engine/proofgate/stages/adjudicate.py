"""Stage 7 - adjudication: a rule table decides, Nemotron Ultra explains and then attacks it.

Design rules, in priority order:
  * REPRODUCED only from sandbox evidence attributed to the project's own code.
  * DUPLICATE only from a strong match against a published advisory.
  * UNGROUNDED only with at least one deterministic contradiction outweighing what checks out.
  * Everything else is NEEDS_INFO. Model opinion alone can never dismiss a report.
The adversarial pass argues the reporter's side; if it lands, a dismissal becomes NEEDS_INFO.
"""

from __future__ import annotations

import json

from ..schema import Decision, Evidence, Verdict
from ..security import fence, guard, new_tag
from .base import Context

CONTRA_WEIGHT = {"function": 3, "code": 3, "repro": 3, "line": 2, "file": 2, "cve": 2,
                 "symbol": 2, "version": 1}
VERIFY_WEIGHT = {"function": 1.0, "code": 2.0, "line": 1.0, "file": 0.5, "symbol": 0.5,
                 "cve": 0.5, "version": 0.25}


def _kind(ctx: Context, evidence: Evidence) -> str:
    if evidence.claim_id == "repro":
        return "repro"
    claim = next((c for c in ctx.run.claims if c.id == evidence.claim_id), None)
    return claim.kind if claim else "other"


def score(ctx: Context) -> dict:
    contra, verify, contradictions, verified = 0.0, 0.0, [], []
    for evidence in ctx.run.evidence:
        if not evidence.deterministic:
            continue
        kind = _kind(ctx, evidence)
        if evidence.status == "contradicted":
            contra += CONTRA_WEIGHT.get(kind, 1)
            contradictions.append(evidence)
        elif evidence.status == "verified":
            verify += VERIFY_WEIGHT.get(kind, 0.5)
            verified.append(evidence)
    return {"contra": contra, "verify": verify, "contradictions": contradictions,
            "verified": verified}


def rule_table(ctx: Context) -> Decision:
    s = score(ctx)
    repro_hit = next((e for e in ctx.run.evidence
                      if e.claim_id == "repro" and e.status == "verified"), None)
    if repro_hit:
        return Decision(verdict=Verdict.REPRODUCED, confidence=0.95,
                        headline="Reproduced: the reporter's steps crash the project's own code",
                        reasons=[repro_hit.detail])

    strong = [p for p in ctx.run.prior_art if p.source == "curl-advisory" and p.score >= 0.9]
    similar = [p for p in ctx.run.prior_art if p.source == "curl-advisory" and 0.6 <= p.score < 0.9]
    if strong or (similar and s["contra"] < 3):
        match = (strong or similar)[0]
        return Decision(
            verdict=Verdict.DUPLICATE, confidence=0.9 if strong else 0.7,
            headline=f"Duplicate of {match.id}: {match.title}",
            reasons=[f"Matches published advisory {match.id} (fixed in {match.fixed_in})",
                     *[e.detail for e in s["verified"][:2]]],
        )

    if s["contradictions"] and s["contra"] >= 3 and s["contra"] > s["verify"]:
        margin = (s["contra"] - s["verify"]) / max(s["contra"], 1)
        return Decision(
            verdict=Verdict.UNGROUNDED, confidence=round(min(0.98, 0.6 + 0.4 * margin), 2),
            headline="Ungrounded: the report's central claims contradict the real code",
            reasons=[e.detail for e in s["contradictions"][:4]],
        )

    reasons = [e.detail for e in s["verified"][:2]]
    if ctx.run.rules_hit:
        reasons.insert(0, f"Policy: {ctx.run.rules_hit[0]['title']} — {ctx.run.rules_hit[0]['reason']}")
    if ctx.run.sandbox is None or not ctx.run.sandbox.ran:
        reasons.append("No runnable reproduction was provided or it could not be run")
    return Decision(
        verdict=Verdict.NEEDS_INFO, confidence=0.6,
        headline="Needs info: claims check out against the code, but nothing proves the bug",
        reasons=reasons or ["Not enough checkable detail to confirm or refute"],
    )


def ledger(ctx: Context) -> str:
    rows = []
    for e in ctx.run.evidence:
        rows.append({"claim": e.claim_id, "status": e.status, "method": e.method,
                     "deterministic": e.deterministic, "detail": e.detail[:300]})
    return json.dumps({
        "version": ctx.run.resolved_version,
        "evidence": rows[:40],
        "prior_art": [{"id": p.id, "score": p.score, "title": p.title[:120]}
                      for p in ctx.run.prior_art[:5]],
        "policy_hits": [{"rule": h["title"], "reason": h["reason"]} for h in ctx.run.rules_hit],
        "sandbox": None if not ctx.run.sandbox else {
            "ran": ctx.run.sandbox.ran, "attribution": ctx.run.sandbox.attribution},
        "flags": ctx.run.flags,
    }, indent=1)


EXPLAIN_SYSTEM = """You are the final reviewer for an open-source project's security inbox.
A rule table has already chosen the verdict {verdict} from an evidence ledger built by
deterministic checks against the real source code. Write for the volunteer maintainer.
Return one JSON object:
{{"headline": "<max 14 words>", "reasons": ["<max 3 bullets, cite file:line or ids>"],
  "reply_draft": "<polite, factual reply to the reporter, max 140 words, cites the evidence,
  invites a reproduction if one is missing; never insulting>"}}
Do not change the verdict. {guard}"""

CHALLENGE_SYSTEM = """You are the reporter's advocate. A triage system reached the verdict
{verdict} on a security report. Using ONLY the evidence ledger and report below, make the
strongest honest case that this verdict is wrong (for example: a check used the wrong version,
a file was renamed, the quoted code is paraphrased but the bug is real).
Return one JSON object:
{{"objection": "<strongest objection, max 60 words>",
  "credible": true|false,
  "what_would_settle_it": "<one concrete check or artifact>"}}
"credible" must be true only if the objection points at a specific gap in the evidence. {guard}"""


async def run(ctx: Context) -> None:
    await ctx.event("adjudicate", "start", "Forming a verdict from the evidence ledger")
    decision = rule_table(ctx)
    await ctx.event("adjudicate", "progress", f"Rule table: {decision.verdict.value}",
                    verdict=decision.verdict.value, confidence=decision.confidence)

    if ctx.llm_on:
        tag = new_tag()
        report = fence(f"{ctx.run.report.title}\n\n{ctx.run.report.body}"[:8000], tag)
        try:
            data, calls = await ctx.llm.chat_json(
                stage="adjudicate", role=ctx.role("ultra"),
                system=EXPLAIN_SYSTEM.format(verdict=decision.verdict.value, guard=guard(tag)),
                user=f"EVIDENCE LEDGER:\n{ledger(ctx)}\n\nREPORT:\n{report}",
                max_tokens=900, budget=ctx.budget,
            )
            ctx.record(calls)
            decision.headline = str(data.get("headline") or decision.headline)[:140]
            decision.reasons = [str(r)[:300] for r in data.get("reasons", [])][:3] or decision.reasons
            decision.reply_draft = str(data.get("reply_draft") or "")[:1500] or None
        except Exception as exc:  # noqa: BLE001
            await ctx.event("adjudicate", "progress", f"Explanation skipped: {exc}")

        try:
            data, calls = await ctx.llm.chat_json(
                stage="adjudicate", role=ctx.role("ultra"),
                system=CHALLENGE_SYSTEM.format(verdict=decision.verdict.value, guard=guard(tag)),
                user=f"EVIDENCE LEDGER:\n{ledger(ctx)}\n\nREPORT:\n{report}",
                max_tokens=600, reasoning=True, budget=ctx.budget,
            )
            ctx.record(calls)
            credible = bool(data.get("credible"))
            decision.challenge = str(data.get("objection") or "")[:500]
            decision.challenge_upheld = not credible
            if credible and decision.verdict == Verdict.UNGROUNDED:
                s = score(ctx)
                # A credible objection only overturns a dismissal that is not overwhelming.
                if s["contra"] < 6:
                    decision.verdict = Verdict.NEEDS_INFO
                    decision.headline = "Needs info: the challenger found a gap worth checking"
                    decision.reasons.insert(0, f"Challenge: {decision.challenge}")
                    decision.confidence = 0.55
            await ctx.event("adjudicate", "progress",
                            f"Adversarial pass: {'objection holds' if credible else 'verdict stands'}",
                            objection=decision.challenge,
                            settle=data.get("what_would_settle_it"))
        except Exception as exc:  # noqa: BLE001
            await ctx.event("adjudicate", "progress", f"Challenge skipped: {exc}")

    if not decision.reply_draft:
        decision.reply_draft = default_reply(ctx, decision)
    ctx.run.decision = decision
    await ctx.event("adjudicate", "done", decision.headline, verdict=decision.verdict.value,
                    confidence=decision.confidence, reasons=decision.reasons,
                    challenge=decision.challenge, challenge_upheld=decision.challenge_upheld)


def default_reply(ctx: Context, decision: Decision) -> str:
    lines = ["Thank you for the report. We checked it against the source code of curl "
             f"{ctx.run.resolved_version}."]
    if decision.verdict == Verdict.UNGROUNDED:
        lines.append("Several statements in the report do not match the code:")
        lines += [f"- {r}" for r in decision.reasons[:3]]
        lines.append("If you can reproduce the issue on a current release, please share the exact "
                     "steps and output and we will look again.")
    elif decision.verdict == Verdict.DUPLICATE:
        lines.append(f"This appears to be already known: {decision.headline}.")
    elif decision.verdict == Verdict.NEEDS_INFO:
        lines.append("The code you reference exists, but we could not confirm the problem. "
                     "Please provide a minimal reproduction against the latest release.")
    else:
        lines.append("We were able to reproduce the problem and are working on a fix.")
    return "\n".join(lines)
