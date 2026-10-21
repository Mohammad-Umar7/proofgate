"""Stage 3 - grounding: check every claim against the real code at the claimed version.

Deterministic checks first (git + tree-sitter, zero tokens), then Nemotron Super reasons over the
real source of the functions involved. Only deterministic checks can produce a `contradicted`
status that is allowed to sink a report.
"""

from __future__ import annotations

import re

from ..codeindex import get_index
from ..repo import Repo
from ..schema import Claim, Evidence
from ..security import fence, guard, new_tag
from .base import Context
from .intake import full_text

LIBC = {
    "strcpy", "strcat", "sprintf", "vsprintf", "gets", "memcpy", "memmove", "strncpy", "strncat",
    "malloc", "calloc", "realloc", "free", "printf", "fprintf", "snprintf", "strlen", "strdup",
    "sscanf", "atoi", "strtok", "system", "popen", "fopen", "read", "write", "recv", "send",
}
_WS = re.compile(r"\s+")
_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def normalize(line: str) -> str:
    return _WS.sub(" ", _COMMENT.sub("", line)).strip()


def significant_lines(code: str) -> list[str]:
    out = []
    for raw in _COMMENT.sub("", code).splitlines():
        line = normalize(raw)
        if len(line) >= 12 and line not in ("{", "}", "else {", "} else {", "return result;"):
            out.append(line)
    return out


_ERE_SPECIAL = set(".[]()*+?{}|^$\\")


def _ws_tolerant(line: str) -> str:
    """POSIX ERE matching `line` with any amount of whitespace between its tokens."""
    tokens = [t for t in re.split(r"\s+", line.strip()) if t]
    esc = ["".join("\\" + ch if ch in _ERE_SPECIAL else ch for ch in t) for t in tokens]
    return "[[:space:]]*".join(esc)


def _longest_token(line: str) -> str:
    return max(re.split(r"\s+", line.strip()), key=len, default="")


def _context(repo: Repo, rev: str, path: str, start: int, end: int) -> str:
    lines = repo.lines(rev, path)
    lo, hi = max(1, start), min(len(lines), end)
    return "\n".join(lines[lo - 1 : hi])


