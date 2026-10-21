"""NVIDIA OpenShell backend: one ephemeral, policy-enforced sandbox per reproduction.

OpenShell sandboxes start with outbound network denied by default; ProofGate never adds a
network policy, so the reporter's code runs with no egress and no credentials (no providers are
attached). Uses the official Python SDK (`pip install openshell`) against the gateway the
OpenShell CLI registered (`openshell gateway ...`), or PG_OPENSHELL_ENDPOINT for host:port.
"""

from __future__ import annotations

import asyncio
import io
import os
import tarfile
import time
import uuid

from ..schema import SandboxResult
from .base import MAX_LOG, Job, Sandbox

WORKSPACE = os.environ.get("PG_OPENSHELL_WORKSPACE", "default")
TEMPLATE = os.environ.get("PG_OPENSHELL_TEMPLATE", "")  # workload template with build tools
ENDPOINT = os.environ.get("PG_OPENSHELL_ENDPOINT", "")
WORKDIR = "/tmp/proofgate"


def _tarball(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=os.path.basename(name))
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class OpenShellSandbox(Sandbox):
    name = "openshell"

    def _client(self):
        from openshell import SandboxClient  # optional dependency

        return SandboxClient(ENDPOINT) if ENDPOINT else SandboxClient.from_active_cluster()

    async def available(self) -> bool:
        def probe() -> bool:
            try:
                with self._client() as client:
                    client.health()
                return True
            except Exception:  # noqa: BLE001 - SDK missing or gateway down
                return False

        return await asyncio.to_thread(probe)

    def _run_sync(self, job: Job) -> SandboxResult:
        name = f"proofgate-{uuid.uuid4().hex[:10]}"
        started = time.perf_counter()
        with self._client() as client:
            if TEMPLATE:
                session = client.create_session_from_template(
                    workspace=WORKSPACE, workload_template=TEMPLATE, name=name,
                    labels={"app": "proofgate", "purpose": "repro"},
                )
            else:
                session = client.create_session(
                    workspace=WORKSPACE, name=name,
                    labels={"app": "proofgate", "purpose": "repro"},
                )
            try:
                client.wait_ready(name, workspace=WORKSPACE, timeout_seconds=180)
                unpack = session.exec(
                    ["sh", "-c", f"mkdir -p {WORKDIR} && tar -x -C {WORKDIR}"],
                    stdin=_tarball(job.files),
                    timeout_seconds=60,
                )
                if unpack.exit_code != 0:
                    raise RuntimeError(f"could not stage files: {unpack.stderr[:300]}")
                result = session.exec(
                    ["sh", "-c", job.command],
                    workdir=WORKDIR,
                    env={
                        "ASAN_OPTIONS": "detect_leaks=1:abort_on_error=0:symbolize=1",
                        "UBSAN_OPTIONS": "print_stacktrace=1",
                    },
                    timeout_seconds=job.timeout,
                )
                timed_out = result.exit_code in (124, 137) and \
                    (time.perf_counter() - started) >= job.timeout
                return SandboxResult(
                    backend=self.name,
                    ran=True,
                    exit_code=result.exit_code,
                    timed_out=timed_out,
                    network="denied (OpenShell default policy)",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    log=(result.stdout + result.stderr)[-MAX_LOG:],
                )
            finally:
                session.delete(allow_missing=True)

    async def run(self, job: Job) -> SandboxResult:
        try:
            return await asyncio.to_thread(self._run_sync, job)
        except Exception as exc:  # noqa: BLE001
            return SandboxResult(backend=self.name, ran=False, log=f"OpenShell error: {exc}")
