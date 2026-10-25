"""Build curl at an instance's base commit (plus a patch) and run its own tests, in Docker.

Every run starts from a clean `git archive` of the base commit in a tmpfs, applies the
regression test and the candidate patch, builds with ccache (a shared volume) and runs
`tests/runtests.pl` on the requested test numbers. The container has no network (the test
servers bind to loopback), no capabilities, a read-only root and hard limits.

The slow autotools step (autoreconf + configure, about a minute) runs once per instance; its
outputs are cached on the host and replayed, so a build-and-test cycle is ~30-60 s.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..config import get_settings
from ..repo import get_repo
from .dataset import test_patch

IMAGE = "proofgate/curl-test:3"
CCACHE_VOLUME = "proofgate-ccache"
JOBS = max(1, min(6, os.cpu_count() or 2))
# NTLM is opt-in in recent curl and its tests need it. Memory errors are caught by running the
# regression tests under valgrind (curl's own CI approach); AddressSanitizer is not usable here,
# it crash-loops on kernels with high ASLR entropy such as Docker Desktop's WSL2 kernel.
CONFIGURE = ("--enable-debug --disable-shared --with-openssl --with-libssh2 --with-nghttp2 "
             "--with-libpsl --with-libidn2 --without-brotli --without-zstd --disable-docs "
             "--disable-manual --enable-ntlm")
SAN_ENV: dict[str, str] = {}
_AUTOTOOLS = re.compile(r"^\+\+\+ b/.*(Makefile\.(am|inc)|configure\.ac|\.m4)$", re.M)

PREPARE = r"""
set -e
mkdir -p /work/src && cd /work/src && tar -xf /in/src.tar
patch -p1 -s --no-backup-if-mismatch < /in/tests.patch
touch /work/.stamp && sleep 1
autoreconf -fi > /work/autoreconf.log 2>&1 || { tail -40 /work/autoreconf.log; exit 3; }
./configure {configure} > /work/configure.log 2>&1 || { tail -60 /work/configure.log; exit 4; }
find . -newer /work/.stamp -type f > /work/gen.list
tar -czf /out/gen.tar.gz -T /work/gen.list
echo PG_PREPARED
"""

RUN = r"""
mkdir -p /work/src && cd /work/src && tar -xf /in/src.tar
patch -p1 -s --no-backup-if-mismatch < /in/tests.patch || { echo PG_TESTPATCH_FAILED; exit 0; }
if [ -s /in/fix.patch ]; then
  patch -p1 -f --no-backup-if-mismatch < /in/fix.patch > /work/patch.log 2>&1 \
    || { cat /work/patch.log; echo PG_PATCH_FAILED; exit 0; }
fi
if [ "$PG_FULL" = 1 ]; then
  { autoreconf -fi && ./configure {configure}; } > /work/configure.log 2>&1 \
    || { tail -60 /work/configure.log; echo PG_BUILD_FAILED; exit 0; }
else
  tar -xzf /in/gen.tar.gz && tar -tzf /in/gen.tar.gz | xargs touch
fi
make -j{jobs} > /work/build.log 2>&1 \
  || { grep -E -B2 -A6 "error:|Error [0-9]" /work/build.log | head -n 120; echo PG_BUILD_FAILED; exit 0; }
make -C tests -j{jobs} > /work/tbuild.log 2>&1 \
  || { grep -E -B2 -A6 "error:|Error [0-9]" /work/tbuild.log | head -n 120; echo PG_BUILD_FAILED; exit 0; }
echo PG_BUILD_OK
files=$(grep '^+++ b/' /in/fix.patch | sed 's#^+++ b/##' | grep -E '\.[ch]$' || true)
CS=scripts/checksrc.pl; [ -f "$CS" ] || CS=lib/checksrc.pl
if [ -n "$files" ] && [ -f "$CS" ]; then
  echo PG_CHECKSRC; perl "$CS" $files 2>&1 | tail -n 40; echo PG_CHECKSRC_END
