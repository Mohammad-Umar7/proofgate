"""Stage 4 - prior art: is this already known, already fixed, or a copy of a public report?

Sources: curl's advisory feed (local, instant), OSV.dev (for cited CVE ids), and Tavily web search
across disclosed HackerOne reports, curl.se, GitHub issues and mailing lists.
"""

from __future__ import annotations

from .. import advisories, tavily
from ..schema import Evidence, PriorArt
from .base import Context


def _identifiers(ctx: Context) -> set[str]:
    out = set()
    for c in ctx.run.claims:
        for value in (c.function, c.symbol):
            if value:
                out.add(value)
        if c.file:
            out.add(c.file.rsplit("/", 1)[-1].split(".")[0])
    return out


async def check_cited_cves(ctx: Context) -> None:
    for claim in [c for c in ctx.run.claims if c.kind == "cve" and c.cve]:
        adv = advisories.by_cve(claim.cve)
        if adv:
            affected = adv.affects(ctx.run.resolved_version)
            note = ""
            if affected is False:
                note = f"; {ctx.run.resolved_version} is not affected (fixed in {adv.fixed_in})"
            ctx.run.evidence.append(Evidence(
                claim_id=claim.id, status="verified", method="curl-advisory",
                detail=f"{claim.cve} is a real curl advisory: {adv.summary}{note}",
                url=adv.www, data={"affects_claimed_version": affected, "fixed_in": adv.fixed_in},
            ))
            ctx.run.prior_art.append(PriorArt(
                source="curl-advisory", id=adv.cve, title=adv.summary, url=adv.www or "",
                score=1.0, fixed_in=adv.fixed_in, snippet=adv.details[:300],
            ))
            continue
        try:
            record = await advisories.osv_lookup(claim.cve)
        except Exception:  # noqa: BLE001 - network failure leaves the claim unverified
            record = {"unknown": True}
        if record is None:
            ctx.run.evidence.append(Evidence(
                claim_id=claim.id, status="contradicted", method="osv",
                detail=f"{claim.cve} does not exist in OSV.dev or in curl's advisory list",
            ))
        elif record.get("unknown"):
            ctx.run.evidence.append(Evidence(
                claim_id=claim.id, status="unverifiable", method="osv",
                detail=f"Could not reach OSV.dev to check {claim.cve}", deterministic=False,
            ))
        else:
            pkgs = sorted({a.get("package", {}).get("name", "?") for a in record.get("affected", [])})
            ctx.run.evidence.append(Evidence(
                claim_id=claim.id, status="contradicted", method="osv",
                detail=f"{claim.cve} is not a curl vulnerability (OSV lists it for "
                       f"{', '.join(pkgs[:4]) or 'another project'})",
                url=f"https://osv.dev/vulnerability/{claim.cve}",
            ))


async def run(ctx: Context) -> None:
    await ctx.event("prior_art", "start", "Searching advisories, OSV and the web for prior art")
    await check_cited_cves(ctx)

    ids = _identifiers(ctx)
    report_tokens = advisories.tokens(f"{ctx.run.report.title} {ctx.run.notes.get('summary') or ''}"
                                      f" {' '.join(ids)}")
    scored = []
    for adv in advisories.curl_advisories():
        score = advisories.similarity(report_tokens, ids, adv)
        if score >= 0.35:
            scored.append((score, adv))
    scored.sort(key=lambda s: s[0], reverse=True)
    cited = {p.id for p in ctx.run.prior_art}
    for score, adv in scored[:5]:
        if adv.cve in cited:
            continue
        ctx.run.prior_art.append(PriorArt(
            source="curl-advisory", id=adv.cve, title=adv.summary, url=adv.www or "",
            score=round(score, 2), fixed_in=adv.fixed_in, snippet=adv.details[:300],
        ))
    await ctx.event("prior_art", "progress",
                    f"Compared against {len(advisories.curl_advisories())} curl advisories",
                    matches=len(scored))

    if ctx.options.prior_art_web and ctx.run.notes.get("tavily_ok", True):
        try:
            query = f"curl {ctx.run.report.title} {ctx.run.notes.get('bug_class') or ''}".strip()
            results = await tavily.search(query)
            for item in results[:6]:
                url = item.get("url", "")
                # Skip the report itself if it was published already.
                if ctx.run.report.source_url and url.rstrip("/") == ctx.run.report.source_url.rstrip("/"):
                    continue
                ctx.run.prior_art.append(PriorArt(
                    source="hackerone" if "hackerone.com" in url else "tavily",
                    id=url.rsplit("/", 1)[-1] or url, title=item.get("title", "")[:200], url=url,
                    score=round(float(item.get("score", 0.0)), 2),
                    snippet=(item.get("content") or "")[:300],
                ))
            await ctx.event("prior_art", "progress", f"Tavily returned {len(results)} results",
                            query=query)
        except tavily.TavilyError as exc:
            await ctx.event("prior_art", "progress", f"Web search skipped: {exc}")
        except Exception as exc:  # noqa: BLE001
            await ctx.event("prior_art", "progress", f"Web search failed: {exc}")

    ctx.run.prior_art.sort(key=lambda p: p.score, reverse=True)
    top = ctx.run.prior_art[0] if ctx.run.prior_art else None
    await ctx.event(
        "prior_art", "done",
        f"Closest match: {top.id} ({top.score:.2f})" if top else "No prior art found",
        prior_art=[p.model_dump() for p in ctx.run.prior_art[:8]],
    )