class Grounder:
    def __init__(self, ctx: Context, rev: str, version: str) -> None:
        self.ctx = ctx
        self.repo = ctx.repo
        self.rev = rev
        self.version = version
        self.index = get_index(self.repo, rev)
        # the code a reporter could have been reading: master on the day the report was filed
        self.head_rev = self.repo.head_at(ctx.run.report.submitted_at)
        self.files: dict[str, str] = {}  # claimed name -> resolved path

    def ev(self, claim: Claim, status: str, method: str, detail: str, **kw) -> Evidence:
        evidence = Evidence(claim_id=claim.id, status=status, method=method, detail=detail,
                            rev=self.rev, **kw)
        self.ctx.run.evidence.append(evidence)
        return evidence

    # -- individual checks ------------------------------------------------

    def check_version(self, claim: Claim) -> None:
        if self.repo.version_exists(claim.version or ""):
            self.ev(claim, "verified", "git-tags", f"curl {claim.version} is a real release")
            return
        latest = ".".join(map(str, self.repo.releases()[-1][0]))
        self.ev(claim, "contradicted", "git-tags",
                f"curl {claim.version} was never released (latest release is {latest})",
                data={"latest": latest})

    def check_file(self, claim: Claim) -> str | None:
        name = claim.file or ""
        found = self.repo.find_by_name(self.rev, name)
        if found:
            path = found[0]
            self.files[name] = path
            exact = path == name.lstrip("./")
            self.ev(claim, "verified" if exact else "partial", "git-ls-tree",
                    f"{path} exists at {self.version}" + ("" if exact else f" (reporter wrote {name})"),
                    file=path, url=self.repo.blob_url(self.rev, path))
            return path
        for rev, label in ((self.head_rev, "master on the report date"), (self.repo.head(), "master")):
            at = self.repo.find_by_name(rev, name)
            if at:
                self.ev(claim, "partial", "git-ls-tree",
                        f"{name} does not exist at {self.version}; it exists on {label} as {at[0]}",
                        file=at[0])
                return None
        ever = self.repo.ever_had_file(name)
        if ever:
            self.ev(claim, "partial", "git-log",
                    f"{name} is not in {self.version} but existed in curl's history "
                    f"(last touched {ever['date']}, {ever['sha'][:10]})",
                    url=self.repo.commit_url(ever["sha"]))
            return None
        if "/" not in name.strip("./"):
            # a bare name like poc.c or server.c that is nowhere in the project's history is
            # almost always the reporter's own file, not a claim about the project
            self.ev(claim, "unverifiable", "git-log",
                    f"{name} is not a {self.repo.project} file (likely the reporter's own)")
            return None
        self.ev(claim, "contradicted", "git-log",
                f"No file named {name} has ever existed in curl: not at {self.version}, not on "
                "master, and nowhere in its history",
                data={"files_checked": len(self.repo.ls(self.rev))})
        return None

    def check_function(self, claim: Claim) -> None:
        name = claim.function or ""
        if name in LIBC:
            self.check_libc_use(claim, name)
            return
        defs = self.index.lookup(name)
        if defs:
            fn = defs[0]
            if claim.file:
                wanted = self.files.get(claim.file, claim.file).rsplit("/", 1)[-1]
                in_file = [d for d in defs if d.file.rsplit("/", 1)[-1] == wanted]
                if not in_file:
                    self.ev(claim, "partial", "tree-sitter",
                            f"{name}() exists, but in {fn.file}, not in {claim.file}",
                            file=fn.file, line_start=fn.start, line_end=fn.end,
                            url=self.repo.blob_url(self.rev, fn.file, fn.start, fn.end))
                    return
                fn = in_file[0]
            chain = self.index.path_from_entry(name)
            self.ev(claim, "verified", "tree-sitter",
                    f"{name}() is defined in {fn.file}:{fn.start}-{fn.end}",
                    file=fn.file, line_start=fn.start, line_end=fn.end,
                    url=self.repo.blob_url(self.rev, fn.file, fn.start, fn.end),
                    data={"reachable_via": chain})
            return
        used = self.repo.identifier_exists(self.rev, name)
        if used:
            # referenced but not defined in the project: an external API (OpenSSL, zlib...),
            # a macro, or a variable. Real, so never a contradiction.
            self.ev(claim, "partial", "git-grep",
                    f"{name} is not a function defined in curl {self.version}, but it is referenced "
                    f"at {used.path}:{used.line} (external API, macro or variable)",
                    file=used.path, line_start=used.line, actual_code=used.text.strip(),
                    url=self.repo.blob_url(self.rev, used.path, used.line))
            return
        for rev, label in ((self.head_rev, "master on the report date"), (self.repo.head(), "master")):
            hit = self.repo.identifier_exists(rev, name)
            if hit:
                self.ev(claim, "partial", "git-grep",
                        f"{name}() is not in {self.version} but exists on {label} ({hit.path}:{hit.line})",
                        file=hit.path, line_start=hit.line, rev=rev)
                return
        history = self.repo.pickaxe(f"{name}(")
        near = self.index.near_names(name)
        if history:
            last = history[0]
            self.ev(claim, "partial", "pickaxe",
                    f"{name}() is not in {self.version}; it last appeared in history around "
                    f"{last['date']} ({last['sha'][:10]})",
                    url=self.repo.commit_url(last["sha"]), data={"history": history, "near": near})
            return
        commits = self.ctx.run.notes.setdefault("commits_searched", self.repo.commit_count())
        self.ev(claim, "contradicted", "pickaxe",
                f"{name}() has never existed in curl: not at {self.version}, not on master, and "
                f"not in any of {commits:,} commits",
                data={"near": near, "ghost": True, "commits_searched": commits})

    def check_libc_use(self, claim: Claim, name: str) -> None:
        paths = tuple(d for d in self.repo.source_dirs if d != "include")
        if claim.file and claim.file in self.files:
            paths = (self.files[claim.file],)
        hits = self.repo.grep(self.rev, f"{name}(", paths=paths, limit=20)
        hits = [h for h in hits if re.search(rf"(?<![\w.]){name}\s*\(", h.text)]
        if hits:
            first = hits[0]
            self.ev(claim, "verified", "git-grep",
                    f"{name}() is called {len(hits)} time(s), first at {first.path}:{first.line}",
                    file=first.path, line_start=first.line, actual_code=first.text.strip(),
                    url=self.repo.blob_url(self.rev, first.path, first.line))
        else:
            where = " in " + paths[0] if len(paths) == 1 else " anywhere in lib/ or src/"
            self.ev(claim, "contradicted", "git-grep",
                    f"{name}() is never called{where} at {self.version}",
                    data={"banned_by_checksrc": name in ("strcpy", "strcat", "sprintf", "gets")})

    def check_line(self, claim: Claim) -> None:
        if not claim.file or not claim.line:
            self.ev(claim, "unverifiable", "git-show", "Line number given without a file")
            return
        path = self.files.get(claim.file) or next(iter(self.repo.find_by_name(self.rev, claim.file)), None)
        if not path:
            at_head = next(iter(self.repo.find_by_name(self.head_rev, claim.file)), None)
            if at_head and claim.line <= len(self.repo.lines(self.head_rev, at_head)):
                self.ev(claim, "partial", "git-show",
                        f"{claim.file}:{claim.line} matches master on the report date, not {self.version}",
                        file=at_head, line_start=claim.line, rev=self.head_rev)
            else:
                # the file claim already carries the verdict on whether the file is real
                self.ev(claim, "unverifiable", "git-show",
                        f"Line {claim.line} cites {claim.file}, which is not in {self.version}")
            return
        lines = self.repo.lines(self.rev, path)
        if claim.line > len(lines):
            head_lines = self.repo.lines(self.head_rev, path) if self.repo.exists(self.head_rev, path) else []
            if claim.line <= len(head_lines):
                self.ev(claim, "partial", "git-show",
                        f"{path} has {len(lines)} lines at {self.version}; line {claim.line} exists on "
                        "master as of the report date", file=path, rev=self.head_rev)
                return
            self.ev(claim, "contradicted", "git-show",
                    f"{path} has only {len(lines)} lines at {self.version}; line {claim.line} "
                    "does not exist", file=path, data={"file_lines": len(lines)})
            return
        lo, hi = max(1, claim.line - 3), min(len(lines), claim.line + 3)
        actual = "\n".join(lines[lo - 1 : hi])
        owner = next((f for f in self.index.functions
                      if f.file == path and f.start <= claim.line <= f.end), None)
        if claim.function:
            named = [f for f in self.index.lookup(claim.function) if f.file == path]
            if named and (owner is None or owner.name != claim.function):
                fn = named[0]
                self.ev(claim, "contradicted", "tree-sitter",
                        f"Line {claim.line} is not in {claim.function}(), which spans "
                        f"{path}:{fn.start}-{fn.end}"
                        + (f"; that line is in {owner.name}()" if owner else ""),
                        file=path, line_start=fn.start, line_end=fn.end,
                        actual_code=actual,
                        url=self.repo.blob_url(self.rev, path, fn.start, fn.end))
                return
        detail = f"{path}:{claim.line} is inside {owner.name}()" if owner else \
            f"{path}:{claim.line} is outside any function"
        self.ev(claim, "verified", "git-show", detail, file=path, line_start=lo, line_end=hi,
                actual_code=actual, url=self.repo.blob_url(self.rev, path, claim.line),
                data={"function": owner.name if owner else None})

    def check_code(self, claim: Claim) -> None:
        wanted = significant_lines(claim.code or "")
        if not wanted:
            self.ev(claim, "unverifiable", "git-grep", "Quoted code has no distinctive lines")
            return
        matched: list[dict] = []
        missing: list[str] = []
        for line in wanted[:30]:
            probe = _ws_tolerant(line[:120])
            hits = self.repo.grep(self.rev, probe, fixed=False, limit=3) or \
                self.repo.grep(self.head_rev, probe, fixed=False, limit=3)
            if hits:
                matched.append({"claimed": line, "path": hits[0].path, "line": hits[0].line,
                                "actual": hits[0].text.strip()})
            else:
                missing.append(line)
        ratio = len(matched) / max(1, len(wanted[:30]))
        where = matched[0] if matched else None
        actual = None
        if where:
            actual = _context(self.repo, self.rev, where["path"], where["line"] - 2,
                              where["line"] + len(wanted) + 2)
        data = {"matched": matched, "missing": missing, "ratio": round(ratio, 2)}
        if ratio >= 0.8:
            self.ev(claim, "verified", "git-grep",
                    f"{len(matched)}/{len(wanted[:30])} quoted lines match {where['path']}",
                    file=where["path"], line_start=where["line"], claimed_code=claim.code,
                    actual_code=actual, data=data,
                    url=self.repo.blob_url(self.rev, where["path"], where["line"]))
            return
        # Has the missing code ever existed anywhere in history? Probe with the most distinctive
        # whitespace-free fragment of each line, so formatting differences cannot hide a match.
        fragments = sorted({_longest_token(m) for m in missing}, key=len, reverse=True)[:2]
        ever = [c for p in fragments if len(p) >= 8 for c in self.repo.pickaxe(p, limit=1)]
        data["history"] = ever
        if ratio == 0 and not ever:
            commits = self.ctx.run.notes.setdefault("commits_searched", self.repo.commit_count())
            self.ev(claim, "contradicted", "pickaxe",
                    f"None of the {len(wanted[:30])} quoted lines exist at {self.version}, and the "
                    f"most distinctive ones never appeared in any of {commits:,} commits",
                    claimed_code=claim.code, data={**data, "commits_searched": commits})
            return
        status = "partial" if ratio >= 0.3 or ever else "contradicted"
        self.ev(claim, status, "git-grep",
                f"Only {len(matched)}/{len(wanted[:30])} quoted lines match the real code at "
                f"{self.version}", file=where["path"] if where else None,
                line_start=where["line"] if where else None, claimed_code=claim.code,
                actual_code=actual, data=data)

    def check_symbol(self, claim: Claim) -> None:
        sym = claim.symbol or ""
        hits = self.repo.grep(self.rev, sym, paths=("include", "lib", "src"), limit=3)
        if hits:
            self.ev(claim, "verified", "git-grep", f"{sym} is defined/used at {hits[0].path}:{hits[0].line}",
                    file=hits[0].path, line_start=hits[0].line,
                    url=self.repo.blob_url(self.rev, hits[0].path, hits[0].line))
            return
        if self.repo.grep(self.repo.head(), sym, paths=("include",), limit=1):
            self.ev(claim, "partial", "git-grep", f"{sym} does not exist at {self.version} (added later)")
            return
        self.ev(claim, "contradicted", "git-grep", f"{sym} does not exist in curl's headers or sources")