fi
cd tests
: > /work/tests.log
if [ -n "{memcheck}" ]; then perl runtests.pl -a -p {memcheck} >> /work/tests.log 2>&1; fi
if [ -n "{tests}" ]; then perl runtests.pl -a -n -p {tests} >> /work/tests.log 2>&1; fi
grep -E "^test [0-9]+|OK \(|FAILED|SKIPPED|^TEST(DONE|FAIL|INFO)" /work/tests.log | head -n 400
echo PG_LOG_TAIL
tail -c 12000 /work/tests.log
echo PG_DONE
"""


@dataclass
class TestRun:
    __test__ = False  # not a pytest test class

    build_ok: bool
    status: dict[str, str] = field(default_factory=dict)  # test -> ok | fail | skip | missing
    log: str = ""
    seconds: float = 0.0
    stage: str = "tests"  # tests | patch | build | infra

    @property
    def style(self) -> list[str]:
        """Warnings from curl's own checksrc.pl on the files the patch touches."""
        if "PG_CHECKSRC" not in self.log:
            return []
        block = self.log.split("PG_CHECKSRC", 1)[1].split("PG_CHECKSRC_END", 1)[0]
        return [line.strip() for line in block.splitlines()
                if re.search(r":\d+:\d+: (error|warning):", line)]

    def passed(self, tests: list[str]) -> bool:
        return self.build_ok and all(self.status.get(t) == "ok" for t in tests)

    def failing(self, tests: list[str]) -> list[str]:
        return [t for t in tests if self.status.get(t) != "ok"]

    def feedback(self, limit: int = 3500) -> str:
        """What the agent sees: the failing stage and the most useful part of the log."""
        if self.stage == "patch":
            return "Your patch did not apply:\n" + self.log[-limit:]
        if not self.build_ok:
            return "The build failed:\n" + self.log.split("PG_BUILD_FAILED")[0][-limit:]
        summary = ", ".join(f"test{t} {s}" for t, s in sorted(self.status.items()))
        tail = self.log.split("PG_LOG_TAIL")[-1].replace("PG_DONE", "")
        style = ("\ncurl's checksrc.pl style checker: " +
                 (f"{len(self.style)} problem(s):\n" + "\n".join(self.style[:15]) if self.style else "clean"))
        return f"Build OK. {summary}{style}\n--- runtests.pl output (tail) ---\n{tail[-limit:]}"


def parse_runtests(log: str, tests: list[str]) -> dict[str, str]:
    status = {t: "missing" for t in tests}
    current = None
    head = log.split("PG_LOG_TAIL")[0]
    for line in head.splitlines():
        if m := re.match(r"test 0*(\d+) SKIPPED", line):
            status[m.group(1)] = "skip"
            current = None
        elif m := re.match(r"test 0*(\d+)\b", line):  # "test 1876 [name]" or "test 0001...[name]"
            current = m.group(1)
        if current and re.search(r"\bOK \(", line):
            status[current] = "ok"
            current = None
    for failed in re.findall(r"TESTFAIL: These test cases failed: ([\d ]+)", log):
        for t in failed.split():
            status[t.lstrip("0") or "0"] = "fail"
    for t, s in status.items():
        if s == "missing" and re.search(rf"\b0*{t}: \w+ FAILED", log):
            status[t] = "fail"
    return status


def _cache(row: dict) -> Path:
    # keyed by image + configure flags, so changing either re-runs configure
    key = hashlib.sha256(f"{IMAGE} {CONFIGURE}".encode()).hexdigest()[:10]
    path = get_settings().cache_dir / "fixbench" / row["id"] / key
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stage_inputs(tmp: Path, row: dict, fix: str = "") -> None:
    tmp.chmod(0o755)  # on Linux the sandbox's unprivileged user must be able to read /in
    repo = get_repo()
    repo.git("archive", "--format=tar", "-o", str(tmp / "src.tar"), row["base"])
    (tmp / "tests.patch").write_text(test_patch(row["base"], row["fix_commit"]), encoding="utf-8",
                                     newline="\n")
    (tmp / "fix.patch").write_text(fix, encoding="utf-8", newline="\n")


