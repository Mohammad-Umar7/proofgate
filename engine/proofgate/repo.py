"""Read-only git plumbing over a project's full history.

Everything here answers "what does the code really say at revision X" without a checkout:
`git show rev:path`, `git grep rev`, `git ls-tree rev`, and the pickaxe (`git log -S`) for
"did this code ever exist in any commit".
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .config import get_settings

PROJECTS: dict[str, dict[str, str]] = {
    "curl": {
        "url": "https://github.com/curl/curl.git",
        "web": "https://github.com/curl/curl",
        "default_branch": "master",
        "tag_prefix": "curl-",
    },
}

_VERSION = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


class GitError(RuntimeError):
    pass


def parse_version(text: str) -> tuple[int, int, int] | None:
    match = _VERSION.search(text or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)


@dataclass(frozen=True)
class GrepHit:
    path: str
    line: int
    text: str


class Repo:
    def __init__(self, project: str = "curl") -> None:
        if project not in PROJECTS:
            raise ValueError(f"unknown project {project!r}")
        self.project = project
        self.meta = PROJECTS[project]
        self.path = get_settings().repos_dir / project

    # -- plumbing ---------------------------------------------------------

    def git(self, *args: str, check: bool = True, timeout: int = 120) -> str:
        proc = subprocess.run(
            ["git", "-C", str(self.path), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if check and proc.returncode != 0:
            raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed")
        return proc.stdout

    def ensure(self) -> Path:
        if not (self.path / ".git").exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--quiet", self.meta["url"], str(self.path)], check=True
            )
        return self.path

    def fetch(self) -> None:
        self.git("fetch", "--quiet", "--tags", "origin", timeout=600)

    # -- revisions --------------------------------------------------------

    @lru_cache(maxsize=1)
    def releases(self) -> list[tuple[tuple[int, int, int], str]]:
        """All release tags as (version, tag), oldest first."""
        prefix = self.meta["tag_prefix"]
        out = []
        for tag in self.git("tag", "--list", f"{prefix}*").split():
            version = parse_version(tag[len(prefix) :].replace("_", "."))
            if version:
                out.append((version, tag))
        return sorted(out)

    def head(self) -> str:
        return f"origin/{self.meta['default_branch']}"

    def resolve(self, version: str | None) -> tuple[str, str]:
        """Map a claimed version to (rev, label). Unknown or missing -> latest release."""
        releases = self.releases()
        if not releases:
            return self.head(), "HEAD"
        wanted = parse_version(version or "")
        if wanted is None:
            ver, tag = releases[-1]
            return tag, ".".join(map(str, ver))
        exact = [tag for ver, tag in releases if ver == wanted]
        if exact:
            return exact[0], ".".join(map(str, wanted))
        older = [(ver, tag) for ver, tag in releases if ver <= wanted]
        ver, tag = older[-1] if older else releases[0]
        return tag, ".".join(map(str, ver))

    def version_exists(self, version: str) -> bool:
        wanted = parse_version(version)
        return wanted is not None and any(ver == wanted for ver, _ in self.releases())

    def commit_count(self) -> int:
        return int(self.git("rev-list", "--count", self.head()).strip() or 0)

    def rev_date(self, rev: str) -> str:
        return self.git("log", "-1", "--format=%cs", rev).strip()

    # -- files ------------------------------------------------------------

    def exists(self, rev: str, path: str) -> bool:
        proc = subprocess.run(
            ["git", "-C", str(self.path), "cat-file", "-e", f"{rev}:{path}"],
            capture_output=True,
        )
        return proc.returncode == 0

    def show(self, rev: str, path: str) -> str:
        return self.git("show", f"{rev}:{path}")

    def lines(self, rev: str, path: str) -> list[str]:
        return self.show(rev, path).splitlines()

    @lru_cache(maxsize=64)
    def ls(self, rev: str) -> tuple[str, ...]:
        return tuple(self.git("ls-tree", "-r", "--name-only", rev).splitlines())

    def find_by_name(self, rev: str, name: str) -> list[str]:
        """Locate a file the reporter named loosely ('cookie.c', 'lib/vtls/openssl.c')."""
        name = name.strip().lstrip("./")
        files = self.ls(rev)
        if name in files:
            return [name]
        base = name.rsplit("/", 1)[-1]
        return [f for f in files if f.rsplit("/", 1)[-1] == base]

    # -- search -----------------------------------------------------------

    def grep(
        self,
        rev: str,
        needle: str,
        *,
        fixed: bool = True,
        paths: tuple[str, ...] = ("lib", "src", "include"),
        limit: int = 50,
    ) -> list[GrepHit]:
        args = ["grep", "-n", "-I"]
        args += ["-F"] if fixed else ["-E"]
        args += ["-e", needle, rev, "--", *paths]
        out = self.git(*args, check=False)
        hits: list[GrepHit] = []
        for raw in out.splitlines():
            # rev:path:line:text
            try:
                _, path, line, text = raw.split(":", 3)
                hits.append(GrepHit(path, int(line), text))
            except ValueError:
                continue
            if len(hits) >= limit:
                break
        return hits

    def pickaxe(
        self, needle: str, *, paths: tuple[str, ...] = ("lib", "src", "include"), limit: int = 5
    ) -> list[dict[str, str]]:
        """Commits anywhere in history that added or removed `needle` (git log -S)."""
        out = self.git(
            "log",
            self.head(),
            f"-S{needle}",
            "--format=%H\x1f%cs\x1f%s",
            f"-n{limit}",
            "--",
            *paths,
            check=False,
            timeout=300,
        )
        commits = []
        for row in out.splitlines():
            parts = row.split("\x1f")
            if len(parts) == 3:
                commits.append({"sha": parts[0], "date": parts[1], "subject": parts[2]})
        return commits

    # -- links ------------------------------------------------------------

    def blob_url(self, rev: str, path: str, start: int | None = None, end: int | None = None) -> str:
        url = f"{self.meta['web']}/blob/{rev}/{path}"
        if start:
            url += f"#L{start}"
            if end and end != start:
                url += f"-L{end}"
        return url

    def commit_url(self, sha: str) -> str:
        return f"{self.meta['web']}/commit/{sha}"


@lru_cache(maxsize=4)
def get_repo(project: str = "curl") -> Repo:
    repo = Repo(project)
    repo.ensure()
    return repo
