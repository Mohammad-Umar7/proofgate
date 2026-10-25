"""FixBench driver: validate instances, run the agent, grade, and publish the metrics.

  proofgate fixbench build                  rebuild bench/fixbench.jsonl from curl's advisories
  proofgate fixbench validate               keep instances whose test fails on base, passes with the fix
  proofgate fixbench run --model super      run the agent on every validated instance
  proofgate fixbench table                  print the results table

Grading is strict: an instance is resolved only if every fail-to-pass test now passes and every
pass-to-pass test still passes, on a fresh build of the agent's final diff.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from dataclasses import asdict

from ..config import ENGINE_DIR
from .agent import solve
from .dataset import area_tests, build_index, gold_patch, load_index, save_index
from .harness import prepare, run_tests

RESULTS = ENGINE_DIR.parent / "bench" / "results"


async def validate(rows: list[dict], concurrency: int = 3, only: list[str] | None = None,
                   log=print) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)
    todo = [r for r in rows if not only or r["id"] in only]

    async def one(row: dict) -> None:
        async with sem:
            started = time.perf_counter()
            try:
                await prepare(row)
                area = area_tests(row)
                tests = row["fail_to_pass"] + area
                gold = await run_tests(row, gold_patch(row["base"], row["fix_commit"]), tests)
                base = await run_tests(row, "", tests)
            except Exception as exc:  # noqa: BLE001 - an instance that cannot build is dropped
                row.update(validated=False, why=f"error: {str(exc)[:200]}")
                log(f"  {row['id']:<16} error {str(exc)[:120]}")
                return
            if not gold.build_ok or not base.build_ok:
                row.update(validated=False,
                           why=f"build failed ({'gold' if not gold.build_ok else 'base'}: {gold.stage}/{base.stage})")
            else:
                f2p = [t for t in row["fail_to_pass"]
                       if base.status.get(t) == "fail" and gold.status.get(t) == "ok"]
                p2p = [t for t in tests if t not in f2p
                       and base.status.get(t) == "ok" and gold.status.get(t) == "ok"]
                row.update(validated=bool(f2p), fail_to_pass_valid=f2p, pass_to_pass=p2p,
                           validation={"base": base.status, "gold": gold.status},
                           why="" if f2p else "regression test does not fail on the base commit")
            log(f"  {row['id']:<16} {'valid' if row['validated'] else 'dropped':<8} "
                f"f2p={row.get('fail_to_pass_valid')} p2p={len(row.get('pass_to_pass') or [])} "
                f"{row.get('why', '')} {time.perf_counter() - started:.0f}s")

    await asyncio.gather(*(one(r) for r in todo))
    save_index(rows)
    return rows


def _files(diff: str) -> set[str]:
    return {line[6:].strip() for line in diff.splitlines() if line.startswith("+++ b/")}


def _step_dict(step) -> dict:
    data = asdict(step)
    data["observation"] = data["observation"][:1800]
    if "body" in data["args"]:
        data["args"]["body"] = data["args"]["body"][:2500]
    return data


async def run_one(row: dict, role: str, budget: float, log=print) -> dict:
    f2p, p2p = row["fail_to_pass_valid"], row["pass_to_pass"]
    tests = f2p + p2p
    result = await solve(row, tests, role=role, budget_usd=budget)
    grade = None
    if result.diff:
        if result.last_test and result.last_test_diff == result.diff:
            grade = result.last_test  # the agent's last test run already built exactly this diff
        else:
            grade = await run_tests(row, result.diff, tests)
    resolved = bool(grade and grade.passed(tests))
    gold = gold_patch(row["base"], row["fix_commit"])
    gold_files = {f for f in _files(gold) if f.startswith(("lib/", "src/", "include/"))}
    edited = _files(result.diff)
    out = {
        "id": row["id"], "summary": row["summary"], "severity": row.get("severity"),
        "published": row.get("published"), "fix_date": row.get("fix_date"),
        "fix_commit": row["fix_commit"], "base": row["base"],
        "advisory_url": row.get("advisory_url"), "model": result.model, "role": role,
        "resolved": resolved,
        "f2p_passed": bool(grade and grade.passed(f2p)),
        "p2p_broken": grade.failing(p2p) if grade and grade.build_ok else [],
        "build_ok": bool(grade and grade.build_ok),
        "first_test_passed": result.first_test_passed,
        "tests_run": result.tests_run, "turns": max((s.turn for s in result.steps), default=0),
        "stop": result.stop, "cost_usd": round(result.cost_usd, 5), "tokens": result.tokens,
        "seconds": result.seconds,
        "localized": bool(edited & gold_files), "files_edited": sorted(edited),
        "gold_files": sorted(gold_files),
        "diff": result.diff, "gold_diff": gold, "summary_agent": result.summary,
        "fail_to_pass": f2p, "pass_to_pass": len(p2p),
        "steps": [_step_dict(s) for s in result.steps],
    }
    log(f"  {row['id']:<16} {'RESOLVED' if resolved else 'unresolved':<10} "
        f"turns={out['turns']} tests={result.tests_run} stop={result.stop} "
        f"${result.cost_usd:.3f} {result.seconds:.0f}s files={sorted(edited)}")
    return out


def metrics(rows: list[dict]) -> dict:
    n = len(rows)
    resolved = [r for r in rows if r["resolved"]]
    costs = [r["cost_usd"] for r in rows]
    return {
        "n": n,
        "resolved": len(resolved),
        "resolved_rate": round(len(resolved) / max(1, n), 3),
        "first_try": sum(1 for r in rows if r["first_test_passed"]),
        "localized": round(sum(r["localized"] for r in rows) / max(1, n), 3),
        "build_ok": round(sum(r["build_ok"] for r in rows) / max(1, n), 3),
        "broke_other_tests": sum(1 for r in rows if r["f2p_passed"] and r["p2p_broken"]),
        "cost_total_usd": round(sum(costs), 4),
        "cost_mean_usd": round(statistics.mean(costs), 4) if costs else 0.0,
        "cost_per_resolved_usd": round(sum(costs) / len(resolved), 4) if resolved else None,
        "turns_mean": round(statistics.mean(r["turns"] for r in rows), 1) if rows else 0,
        "tests_mean": round(statistics.mean(r["tests_run"] for r in rows), 1) if rows else 0,
        "seconds_mean": round(statistics.mean(r["seconds"] for r in rows), 1) if rows else 0,
        # fixes committed after the model's training data ends cannot have been memorized
        "post_cutoff": {"cutoff": TRAINING_CUTOFF,
                        "n": sum(1 for r in rows if _after_cutoff(r)),
                        "resolved": sum(1 for r in resolved if _after_cutoff(r))},
    }


# Nemotron 3 Super model card (NVIDIA NIM reference, "Data Freshness"): pre-training data to
# June 2025, post-training data to February 2026.
TRAINING_CUTOFF = "2026-03-01"


def _after_cutoff(row: dict) -> bool:
    return (row.get("fix_date") or row.get("published") or "") >= TRAINING_CUTOFF


async def run_bench(role: str, limit: int | None, concurrency: int, budget: float,
                    only: list[str] | None = None, log=print) -> dict:
    rows = [r for r in load_index() if r.get("validated")]
    if only:
        rows = [r for r in rows if r["id"] in only]
    if limit:
        rows = rows[:limit]
    sem = asyncio.Semaphore(concurrency)
    results: list[dict] = []

    async def worker(row: dict) -> None:
        async with sem:
            try:
                results.append(await run_one(row, role, budget, log))
            except Exception as exc:  # noqa: BLE001 - record and keep going
                log(f"  {row['id']}: error {exc}")

    await asyncio.gather(*(worker(r) for r in rows))
    results.sort(key=lambda r: r["published"] or "", reverse=True)
    summary = {"role": role, "model": results[0]["model"] if results else None,
               "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "metrics": metrics(results), "rows": results}
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"fixbench-{role}.json"
    if only and path.exists():  # partial rerun: merge into the existing results
        old = json.loads(path.read_text(encoding="utf-8"))
        keep = [r for r in old["rows"] if r["id"] not in {x["id"] for x in results}]
        summary["rows"] = sorted(keep + results, key=lambda r: r["published"] or "", reverse=True)
        summary["metrics"] = metrics(summary["rows"])
    path.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def table() -> str:
    lines = ["| Agent model (Token Factory) | Resolved | Fixed on 1st test run | Edited the right file | "
             "Broke other tests | Cost / CVE | Cost / fix | Time / CVE |",
             "|---|---|---|---|---|---|---|---|"]
    for role in ("nano", "super", "ultra"):
        path = RESULTS / f"fixbench-{role}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        m = data["metrics"]
        per_fix = f"${m['cost_per_resolved_usd']:.3f}" if m["cost_per_resolved_usd"] else "n/a"
        lines.append(
            f"| `{data['model']}` | **{m['resolved']} / {m['n']}** ({m['resolved_rate'] * 100:.0f}%) "
            f"| {m['first_try']} | {m['localized'] * 100:.0f}% | {m['broke_other_tests']} "
            f"| ${m['cost_mean_usd']:.3f} | {per_fix} | {m['seconds_mean'] / 60:.1f} min |")
    index = load_index()
    valid = sum(1 for r in index if r.get("validated"))
    lines.append(f"\n_{valid} of {len(index)} candidate CVEs validated (regression test fails on the "
                 f"vulnerable commit and passes with curl's fix in the sandbox). Generated "
                 f"{time.strftime('%Y-%m-%d')} by `proofgate fixbench table`._")
    return "\n".join(lines)


def update_readme() -> None:
    readme = RESULTS.parent.parent / "README.md"
    text = readme.read_text(encoding="utf-8")
    start, end = "<!-- FIXBENCH:START -->", "<!-- FIXBENCH:END -->"
    if start not in text:
        return
    before, _, rest = text.partition(start)
    _, _, after = rest.partition(end)
    readme.write_text(f"{before}{start}\n{table()}\n{end}{after}", encoding="utf-8")


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="proofgate fixbench")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    val = sub.add_parser("validate")
    val.add_argument("--concurrency", type=int, default=3)
    val.add_argument("--only", nargs="*", default=None, help="instance ids (CVE-...)")
    run = sub.add_parser("run")
    run.add_argument("--model", choices=("nano", "super", "ultra"), default="super")
    run.add_argument("--limit", type=int, default=None)
    run.add_argument("--only", nargs="*", default=None, help="instance ids (CVE-...)")
    run.add_argument("--concurrency", type=int, default=3)
    run.add_argument("--budget", type=float, default=0.6, help="max USD per instance")
    sub.add_parser("table")
    args = parser.parse_args(argv)

    if args.cmd == "build":
        rows = build_index()
        print(f"{len(rows)} candidate instances")
    elif args.cmd == "validate":
        rows = asyncio.run(validate(load_index(), args.concurrency, args.only))
        print(f"{sum(bool(r.get('validated')) for r in rows)} / {len(rows)} instances validated")
    elif args.cmd == "run":
        summary = asyncio.run(run_bench(args.model, args.limit, args.concurrency, args.budget,
                                        args.only))
        print(json.dumps(summary["metrics"], indent=1))
    else:
        update_readme()
        print(table())
    return 0