def _docker(tmp: Path, script: str, *, out: Path | None = None, env: dict[str, str] | None = None,
            memory: str = "3g") -> list[str]:
    argv = [
        "docker", "run", "--rm", "--network", "none", "--read-only",
        "--tmpfs", "/work:rw,exec,size=2200m,mode=1777", "--tmpfs", "/tmp:rw,exec,size=256m,mode=1777",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "2048", "--memory", memory, "--cpus", str(JOBS),
        "-v", f"{CCACHE_VOLUME}:/ccache", "-v", f"{tmp}:/in:ro",
    ]
    if out:
        argv += ["-v", f"{out}:/out"]
    for key, value in {**SAN_ENV, **(env or {})}.items():
        argv += ["--env", f"{key}={value}"]
    return argv + [IMAGE, "sh", "-c", script]


async def _exec(argv: list[str], timeout: int) -> tuple[int | None, str]:
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        out, _ = await proc.communicate()
        return None, out.decode("utf-8", "replace") + "\nPG_TIMEOUT"
    return proc.returncode, out.decode("utf-8", "replace")


async def prepare(row: dict) -> Path:
    """Run autoreconf + configure once for this instance and cache the generated files."""
    cache = _cache(row)
    gen = cache / "gen.tar.gz"
    if gen.exists():
        return gen
    cache.chmod(0o777)  # ... and write the generated files to /out
    with tempfile.TemporaryDirectory(prefix="pg-fb-") as tmp:
        _stage_inputs(Path(tmp), row)
        code, log = await _exec(_docker(Path(tmp), PREPARE.replace("{configure}", CONFIGURE),
                                        out=cache), timeout=900)
    if "PG_PREPARED" not in log or not gen.exists():
        (cache / "prepare.log").write_text(log, encoding="utf-8")
        raise RuntimeError(f"{row['id']}: prepare failed ({code}): {log[-600:]}")
    return gen


async def run_tests(row: dict, fix: str, tests: list[str], timeout: int = 1500) -> TestRun:
    """Build base + regression test + `fix` and run `tests`. The instance's own regression
    tests run under valgrind; the nearby tests run without it, for speed."""
    gen = await prepare(row)
    started = time.perf_counter()
    own = set(row.get("fail_to_pass_valid") or row["fail_to_pass"])
    memcheck = [t for t in tests if t in own]
    rest = [t for t in tests if t not in own]
    script = (RUN.replace("{configure}", CONFIGURE).replace("{jobs}", str(JOBS))
              .replace("{memcheck}", " ".join(memcheck)).replace("{tests}", " ".join(rest)))
    with tempfile.TemporaryDirectory(prefix="pg-fb-") as tmp:
        _stage_inputs(Path(tmp), row, fix)
        (Path(tmp) / "gen.tar.gz").write_bytes(gen.read_bytes())
        full = "1" if _AUTOTOOLS.search(fix or "") else "0"
        code, log = await _exec(_docker(Path(tmp), script, env={"PG_FULL": full}), timeout)
    seconds = round(time.perf_counter() - started, 1)
    if "PG_PATCH_FAILED" in log:
        return TestRun(False, log=log, seconds=seconds, stage="patch")
    if "PG_BUILD_OK" not in log:
        stage = "build" if "PG_BUILD_FAILED" in log else "infra"
        return TestRun(False, log=log, seconds=seconds, stage=stage)
    return TestRun(True, parse_runtests(log, tests), log=log, seconds=seconds)


def docker_ready() -> bool:
    try:
        return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True,
                              timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
