"""`proofgate` command line: check a report, serve the API, export the code galaxy, run arena."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .schema import Report, StageEvent
from .stages.base import Options

ICONS = {"start": "->", "progress": "  ", "done": "OK", "skipped": "--", "error": "!!"}


async def _print_event(event: StageEvent) -> None:
    if event.status in ("start", "done", "skipped", "error") or event.stage == "grounding":
        cost = f"${event.cost_usd:.4f}" if event.cost_usd else ""
        print(f"{ICONS[event.status]} {event.stage:<10} {event.message[:110]} {cost}", flush=True)


def _load_report(path: str) -> Report:
    text = Path(path).read_text(encoding="utf-8") if path != "-" else sys.stdin.read()
    if path.endswith(".json"):
        return Report(**json.loads(text))
    first, _, rest = text.partition("\n")
    return Report(title=first.lstrip("# ").strip(), body=rest.strip())


async def _check(args: argparse.Namespace) -> int:
    from . import store
    from .pipeline import execute

    options = Options(use_llm=not args.offline, grounding=not args.no_grounding,
                      sandbox=not args.no_sandbox, fix=args.fix)
    run = await execute(_load_report(args.report), options, None if args.json else _print_event)
    store.save(run, source="cli")
    card = run.notes.get("card", {})
    if args.json:
        print(json.dumps(card, indent=2))
    else:
        print(f"\n{card.get('verdict')}  ({card.get('confidence')})  {card.get('headline')}")
        for reason in card.get("reasons", []):
            print(f"  - {reason}")
        print(f"\ncost ${card.get('cost_usd', 0):.4f}  time {card.get('seconds')}s  run {run.id}")
    return 0 if card.get("verdict") else 1


async def _arena(args: argparse.Namespace) -> int:
    from .arena import red_team_report, template_report
    from .pipeline import execute

    caught = 0
    for level in range(1, 6):
        report = template_report(level, seed=args.seed) if args.offline else \
            await red_team_report(level, seed=args.seed)
        run = await execute(report, Options(use_llm=not args.offline, fix=False))
        verdict = run.decision.verdict.value if run.decision else "?"
        ok = verdict in ("UNGROUNDED", "NEEDS_INFO")
        caught += ok
        flag = " [injection flagged]" if "prompt-injection" in run.flags else ""
        print(f"level {level}: {'CAUGHT ' if ok else 'FOOLED '} {verdict:<11} {report.title[:70]}{flag}")
    print(f"\nProofGate {caught}/5 vs red team")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="proofgate", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="triage one report (.md: first line is the title, or .json)")
    check.add_argument("report")
    check.add_argument("--json", action="store_true")
    check.add_argument("--offline", action="store_true", help="deterministic stages only")
    check.add_argument("--no-grounding", action="store_true", help="ablation")
    check.add_argument("--no-sandbox", action="store_true")
    check.add_argument("--fix", action="store_true", help="run the fix loop on reproduced bugs")

    sub.add_parser("serve", help="run the API server")

    graph = sub.add_parser("graph", help="export the code galaxy JSON for a version")
    graph.add_argument("--version", default=None)
    graph.add_argument("-o", "--out", default="-")

    image = sub.add_parser("image", help="build the sanitizer sandbox image for a release tag")
    image.add_argument("rev")

    arena = sub.add_parser("arena", help="red team vs ProofGate, five rounds")
    arena.add_argument("--offline", action="store_true")
    arena.add_argument("--seed", type=int, default=7)

    sub.add_parser("bench", help="SlopBench: build | fetch | run --config ...", add_help=False)

    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "bench":
        from .bench.run import main as bench_main

        return bench_main(argv[1:])
    args = parser.parse_args(argv)
    if args.cmd == "check":
        return asyncio.run(_check(args))
    if args.cmd == "serve":
        from .server import main as serve

        serve()
        return 0
    if args.cmd == "graph":
        from .codeindex import get_index
        from .repo import get_repo

        repo = get_repo("curl")
        rev, label = repo.resolve(args.version)
        data = get_index(repo, rev).export_graph()
        data["version"] = label
        text = json.dumps(data, separators=(",", ":"))
        if args.out == "-":
            print(text)
        else:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"wrote {args.out}: {len(data['nodes'])} functions, {len(data['edges'])} calls")
        return 0
    if args.cmd == "image":
        from .repo import get_repo
        from .sandbox.images import build_image

        asyncio.run(build_image(get_repo("curl"), args.rev))
        return 0
    if args.cmd == "arena":
        return asyncio.run(_arena(args))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
