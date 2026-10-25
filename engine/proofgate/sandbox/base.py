"""Sandbox backends. All of them: no network, no credentials, ephemeral, resource-limited."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from ..config import get_settings
from ..schema import SandboxResult

DEFAULT_TIMEOUT = 60
MAX_LOG = 64_000


@dataclass
class Job:
    files: dict[str, str]  # name -> content, copied into the sandbox work dir
    command: str  # run with `sh -c` inside the sandbox
    image: str
    timeout: int = DEFAULT_TIMEOUT
    work_size: str = "128m"  # tmpfs for /work; the fix loop needs room for a source tree


class Sandbox:
    name = "off"

    async def available(self) -> bool:
        return False

    async def run(self, job: Job) -> SandboxResult:
        return SandboxResult(backend=self.name, ran=False, log="sandbox disabled")


class DockerSandbox(Sandbox):
    """`docker run` with networking disabled, a read-only root, dropped capabilities and limits."""

    name = "docker"

    async def available(self) -> bool:
        if not shutil.which("docker"):
            return False
        proc = await asyncio.create_subprocess_exec(
            "docker", "info", "--format", "{{.ServerVersion}}",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        return await proc.wait() == 0

    def argv(self, job: Job, workdir: Path) -> list[str]:
        return [
            "docker", "run", "--rm",
            "--network", "none",
            "--read-only",
            "--tmpfs", f"/work:rw,exec,size={job.work_size},mode=1777",
            "--tmpfs", "/tmp:rw,size=64m,mode=1777",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--pids-limit", "256",
            "--memory", "1g",
            "--cpus", "2",
            "--env", "ASAN_OPTIONS=detect_leaks=1:abort_on_error=0:symbolize=1",
            "--env", "UBSAN_OPTIONS=print_stacktrace=1",
            "-v", f"{workdir}:/in:ro",
            job.image,
            "sh", "-c", f"cp -r /in/. /work/ && cd /work && {job.command}",
        ]

    async def run(self, job: Job) -> SandboxResult:
        with tempfile.TemporaryDirectory(prefix="pg-sbx-") as tmp:
            workdir = Path(tmp)
            for name, content in job.files.items():
                target = workdir / Path(name).name  # flatten: no path traversal into the host
                target.write_text(content, encoding="utf-8")
            started = time.perf_counter()
            proc = await asyncio.create_subprocess_exec(
                *self.argv(job, workdir),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            timed_out = False
            try:
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=job.timeout)
            except asyncio.TimeoutError:
                timed_out = True
                proc.kill()
                out, _ = await proc.communicate()
            return SandboxResult(
                backend=self.name,
                ran=True,
                exit_code=None if timed_out else proc.returncode,
                timed_out=timed_out,
                network="none",
                duration_ms=int((time.perf_counter() - started) * 1000),
                log=out.decode("utf-8", "replace")[-MAX_LOG:],
            )


def get_sandbox() -> Sandbox:
    choice = get_settings().sandbox.lower()
    if choice == "openshell":
        from .openshell import OpenShellSandbox

        return OpenShellSandbox()
    if choice == "docker":
        return DockerSandbox()
    return Sandbox()
