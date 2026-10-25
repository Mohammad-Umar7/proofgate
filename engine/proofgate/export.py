"""Export the static demo data the web app needs (all real, all reproducible):

  graph.json     curl's call graph at the latest release (tree-sitter), for the code galaxy
  history.json   commits per month across curl's whole history, for the history helix
  replays.json   recorded pipeline runs: synthetic samples + selected SlopBench reports
  bench.json     SlopBench metrics
  fixbench.json  FixBench: metrics and per-CVE grades for each agent model (small)
  fixbench-<model>.json  that model's transcripts, patches and the maintainers' patches

Real HackerOne reports are exported as title, link and the extracted claims only; their full
text is not redistributed.
"""

from __future__ import annotations

import asyncio
import json
from collections import Counter

from .bench.dataset import load_index, load_report
from .codeindex import get_index
from .config import ENGINE_DIR
from .pipeline import execute
from .repo import get_repo
from .schema import Report, StageEvent
from .stages.base import Options

ROOT = ENGINE_DIR.parent
OUT = ROOT / "web" / "public" / "data"
SAMPLES = ROOT / "bench" / "samples"


def export_graph() -> dict:
    repo = get_repo("curl")
    rev, version = repo.resolve(None)
    data = get_index(repo, rev).export_graph()
    data["version"] = version
    return data


def export_history() -> dict:
    repo = get_repo("curl")
    months = Counter(d[:7] for d in repo.git("log", repo.head(), "--format=%cs").split())
    ordered = sorted(months.items())
    return {"months": ordered, "total": sum(months.values()),
            "first": ordered[0][0], "last": ordered[-1][0]}


async def record(report: Report, options: Options) -> tuple[list[dict], dict]:
    events: list[dict] = []

    async def emit(event: StageEvent) -> None:
        events.append(json.loads(event.model_dump_json()))

    run = await execute(report, options, emit)
    return events, run.notes.get("card", {})


def _strip(events: list[dict]) -> list[dict]:
    """Drop bulky or report-derived fields not needed by the UI."""
    for event in events:
        if event["stage"] == "card":
            event["data"] = {}
    return events


async def export_replays(options: Options, picks: int = 4) -> list[dict]:
    replays = []
    for path in sorted(SAMPLES.glob("*.json")):
        sample = json.loads(path.read_text(encoding="utf-8"))
        report = Report(title=sample["title"], body=sample["body"])
        events, card = await record(report, options)
        replays.append({"id": sample["id"], "label": sample["label"], "kind": "synthetic",
                        "report": {"title": report.title, "body": report.body},
                        "events": _strip(events), "card": card})
    results = ROOT / "bench" / "results" / "latest.json"
    rows = json.loads(results.read_text(encoding="utf-8")).get("rows", []) if results.exists() else []
    index = {r["id"]: r for r in load_index()}
    slop = [r for r in rows if r["label"] == "slop" and r["verdict"] == "UNGROUNDED"]
    slop.sort(key=lambda r: -r["contradictions"])
    valid = [r for r in rows if r["label"] == "valid" and r["verdict"] != "UNGROUNDED"]
    for row in slop[:picks] + valid[: max(1, picks // 2)]:
        meta = index.get(row["id"])
        data = load_report(meta) if meta else None
        if not data:
            continue
        exclude = {meta["url"], "gist.github.com/bagder", "daniel.haxx.se/blog"}
        if meta.get("cve"):
            exclude.add(meta["cve"])
        report = Report(title=data.get("title") or meta["title"],
                        body=data.get("vulnerability_information") or "",
                        source_url=meta["url"])
        opts = Options(**{**options.__dict__, "exclude": frozenset(exclude)})
        events, card = await record(report, opts)
        label = ("Real curl report · listed as AI slop" if meta["label"] == "slop"
                 else f"Real curl report · became {meta.get('cve')}")
        replays.append({"id": row["id"], "label": label, "kind": meta["label"],
                        "report": {"title": report.title, "body": "", "source_url": meta["url"]},
                        "events": _strip(events), "card": card})
    return replays


async def export_arena(options: Options, seeds: tuple[int, ...] = (7, 11)) -> list[dict]:
    from .arena import LEVELS, red_team_report, template_report

    rounds = []
    for seed in seeds:
        for level in range(1, 6):
            report = (await red_team_report(level, seed=seed)) if options.use_llm \
                else template_report(level, seed=seed)
            events, card = await record(report, options)
            verdict = card.get("verdict")
            rounds.append({
                "seed": seed, "level": level, "strategy": LEVELS[level],
                "author": "Nemotron Super" if options.use_llm else "template",
                "report": {"title": report.title, "body": report.body},
                "verdict": verdict, "caught": verdict in ("UNGROUNDED", "NEEDS_INFO"),
                "events": _strip(events), "card": card,
            })
    return rounds


HEAVY = ("steps", "diff", "gold_diff", "summary_agent")


def export_fixbench() -> tuple[dict, dict[str, dict]]:
    """FixBench results: a small summary (metrics, per-instance outcome, dropped instances, the
    Super-then-Ultra cascade) and, per model, the full transcripts and patches."""
    from .fixbench.dataset import load_index as fixbench_index
    from .fixbench.run import cascade, load_results

    models = load_results()
    routed = cascade(models["super"], models["ultra"]) if {"super", "ultra"} <= set(models) else None
    instances = [{k: r.get(k) for k in ("id", "summary", "severity", "published", "fix_commit",
                                        "base", "advisory_url", "source_files", "validated", "why",
                                        "fail_to_pass_valid", "pass_to_pass")}
                 for r in fixbench_index()]
    for r in instances:
        r["pass_to_pass"] = len(r["pass_to_pass"] or [])
    summary_models = {role: {**data, "rows": [{k: v for k, v in r.items() if k not in HEAVY}
                                              for r in data["rows"]]}
                      for role, data in models.items()}
    details = {role: {"role": role, "rows": [{"id": r["id"], **{k: r.get(k) for k in HEAVY}}
                                             for r in data["rows"]]}
               for role, data in models.items()}
    return {"models": summary_models, "instances": instances, "cascade": routed}, details


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="proofgate export-web")
    parser.add_argument("--offline", action="store_true", help="deterministic stages only")
    parser.add_argument("--only", choices=["graph", "history", "replays", "bench", "arena",
                                           "fixbench"], default=None)
    args = parser.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)

    def write(name: str, data) -> None:
        path = OUT / name
        path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")

    if args.only in (None, "graph"):
        write("graph.json", export_graph())
    if args.only in (None, "history"):
        write("history.json", export_history())
    if args.only in (None, "bench"):
        src = ROOT / "bench" / "results" / "latest.json"
        if src.exists():
            bench = json.loads(src.read_text(encoding="utf-8"))
            write("bench.json", bench)
    if args.only in (None, "fixbench"):
        summary, details = export_fixbench()
        write("fixbench.json", summary)
        for role, detail in details.items():
            write(f"fixbench-{role}.json", detail)
    options = Options(use_llm=not args.offline, sandbox=False, fix=False,
                      prior_art_web=not args.offline)
    if args.only in (None, "replays"):
        write("replays.json", asyncio.run(export_replays(options)))
    if args.only in (None, "arena"):
        write("arena.json", asyncio.run(export_arena(options)))
    return 0
