"""Build and look up sanitizer images of the project at an exact release tag."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..repo import Repo

DOCKERFILE = Path(__file__).with_name("Dockerfile.curl-asan")


def image_name(project: str, rev: str) -> str:
    return f"proofgate/{project}-asan:{rev.replace('/', '-').lower()}"


async def image_exists(name: str) -> bool:
    if not shutil.which("docker"):
        return False
    proc = await asyncio.create_subprocess_exec(
        "docker", "image", "inspect", name,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    return await proc.wait() == 0


async def build_image(repo: Repo, rev: str, log=print) -> str:
    """`git archive` the tag into a temp context and build the sanitizer image (minutes)."""
    name = image_name(repo.project, rev)
    with tempfile.TemporaryDirectory(prefix="pg-img-") as tmp:
        ctx = Path(tmp)
        archive = subprocess.run(
            ["git", "-C", str(repo.path), "archive", "--format=tar", rev],
            capture_output=True, check=True,
        ).stdout
        subprocess.run(["tar", "-x", "-C", str(ctx)], input=archive, check=True)
        shutil.copy(DOCKERFILE, ctx / "Dockerfile.proofgate")
        proc = await asyncio.create_subprocess_exec(
            "docker", "build", "-q", "-t", name, "-f", str(ctx / "Dockerfile.proofgate"), str(ctx),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"image build failed: {out.decode(errors='replace')[-800:]}")
    log(f"built {name}")
    return name