SUPER_SYSTEM = """You are a senior C security engineer reviewing a vulnerability report against
the REAL source code of {project} {version}. The source excerpts below are authoritative; the
report may be wrong or fabricated. Decide whether the described bug can happen in this code.
Return one JSON object:
{{"assessment": "plausible|implausible|unclear",
  "reachable": "yes|no|unclear",
  "guards": [{{"file": "...", "line": <int>, "code": "<exact line>", "why": "<what it prevents>"}}],
  "mismatches": ["<where the report's description differs from the real code>"],
  "reasoning": "<at most 120 words, cite file:line>"}}
Cite only lines that appear in the excerpts. {guard}"""


async def reason_over_code(ctx: Context, grounder: Grounder) -> None:
    """Nemotron Super: read the real functions and judge reachability and existing guards."""
    targets = []
    for evidence in ctx.run.evidence:
        if evidence.method == "tree-sitter" and evidence.status in ("verified", "partial") \
                and evidence.file and evidence.line_start and evidence.line_end:
            targets.append((evidence.file, evidence.line_start, evidence.line_end))
    for evidence in ctx.run.evidence:
        if evidence.method in ("git-show", "git-grep") and evidence.file and evidence.line_start:
            owner = next((f for f in grounder.index.functions if f.file == evidence.file
                          and f.start <= evidence.line_start <= f.end), None)
            if owner:
                targets.append((owner.file, owner.start, owner.end))
    seen, excerpts, budget_lines = set(), [], 900
    for path, start, end in targets:
        if (path, start) in seen or budget_lines <= 0:
            continue
        seen.add((path, start))
        end = min(end, start + min(budget_lines, 400))
        code = _context(grounder.repo, grounder.rev, path, start, end)
        numbered = "\n".join(f"{start + i:5d}  {ln}" for i, ln in enumerate(code.splitlines()))
        excerpts.append(f"=== {path}:{start}-{end} ===\n{numbered}")
        budget_lines -= end - start + 1
    if not excerpts:
        return
    tag = new_tag()
    data, calls = await ctx.llm.chat_json(
        stage="grounding",
        role=ctx.role("super"),
        system=SUPER_SYSTEM.format(project=ctx.run.report.project, version=grounder.version,
                                   guard=guard(tag)),
        user="REAL SOURCE:\n" + "\n\n".join(excerpts) + "\n\nREPORT:\n" +
             fence(full_text(ctx)[:12000], tag),
        max_tokens=1500,
        reasoning=True,
        budget=ctx.budget,
    )
    ctx.record(calls)
    status = {"plausible": "verified", "implausible": "contradicted"}.get(
        data.get("assessment"), "unverifiable")
    ctx.run.evidence.append(Evidence(
        claim_id="analysis",
        status=status,
        method="llm-super",
        deterministic=False,
        detail=str(data.get("reasoning", ""))[:900],
        rev=grounder.rev,
        data={k: data.get(k) for k in ("assessment", "reachable", "guards", "mismatches")},
    ))
    await ctx.event("grounding", "progress",
                    f"Nemotron Super read {len(excerpts)} real functions: {data.get('assessment')}",
                    assessment=data.get("assessment"), guards=data.get("guards"))


