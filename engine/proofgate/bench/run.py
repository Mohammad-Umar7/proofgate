"""Run SlopBench under a configuration and compute the metrics we publish.

Metrics
  slop_closed        slop reports ProofGate would close (UNGROUNDED or DUPLICATE)
  slop_ungrounded    slop reports dismissed with a deterministic contradiction
  valid_dismissed    real CVE reports wrongly marked UNGROUNDED  (target: zero)
  agreement          share of reports where ProofGate's action matches the curl team's outcome
  cost / time        mean and p90 per report
Leakage control: a report's own advisory, its own HackerOne page and the public slop list are
excluded from prior art, so ProofGate cannot "look up the answer".
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time

from ..config import ENGINE_DIR
from ..pipeline import execute
from ..schema import Report
from ..stages.base import Options
from .dataset import load_index, load_report

RESULTS = ENGINE_DIR.parent / "bench" / "results"
LEAKY = ("gist.github.com/bagder", "daniel.haxx.se/blog")

CONFIGS: dict[str, dict] = {
    "deterministic": dict(use_llm=False, sandbox=False, fix=False, prior_art_web=False),
    "full": dict(use_llm=True, sandbox=False, fix=False, prior_art_web=True),
    "no-grounding": dict(use_llm=True, grounding=False, sandbox=False, fix=False,
                         prior_art_web=True),
    "single-model": dict(use_llm=True, routed=False, sandbox=False, fix=False,
                         prior_art_web=True),
}


def _p90(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(0.9 * (len(ordered) - 1))))]


async def run_one(row: dict, config: str) -> dict | None:
    data = load_report(row)
    if not data:
        return None
    report = Report(id=row["id"], title=data.get("title") or row["title"],
                    body=data.get("vulnerability_information") or "",
                    source_url=row["url"], submitted_at=data.get("created_at"))
    exclude = {row["url"], *LEAKY}
    if row.get("cve"):
        exclude.add(row["cve"])
    options = Options(**CONFIGS[config], exclude=frozenset(exclude))
    started = time.perf_counter()
    run = await execute(report, options)
    card = run.notes.get("card", {})
    contradictions = [e for e in run.evidence if e.status == "contradicted" and e.deterministic]
    return {
        "id": row["id"], "url": row["url"], "label": row["label"], "cve": row.get("cve"),
        "title": row["title"][:140], "verdict": card.get("verdict"),
        "confidence": card.get("confidence"), "cost_usd": run.cost_usd,
        "seconds": round(time.perf_counter() - started, 2),
        "contradictions": len(contradictions),
        "credibility": card.get("credibility"),
        "evidence": [e.detail[:200] for e in contradictions[:3]],
        "flags": run.flags, "version": run.resolved_version,
    }


def auc(pos: list[float], neg: list[float]) -> float | None:
    """Probability a random valid report outranks a random slop report (Mann-Whitney)."""
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return round(wins / (len(pos) * len(neg)), 3)


def metrics(rows: list[dict]) -> dict:
    slop = [r for r in rows if r["label"] == "slop"]
    valid = [r for r in rows if r["label"] == "valid"]
    closed = [r for r in slop if r["verdict"] in ("UNGROUNDED", "DUPLICATE")]
    ungrounded = [r for r in slop if r["verdict"] == "UNGROUNDED"]
    dismissed = [r for r in valid if r["verdict"] == "UNGROUNDED"]
    valid_closed = [r for r in valid if r["verdict"] in ("UNGROUNDED", "DUPLICATE")]
    # agreement: slop closed, valid kept open for a human (NEEDS_INFO or REPRODUCED)
    agree = len(closed) + (len(valid) - len(valid_closed))
    costs = [r["cost_usd"] for r in rows]
    secs = [r["seconds"] for r in rows]

    def dist(group):
        out: dict[str, int] = {}
        for r in group:
            out[r["verdict"]] = out.get(r["verdict"], 0) + 1
        return out

    return {
        "n": len(rows), "n_slop": len(slop), "n_valid": len(valid),
        "slop_closed": round(len(closed) / max(1, len(slop)), 3),
        "slop_ungrounded": round(len(ungrounded) / max(1, len(slop)), 3),
        "valid_dismissed": len(dismissed),
        "valid_dismissed_ids": [r["id"] for r in dismissed],
        "valid_closed": len(valid_closed),
        "agreement": round(agree / max(1, len(rows)), 3),
        "cost_mean_usd": round(statistics.mean(costs), 5) if costs else 0.0,
        "cost_total_usd": round(sum(costs), 4),
        "seconds_mean": round(statistics.mean(secs), 2) if secs else 0.0,
        "seconds_p90": round(_p90(secs), 2),
        "verdicts_slop": dist(slop), "verdicts_valid": dist(valid),
        # ranking quality of the credibility score, overall and inside the NEEDS_INFO queue
        "credibility_auc": auc([r["credibility"] for r in valid if r.get("credibility") is not None],
                               [r["credibility"] for r in slop if r.get("credibility") is not None]),
        "credibility_auc_needs_info": auc(
            [r["credibility"] for r in valid if r["verdict"] == "NEEDS_INFO" and r.get("credibility") is not None],
            [r["credibility"] for r in slop if r["verdict"] == "NEEDS_INFO" and r.get("credibility") is not None]),
    }


async def run_bench(config: str, limit: int | None = None, concurrency: int = 4,
                    log=print) -> dict:
    rows = load_index()
    if limit:
        slop = [r for r in rows if r["label"] == "slop"][:limit]
        valid = [r for r in rows if r["label"] == "valid"][:limit]
        rows = slop + valid
    sem = asyncio.Semaphore(concurrency)
    results: list[dict] = []

    async def worker(row):
        async with sem:
            try:
                out = await run_one(row, config)
            except Exception as exc:  # noqa: BLE001 - record and continue
                log(f"  {row['id']}: error {exc}")
                return
            if out:
                results.append(out)
                log(f"  {out['id']:<12} {out['label']:<5} -> {out['verdict']:<11} "
                    f"${out['cost_usd']:.4f} {out['seconds']}s")

    await asyncio.gather(*(worker(r) for r in rows))
    results.sort(key=lambda r: r["id"])
    summary = {"config": config, "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "metrics": metrics(results), "rows": results}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{config}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    combined_path = RESULTS / "latest.json"
    combined = json.loads(combined_path.read_text(encoding="utf-8")) if combined_path.exists() else {}
    combined.setdefault("configs", {})[config] = summary["metrics"]
    combined["generated"] = summary["generated"]
    # rows shown on the dashboard: the full pipeline when it exists, else the latest run of this config
    if config == "full" or combined.get("rows_config") in (None, config) or "full" not in combined["configs"]:
        combined["rows"] = results
        combined["rows_config"] = config
    combined_path.write_text(json.dumps(combined, indent=1), encoding="utf-8")
    return summary


LABELS = {
    "deterministic": "Deterministic only (git + tree-sitter + advisories)",
    "full": "Full pipeline (routed Nemotron + Tavily)",
    "no-grounding": "Ablation: no grounding",
    "single-model": "Ablation: Nemotron Ultra for every role",
}


def results_table() -> str:
    combined = json.loads((RESULTS / "latest.json").read_text(encoding="utf-8"))
    rows = ["| Configuration | Slop closed with proof | Real CVEs wrongly dismissed | Real CVEs closed as duplicate | Agreement with curl | Cost / report | Time / report |",
            "|---|---|---|---|---|---|---|"]
    for name in ("deterministic", "full", "single-model", "no-grounding"):
        m = combined.get("configs", {}).get(name)
        if not m:
            continue
        dup = m.get("valid_closed", m["valid_dismissed"]) - m["valid_dismissed"]
        rows.append(
            f"| {LABELS[name]} | {m['slop_closed'] * 100:.0f}% ({round(m['slop_closed'] * m['n_slop'])}/{m['n_slop']}) "
            f"| **{m['valid_dismissed']}** / {m['n_valid']} | {dup} | {m['agreement'] * 100:.0f}% "
            f"| ${m['cost_mean_usd']:.4f} | {m['seconds_mean']:.1f}s |")
    missing = [LABELS[n] for n in ("full", "single-model", "no-grounding") if n not in combined.get("configs", {})]
    note = f"\n\n_Not yet run: {', '.join(missing)}._" if missing else ""
    return "\n".join(rows) + note + f"\n\n_Generated {combined.get('generated')} by `proofgate bench table`._"


def update_readme() -> None:
    readme = RESULTS.parent.parent / "README.md"
    text = readme.read_text(encoding="utf-8")
    start, end = "<!-- BENCH:START -->", "<!-- BENCH:END -->"
    before, _, rest = text.partition(start)
    _, _, after = rest.partition(end)
    readme.write_text(f"{before}{start}\n{results_table()}\n{end}{after}", encoding="utf-8")


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="proofgate bench")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="rebuild bench/slopbench.jsonl from the public sources")
    sub.add_parser("fetch", help="download disclosed report text into the local cache")
    sub.add_parser("table", help="print the results table and update README.md")
    run = sub.add_parser("run", help="run a configuration")
    run.add_argument("--config", choices=sorted(CONFIGS), default="deterministic")
    run.add_argument("--limit", type=int, default=None, help="per-class cap for quick runs")
    run.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args(argv)

    from .dataset import build_index, fetch_reports

    if args.cmd == "build":
        rows = build_index()
        print(f"{len(rows)} reports: {sum(r['label'] == 'slop' for r in rows)} slop, "
              f"{sum(r['label'] == 'valid' for r in rows)} valid")
    elif args.cmd == "fetch":
        print(asyncio.run(fetch_reports(load_index())))
    elif args.cmd == "table":
        update_readme()
        print(results_table())
    else:
        summary = asyncio.run(run_bench(args.config, args.limit, args.concurrency))
        print(json.dumps(summary["metrics"], indent=1))
    return 0
