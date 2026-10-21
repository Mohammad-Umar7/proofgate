"""Stage 5 - project rules: apply the project's own definition of "not a security issue".

The rulebook is built from the project's policy document at runtime (for curl,
docs/VULN-DISCLOSURE-POLICY.md, section "Not security issues"), so it stays current as the
project changes its policy. Some rules have deterministic triggers; Nemotron Super judges the rest.
"""

from __future__ import annotations

import re
from functools import lru_cache

from ..repo import Repo
from ..security import fence, guard, new_tag
from .base import Context
from .intake import full_text

POLICY_FILES = ("docs/VULN-DISCLOSURE-POLICY.md", "SECURITY.md")


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


@lru_cache(maxsize=4)
def rulebook(repo: Repo) -> tuple[dict, ...]:
    for path in POLICY_FILES:
        if repo.exists(repo.head(), path):
            text = repo.show(repo.head(), path)
            break
    else:
        return ()
    match = re.search(r"^# Not security issues\s*$(.*?)(?=^# )", text, re.S | re.M)
    if not match:
        return ()
    rules = []
    for section in re.split(r"^## ", match.group(1), flags=re.M)[1:]:
        title, _, body = section.partition("\n")
        body = re.sub(r"\s+", " ", body).strip()
        rules.append({"id": _slug(title), "title": title.strip(), "text": body[:900],
                      "source": f"{POLICY_FILES[0]}#{_slug(title)}"})
    return tuple(rules)


def deterministic_hits(ctx: Context, rules: dict[str, dict]) -> list[dict]:
    hits = []
    paths = {e.file for e in ctx.run.evidence if e.file}
    paths |= {c.file for c in ctx.run.claims if c.file}
    test_paths = sorted(p for p in paths if p and p.startswith("tests/"))
    if test_paths and "test-code" in rules:
        hits.append({"rule": "test-code", "reason": f"The cited code is test code: {', '.join(test_paths)}",
                     "deterministic": True})

    repo = ctx.repo
    for evidence in ctx.run.evidence:
        if evidence.status != "verified" or not evidence.file or not evidence.line_start:
            continue
        try:
            lines = repo.lines(evidence.rev or repo.head(), evidence.file)[: evidence.line_start]
        except Exception:  # noqa: BLE001
            continue
        depth, guarded = 0, None
        for line in reversed(lines):
            stripped = line.strip()
            if stripped.startswith("#endif"):
                depth += 1
            elif stripped.startswith("#if"):
                if depth == 0 and re.search(r"DEBUGBUILD|CURLDEBUG|UNITTESTS", stripped):
                    guarded = stripped
                    break
                depth = max(0, depth - 1)
        if guarded and "debug-experiments" in rules:
            hits.append({"rule": "debug-experiments",
                         "reason": f"{evidence.file}:{evidence.line_start} is only compiled in debug "
                                   f"builds ({guarded})", "deterministic": True})
            break

    master_only = [e for e in ctx.run.evidence
                   if e.status == "partial" and "exists on master" in e.detail]
    if master_only and "non-released-code" in rules:
        hits.append({"rule": "non-released-code", "reason": master_only[0].detail,
                     "deterministic": True})
    return hits


RULES_SYSTEM = """You apply a project's written security policy to a vulnerability report.
Below is the list of categories the project explicitly does NOT treat as security issues.
Decide which categories clearly apply to the report. Be conservative: if unsure, do not list it.
Return one JSON object: {{"applies": [{{"rule": "<id>", "reason": "<max 30 words>"}}]}}
POLICY:
{rules}
{guard}"""


async def run(ctx: Context) -> None:
    await ctx.event("rules", "start", "Applying the project's security policy")
    book = rulebook(ctx.repo)
    by_id = {r["id"]: r for r in book}
    if not book:
        await ctx.event("rules", "skipped", "No policy document found")
        return
    await ctx.event("rules", "progress",
                    f"Rulebook: {len(book)} 'not a security issue' categories from the policy",
                    rules=[r["title"] for r in book])

    hits = deterministic_hits(ctx, by_id)
    if ctx.llm_on:
        tag = new_tag()
        policy = "\n".join(f"- {r['id']}: {r['title']} — {r['text'][:400]}" for r in book)
        try:
            data, calls = await ctx.llm.chat_json(
                stage="rules",
                role=ctx.role("super"),
                system=RULES_SYSTEM.format(rules=policy, guard=guard(tag)),
                user=fence(full_text(ctx)[:10000], tag),
                max_tokens=600,
                budget=ctx.budget,
            )
            ctx.record(calls)
            known = {h["rule"] for h in hits}
            for item in data.get("applies", [])[:4]:
                if item.get("rule") in by_id and item["rule"] not in known:
                    hits.append({"rule": item["rule"], "reason": str(item.get("reason", ""))[:240],
                                 "deterministic": False})
        except Exception as exc:  # noqa: BLE001
            await ctx.event("rules", "progress", f"Policy reasoning skipped: {exc}")

    for hit in hits:
        rule = by_id[hit["rule"]]
        hit.update(title=rule["title"], source=rule["source"])
    ctx.run.rules_hit = hits
    await ctx.event(
        "rules", "done",
        f"{len(hits)} policy rule(s) apply: " + ", ".join(h["title"] for h in hits) if hits
        else "No policy exclusions apply",
        hits=hits,
    )
