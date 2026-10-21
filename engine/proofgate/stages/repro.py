"""Stage 6 - reproduction: run the reporter's OWN reproduction in an isolated sandbox.

ProofGate never writes or completes an exploit. It only executes what the reporter supplied,
against the project built at the claimed version with sanitizers, with no network and no
secrets, then attributes any crash: inside the project's code, or inside the reporter's code.
"""

from __future__ import annotations

import os
import re

from ..sandbox import get_sandbox, parse_sanitizer
from ..sandbox.base import Job
from ..sandbox.images import build_image, image_exists, image_name
from ..schema import Evidence, SandboxResult
from .base import Context

_PROMPT = re.compile(r"^\s*\$\s+", re.M)
_COMPILE_ERROR = re.compile(r"error: (.+)")
AUTOBUILD = os.environ.get("PG_SANDBOX_AUTOBUILD", "0") == "1"


def plan(ctx: Context) -> Job | None:
    """Turn the report's code blocks into one sandbox job, or None if nothing is runnable."""
    pocs = [b for b in ctx.run.code_blocks if b.role == "poc"]
    shells = [b for b in ctx.run.code_blocks if b.role == "shell"]
    files: dict[str, str] = {}
    steps: list[str] = []
    if pocs:
        files["poc.c"] = pocs[0].text
        steps.append(
            "pg-cc -o poc poc.c > build.log 2>&1; ok=$?; tail -n 40 build.log; "
            "[ $ok -eq 0 ] && echo '--- running poc ---' && ./poc"
        )
    for i, block in enumerate(shells[:2]):
        script = _PROMPT.sub("", block.text)
        lines = [ln for ln in script.splitlines()
                 if ln.strip() and not ln.strip().startswith(("gcc", "clang", "cc "))]
        if lines:
            name = f"step{i + 1}.sh"
            files[name] = "set -x\n" + "\n".join(lines) + "\n"
            steps.append(f"sh {name}")
    if not steps:
        return None
    return Job(files=files, command=" ; ".join(steps), image="", timeout=90)


async def run(ctx: Context) -> None:
    await ctx.event("repro", "start", "Looking for the reporter's reproduction")
    job = plan(ctx)
    if job is None:
        ctx.run.sandbox = SandboxResult(backend="none", ran=False,
                                        log="The report contains no runnable reproduction.")
        await ctx.event("repro", "skipped", "No reproduction steps in the report")
        return
    if not ctx.options.sandbox:
        await ctx.event("repro", "skipped", "Sandbox disabled for this run")
        return

    sandbox = get_sandbox()
    if not await sandbox.available():
        ctx.run.sandbox = SandboxResult(backend=sandbox.name, ran=False, log="sandbox unavailable")
        await ctx.event("repro", "skipped", f"Sandbox backend '{sandbox.name}' is not available")
        return

    rev = ctx.run.resolved_rev or ctx.repo.head()
    job.image = image_name(ctx.run.report.project, rev)
    if sandbox.name == "docker" and not await image_exists(job.image):
        if not AUTOBUILD:
            await ctx.event("repro", "skipped",
                            f"No sanitizer build of {rev} yet (run `proofgate image {rev}`)")
            return
        await ctx.event("repro", "progress", f"Building {rev} with ASan + UBSan (one time)")
        await build_image(ctx.repo, rev)

    await ctx.event("repro", "progress",
                    f"Running in {sandbox.name}: no network, no credentials, read-only root",
                    files=sorted(job.files), command=job.command)
    result = await sandbox.run(job)
    report = parse_sanitizer(result.log)
    result.sanitizer = report
    result.attribution = report["attribution"] if report else "none"
    ctx.run.sandbox = result

    compile_errors = _COMPILE_ERROR.findall(result.log) if "poc.c" in job.files else []
    if compile_errors and "--- running poc ---" not in result.log:
        ctx.run.evidence.append(Evidence(
            claim_id="repro", status="contradicted", method="sandbox-compile",
            detail=f"The reporter's PoC does not compile against curl {ctx.run.resolved_version}: "
                   f"{compile_errors[0][:160]}",
            data={"errors": compile_errors[:5]},
        ))
    elif report and report["attribution"] == "project":
        top = report["top"]
        ctx.run.evidence.append(Evidence(
            claim_id="repro", status="verified", method="sandbox",
            detail=f"{report['tool']} {report['kind']} inside project code at "
                   f"{top['file']}:{top['line']} ({top['function']})",
            file=top["file"], line_start=top["line"], data=report,
        ))
    elif report and report["attribution"] == "reporter":
        top = report["top"]
        ctx.run.evidence.append(Evidence(
            claim_id="repro", status="contradicted", method="sandbox",
            detail=f"The crash ({report['kind']}) happens in the reporter's own code "
                   f"({top['file']}:{top['line']}), not in curl",
            data=report,
        ))
    else:
        ctx.run.evidence.append(Evidence(
            claim_id="repro", status="unverifiable", method="sandbox", deterministic=True,
            detail=f"Reproduction ran (exit {result.exit_code}) without any sanitizer finding",
        ))

    await ctx.event("repro", "done", ctx.run.evidence[-1].detail,
                    exit_code=result.exit_code, attribution=result.attribution,
                    sanitizer=report, log=result.log[-6000:], duration_ms=result.duration_ms)
