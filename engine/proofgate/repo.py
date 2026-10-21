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
        "source_dirs": "lib,src,include",
    },
}


def project_meta(project: str) -> dict[str, str]:
    """Known projects, or any git project described by PG_* environment variables
    (this is how the GitHub Action points ProofGate at the repository it runs in)."""
    import os

    if project in PROJECTS:
        return PROJECTS[project]
    url = os.environ.get("PG_REPO_URL", "")
    if not url:
        raise ValueError(f"unknown project {project!r}; set PG_REPO_URL to triage any git repo")
    return {
        "url": url,
        "web": os.environ.get("PG_REPO_WEB", url.removesuffix(".git")),
        "default_branch": os.environ.get("PG_DEFAULT_BRANCH", "main"),
        "tag_prefix": os.environ.get("PG_TAG_PREFIX", "v"),
        "source_dirs": os.environ.get("PG_SOURCE_DIRS", "src,lib,include"),
        "path": os.environ.get("PG_REPO_PATH", ""),
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
        self.project = project
        self.meta = project_meta(project)
        explicit = self.meta.get("path")
        self.path = Path(explicit) if explicit else get_settings().repos_dir / project
        self.source_dirs = tuple(d for d in self.meta.get("source_dirs", "lib,src,include").split(",") if d)
        self._pickaxe_cache: dict[tuple[str, tuple[str, ...], int], list[dict[str, str]]] = {}

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

    @lru_cache(maxsize=1)
    def release_dates(self) -> list[tuple[str, tuple[int, int, int], str]]:
        """(date, version, tag) for every release tag, oldest first."""
        prefix = self.meta["tag_prefix"]
        out = []
        rows = self.git("for-each-ref", "--format=%(creatordate:short) %(refname:short)",
                        f"refs/tags/{prefix}*").splitlines()
        for row in rows:
            date, _, tag = row.partition(" ")
            version = parse_version(tag[len(prefix):].replace("_", "."))
            if version:
                out.append((date, version, tag))
        return sorted(out)

    def release_at(self, date: str) -> tuple[str, str] | None:
        """The newest release published on or before `date` (YYYY-MM-DD...)."""
        day = (date or "")[:10]
        if not day:
            return None
        older = [(v, tag) for d, v, tag in self.release_dates() if d <= day]
        if not older:
            return None
        version, tag = max(older)
        return tag, ".".join(map(str, version))

    def head_at(self, date: str | None) -> str:
        """The default branch as it was on `date` (the code a reporter could have read)."""
        if not date:
            return self.head()
        sha = self.git("rev-list", "-1", f"--before={date[:19]}", self.head(), check=False).strip()
        return sha or self.head()

    def ever_had_file(self, name: str) -> dict[str, str] | None:
        """Last commit that touched a file with this name anywhere in history (deleted files too)."""
        base = name.strip().lstrip("./").rsplit("/", 1)[-1]
        out = self.git("log", self.head(), "-1", "--format=%H\x1f%cs\x1f%s", "--",
                       f"*{base}", check=False).strip()
        parts = out.split("\x1f")
        return {"sha": parts[0], "date": parts[1], "subject": parts[2]} if len(parts) == 3 else None

    def identifier_exists(self, rev: str, name: str) -> GrepHit | None:
        """Any whole-word use of `name` (function, macro, variable, external API) at `rev`."""
        hits = self.grep(rev, name, word=True, limit=1)
        return hits[0] if hits else None

    def resolve(self, version: str | None, as_of: str | None = None) -> tuple[str, str]:
        """Map a claimed version to (rev, label).

        No claimed version -> the newest release on the day the report was filed (`as_of`),
        or the latest release for a report filed now."""
        releases = self.releases()
        if not releases:
            return self.head(), "HEAD"
        wanted = parse_version(version or "")
        if wanted is None:
            dated = self.release_at(as_of) if as_of else None
            if dated:
                return dated
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

    def show_many(self, rev: str, paths: list[str]) -> dict[str, str]:
        """Read many blobs through one `git cat-file --batch` process."""
        proc = subprocess.Popen(
            ["git", "-C", str(self.path), "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        request = "".join(f"{rev}:{p}\n" for p in paths).encode()
        out, _ = proc.communicate(request, timeout=300)
        result: dict[str, str] = {}
        pos = 0
        for path in paths:
            header_end = out.index(b"\n", pos)
            header = out[pos:header_end].split()
            pos = header_end + 1
            if len(header) < 3 or header[1] == b"missing":
                continue
            size = int(header[2])
            result[path] = out[pos : pos + size].decode("utf-8", "replace")
            pos += size + 1  # trailing newline after each object
        return result

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
        paths: tuple[str, ...] | None = None,
        limit: int = 50,
        word: bool = False,
    ) -> list[GrepHit]:
        paths = paths or self.source_dirs
        args = ["grep", "-n", "-I"] + (["-w"] if word else [])
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
        self, needle: str, *, paths: tuple[str, ...] | None = None, limit: int = 5
    ) -> list[dict[str, str]]:
        """Commits anywhere in history that added or removed `needle` (git log -S).

        Cached per (needle, paths): reports cite the same invented names over and over."""
        paths = paths or self.source_dirs
        key = (needle, paths, limit)
        if key in self._pickaxe_cache:
            return self._pickaxe_cache[key]
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
        self._pickaxe_cache[key] = commits
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