async def run(ctx: Context) -> None:
    await ctx.event("grounding", "start", "Checking claims against the real code")
    repo = ctx.repo
    claims = ctx.run.claims
    claimed = next((c.version for c in claims if c.kind == "version" and c.version), None)
    filed = ctx.run.report.submitted_at
    rev, version = repo.resolve(claimed, as_of=filed)
    ctx.run.resolved_rev, ctx.run.resolved_version = rev, version
    when = f" (newest release on {filed[:10]})" if filed and not claimed else ""
    await ctx.event("grounding", "progress",
                    f"Resolved {claimed or 'unspecified version'} -> {rev}{when}",
                    rev=rev, version=version, claimed=claimed, filed=filed)

    if not ctx.options.grounding:
        await ctx.event("grounding", "skipped", "Grounding disabled (ablation)")
        return

    grounder = Grounder(ctx, rev, version)
    order = {"version": 0, "file": 1, "function": 2, "line": 3, "code": 4, "symbol": 5}
    for claim in sorted(claims, key=lambda c: order.get(c.kind, 9)):
        try:
            if claim.kind == "version" and claim.version:
                grounder.check_version(claim)
            elif claim.kind == "file" and claim.file:
                grounder.check_file(claim)
            elif claim.kind == "function" and claim.function:
                grounder.check_function(claim)
            elif claim.kind == "line":
                grounder.check_line(claim)
            elif claim.kind == "code" and claim.code:
                grounder.check_code(claim)
            elif claim.kind == "symbol" and claim.symbol:
                grounder.check_symbol(claim)
            else:
                continue
        except Exception as exc:  # noqa: BLE001 - one bad claim must not stop the stage
            grounder.ev(claim, "unverifiable", "error", f"check failed: {exc}")
        last = ctx.run.evidence[-1]
        await ctx.event("grounding", "progress", last.detail, claim=claim.id,
                        verdict=last.status, method=last.method)

    if ctx.llm_on:
        try:
            await reason_over_code(ctx, grounder)
        except Exception as exc:  # noqa: BLE001
            await ctx.event("grounding", "progress", f"Code reasoning skipped: {exc}")

    tally: dict[str, int] = {}
    for evidence in ctx.run.evidence:
        tally[evidence.status] = tally.get(evidence.status, 0) + 1
    await ctx.event("grounding", "done",
                    f"{tally.get('verified', 0)} verified, {tally.get('contradicted', 0)} contradicted, "
                    f"{tally.get('partial', 0)} partial", tally=tally)
