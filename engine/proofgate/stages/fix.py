"""Stage 8 - triage to fix: for a reproduced bug, write a regression test and a patch, then
build and test the patched project in the sandbox, iterating on failures.

The agent loop: Nemotron Super drafts (test + unified diff) -> `git apply --check` against the
exact release -> rebuild inside the sandbox -> rerun the reporter's reproduction (must be clean)
-> run the project's own tests for that area -> feed any failure back, up to MAX_ITERATIONS.
The result is a patch file and an optional draft PR on a fork; a maintainer reviews everything.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from ..sandbox import get_sandbox, parse_sanitizer
from ..sandbox.base import Job
from ..sandbox.images import image_exists, image_name
from ..schema import FixAttempt, Verdict
from .base import Context
from .repro import plan

MAX_ITERATIONS = 3
_DIFF = re.compile(r"```(?:diff|patch)?\n(.*?)```", re.S)

FIX_SYSTEM = """You are a careful C maintainer of {project}. A bug was reproduced in the sandbox:
the sanitizer report and the real source of the affected function are below. Write:
1. a minimal patch as a unified diff against the given files (paths relative to the repo root,
   with a/ and b/ prefixes), changing as little as possible and matching the code style;
2. a one-paragraph commit message.
Return JSON: {{"patch": "<unified diff>", "message": "<commit message>",
"test_keyword": "<one keyword of the project's test suite for this area, e.g. cookies>"}}
Do not change unrelated code. Do not add new dependencies."""


def _function_source(ctx: Context) -> tuple[str, str]:
    report = ctx.run.sandbox.sanitizer if ctx.run.sandbox else None
    top = (report or {}).get("top") or {}
    path = (top.get("file") or "").split("/build/curl/")[-1].lstrip("/")
    if not path:
        return "", ""
    rev = ctx.run.resolved_rev or ctx.repo.head()
    try:
        lines = ctx.repo.lines(rev, path)
    except Exception:  # noqa: BLE001
        return path, ""
    line = int(top.get("line") or 1)
    lo, hi = max(1, line - 80), min(len(lines), line + 80)
    numbered = "\n".join(f"{i:5d}  {lines[i - 1]}" for i in range(lo, hi + 1))
    return path, numbered


def apply_check(ctx: Context, patch: str) -> tuple[bool, str]:
    """Check the patch applies cleanly to the exact release, using a throwaway worktree."""
    rev = ctx.run.resolved_rev or ctx.repo.head()
    with tempfile.TemporaryDirectory(prefix="pg-fix-") as tmp:
        tree = Path(tmp) / "tree"
        ctx.repo.git("worktree", "add", "--detach", str(tree), rev)
        try:
            patch_file = Path(tmp) / "fix.patch"
            patch_file.write_text(patch, encoding="utf-8")
            proc = subprocess.run(["git", "-C", str(tree), "apply", "--check", str(patch_file)],
                                  capture_output=True, text=True)
            return proc.returncode == 0, proc.stderr.strip()[-600:]
        finally:
            ctx.repo.git("worktree", "remove", "--force", str(tree), check=False)


def verify_job(ctx: Context, patch: str, keyword: str) -> Job:
    repro = plan(ctx)
    files = dict(repro.files) if repro else {}
    files["fix.patch"] = patch
    steps = [
        "{ cp -a /build/curl /work/src && cd /work/src && patch -p1 < /work/fix.patch "
        "&& make -j4 -s > /work/build.log 2>&1; } "
        "|| { tail -n 60 /work/build.log 2>/dev/null; echo PG_BUILD_FAILED; exit 90; }",
        "echo PG_BUILD_OK",
        "export PATH=/work/src/src:$PATH",
        "cd /work",
    ]
    if "poc.c" in files:
        steps.append("cc $SAN_FLAGS -I/work/src/include poc.c /work/src/lib/.libs/libcurl.a "
                     "-lssl -lcrypto -lz -lpthread -o poc && ./poc; echo PG_REPRO_EXIT=$?")
    for name in sorted(f for f in files if f.startswith("step")):
        steps.append(f"sh {name}; echo PG_REPRO_EXIT=$?")
    if keyword:
        safe = re.sub(r"[^A-Za-z0-9_-]", "", keyword)[:24]
        steps.append(f"cd /work/src/tests && (make -s -j4 > /dev/null 2>&1; "
                     f"perl runtests.pl -a -n {safe} 2>&1 | tail -n 25)")
    return Job(files=files, command=" ; ".join(steps),
               image=image_name(ctx.run.report.project, ctx.run.resolved_rev or "head"),
               timeout=900, work_size="2g")


async def run(ctx: Context) -> None:
    decision = ctx.run.decision
    if not decision or decision.verdict != Verdict.REPRODUCED or not ctx.options.fix:
        await ctx.event("fix", "skipped", "Only reproduced reports go to the fix loop")
        return
    if not ctx.llm_on:
        await ctx.event("fix", "skipped", "Fix loop needs Token Factory (NEBIUS_API_KEY)")
        return
    sandbox = get_sandbox()
    image = image_name(ctx.run.report.project, ctx.run.resolved_rev or "head")
    if sandbox.name != "docker" or not await image_exists(image):
        await ctx.event("fix", "skipped", "Fix loop needs the Docker sandbox image for this release")
        return

    await ctx.event("fix", "start", "Writing a regression test and a patch")
    path, source = _function_source(ctx)
    feedback = ""
    for iteration in range(1, MAX_ITERATIONS + 1):
        data, calls = await ctx.llm.chat_json(
            stage="fix", role=ctx.role("super"),
            system=FIX_SYSTEM.format(project=ctx.run.report.project),
            user=(f"SANITIZER REPORT:\n{ctx.run.sandbox.log[-4000:]}\n\n"
                  f"SOURCE {path}:\n{source}\n\n{feedback}"),
            max_tokens=2500, reasoning=True, budget=ctx.budget,
        )
        ctx.record(calls)
        patch = str(data.get("patch") or "")
        if "```" in patch:
            match = _DIFF.search(patch)
            patch = match.group(1) if match else patch
        if not patch.endswith("\n"):
            patch += "\n"
        ok, err = apply_check(ctx, patch)
        if not ok:
            feedback = f"Your previous patch did not apply: {err}\nReturn a corrected patch."
            ctx.run.fix.append(FixAttempt(iteration=iteration, patch=patch, test="",
                                          build_ok=False, repro_fixed=False, suite_passed=False,
                                          log=err))
            await ctx.event("fix", "progress", f"Attempt {iteration}: patch does not apply, retrying")
            continue

        await ctx.event("fix", "progress", f"Attempt {iteration}: patch applies; rebuilding in sandbox")
        result = await sandbox.run(verify_job(ctx, patch, str(data.get("test_keyword") or "")))
        log = result.log
        build_ok = "PG_BUILD_OK" in log
        still_crashes = parse_sanitizer(log) is not None
        suite_failed = bool(re.search(r"TESTFAIL|FAILED", log))
        attempt = FixAttempt(iteration=iteration, patch=patch, test=data.get("test_keyword") or "",
                             build_ok=build_ok, repro_fixed=build_ok and not still_crashes,
                             suite_passed=build_ok and not suite_failed, log=log[-6000:])
        ctx.run.fix.append(attempt)
        if attempt.build_ok and attempt.repro_fixed and attempt.suite_passed:
            ctx.run.notes["fix_message"] = data.get("message")
            await ctx.event("fix", "done",
                            f"Patch verified on attempt {iteration}: builds, reproduction is clean, "
                            "area tests pass", patch=patch, iteration=iteration)
            return
        feedback = ("Your previous patch " +
                    ("did not build" if not build_ok else
                     "still triggers the sanitizer" if still_crashes else "broke existing tests") +
                    f". Log tail:\n{log[-2500:]}\nReturn a corrected patch.")
        await ctx.event("fix", "progress", f"Attempt {iteration} failed verification; iterating")
    await ctx.event("fix", "done", f"No verified patch after {MAX_ITERATIONS} attempts; "
                                   "a maintainer should take it from here")
