"""Stage 2 - claim extraction: every checkable statement in the report, as structured claims.

A deterministic extractor always runs (paths, functions, lines, versions, CVEs, quoted code).
Nemotron Nano then adds claims the patterns miss and ties them together (this function is in
that file at that line). Both sets are merged; nothing the patterns found is ever dropped.
"""

from __future__ import annotations

import re

from ..schema import Claim
from ..security import fence, guard, new_tag
from .base import Context
from .intake import full_text

_PATH = re.compile(r"\b((?:lib|src|include|tests|docs)/[\w/.+-]+\.(?:c|h))\b")
_BARE_FILE = re.compile(r"(?<![/\w])([\w+-]+\.(?:c|h))\b")
_FILE_LINE = re.compile(r"\b([\w/.+-]+\.(?:c|h)):(\d{1,5})\b")
_LINE_WORD = re.compile(r"\blines?\s+(\d{1,5})(?:\s*[-–]\s*(\d{1,5}))?", re.I)
_FUNC = re.compile(r"`?\b((?:Curl_|curl_|Curl|ossl_|cf_|http2?_|ws_|ftp_|smtp_|imap_|pop3_|"
                   r"tool_|cookie_|socks_|telnet_|mqtt_|parse_|do_)\w+)\s*\(")
_TICKED = re.compile(r"`([A-Za-z_]\w{3,})(?:\([^`]*\))?`")


def _looks_like_function(name: str, called: bool) -> bool:
    """Backticked words are often types, options or plain words; keep likely function names."""
    if called:
        return True
    if name.endswith("_t") or name.isupper() or len(name) < 6:
        return False
    return "_" in name or any(c.isupper() for c in name[1:])
_UNSAFE_CALL = re.compile(r"\b(strcpy|strcat|sprintf|vsprintf|gets|strncpy|strncat)\s*\(")
_VERSION = re.compile(r"\b(?:curl|libcurl|version|v)[\s/:-]*([1-9]\d?\.\d+\.\d+)(?![.\d])", re.I)
# functions the reporter defines in their own code (PoC harnesses, servers) are not claims
_DEFINED = re.compile(
    r"^[ \t]*(?:static\s+|inline\s+|const\s+|unsigned\s+|struct\s+\w+\s*\**\s*)*"
    r"(?:void|int|char|size_t|ssize_t|long|bool|CURLcode|CURLMcode|double|float|\w+_t)\s*\**\s*"
    r"([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{?\s*$", re.M,
)
_CVE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)
_OPTION = re.compile(r"\b(CURL(?:OPT|INFO|MOPT|E|M)_[A-Z0-9_]+)\b")

EXTRACT_SYSTEM = """You extract checkable factual claims from a security report about the
{project} source code. Return one JSON object:
{{"claims": [{{"kind": "file|function|line|code|version|cve|symbol|crash|behavior",
  "text": "<the claim in the reporter's words, max 25 words>",
  "file": "<path or null>", "function": "<name or null>", "line": <int or null>,
  "version": "<x.y.z or null>", "cve": "<CVE id or null>", "symbol": "<identifier or null>"}}],
 "summary": "<one sentence: what bug the reporter says exists>",
 "bug_class": "<e.g. heap overflow, use-after-free, injection, DoS, info leak, logic>"}}
Only include claims that can be checked against the code or public records. Never invent
details that are not in the report. {guard}"""


def _add(claims: list[Claim], **kw) -> None:
    key = (kw.get("kind"), kw.get("file"), kw.get("function"), kw.get("line"),
           kw.get("version"), kw.get("cve"), kw.get("symbol"), (kw.get("code") or "")[:80])
    for c in claims:
        if (c.kind, c.file, c.function, c.line, c.version, c.cve, c.symbol,
                (c.code or "")[:80]) == key:
            return
    claims.append(Claim(id=f"c{len(claims) + 1}", **kw))


def extract_rules(text: str, blocks) -> list[Claim]:
    claims: list[Claim] = []
    prose = re.sub(r"```.*?```", " ", text, flags=re.S)
    for match in _FILE_LINE.finditer(text):
        _add(claims, kind="line", text=match.group(0), file=match.group(1), line=int(match.group(2)))
    for match in _PATH.finditer(prose):
        _add(claims, kind="file", text=match.group(1), file=match.group(1))
    known = {c.file.rsplit("/", 1)[-1] for c in claims if c.file}
    for match in _BARE_FILE.finditer(prose):
        name = match.group(1)
        if name not in known and name not in ("curl.h",):
            known.add(name)
            _add(claims, kind="file", text=name, file=name)
    for match in _LINE_WORD.finditer(prose):
        _add(claims, kind="line", text=match.group(0), line=int(match.group(1)))
    own = {m.group(1) for m in _DEFINED.finditer(text)}
    for block in blocks:
        if block.role in ("poc", "shell", "other"):
            own |= {m.group(1) for m in _DEFINED.finditer(block.text)}
    seen_funcs = set(own)
    for match in list(_FUNC.finditer(prose)) + list(_TICKED.finditer(prose)):
        name = match.group(1)
        if name in seen_funcs or name.isupper():
            continue
        if match.re is _TICKED and not _looks_like_function(name, "(" in match.group(0)):
            continue
        seen_funcs.add(name)
        _add(claims, kind="function", text=f"{name}()", function=name)
    # "curl calls strcpy in lib/x.c": unsafe libc calls named in prose are checkable claims
    files_named = [c.file for c in claims if c.kind == "file" and c.file]
    for match in _UNSAFE_CALL.finditer(prose):
        name = match.group(1)
        if name not in seen_funcs:
            seen_funcs.add(name)
            _add(claims, kind="function", text=f"{name}() call", function=name,
                 file=files_named[0] if len(files_named) == 1 else None)
    for match in _VERSION.finditer(text):
        _add(claims, kind="version", text=match.group(0), version=match.group(1))
    for match in _CVE.finditer(text):
        _add(claims, kind="cve", text=match.group(0), cve=match.group(0).upper())
    for match in _OPTION.finditer(prose):
        _add(claims, kind="symbol", text=match.group(1), symbol=match.group(1))
    for block in blocks:
        if block.role == "quoted-source":
            _add(claims, kind="code", text=f"quoted code block #{block.index + 1}", code=block.text)
    # A bare "line N" belongs to the file (and function) the report is about, when unambiguous.
    files = {c.file for c in claims if c.kind == "file" and c.file}
    funcs = [c.function for c in claims if c.kind == "function" and c.function]
    for claim in claims:
        if claim.kind == "line" and not claim.file and len(files) == 1:
            claim.file = next(iter(files))
        if claim.kind == "line" and not claim.function and len(funcs) == 1:
            claim.function = funcs[0]
    return claims


async def run(ctx: Context) -> None:
    await ctx.event("claims", "start", "Extracting checkable claims")
    text = full_text(ctx)
    claims = extract_rules(text, ctx.run.code_blocks)
    await ctx.event("claims", "progress", f"{len(claims)} claims from deterministic patterns")

    if ctx.llm_on:
        tag = new_tag()
        try:
            data, calls = await ctx.llm.chat_json(
                stage="claims",
                role=ctx.role("nano"),
                system=EXTRACT_SYSTEM.format(project=ctx.run.report.project, guard=guard(tag)),
                user=fence(text[:24000], tag),
                max_tokens=1800,
                budget=ctx.budget,
            )
            ctx.record(calls)
            ctx.run.notes["summary"] = data.get("summary")
            ctx.run.notes["bug_class"] = data.get("bug_class")
            before = len(claims)
            own = {m.group(1) for m in _DEFINED.finditer(text)}
            for item in data.get("claims", [])[:40]:
                kind = item.get("kind")
                if kind not in ("file", "function", "line", "version", "cve", "symbol",
                                "crash", "behavior"):
                    continue
                if kind == "function" and (item.get("function") or "").strip("()") in own:
                    continue  # the reporter's own helper, not a claim about the project
                line = item.get("line")
                _add(
                    claims,
                    kind=kind,
                    text=str(item.get("text") or "")[:300],
                    file=item.get("file") or None,
                    function=(item.get("function") or "").strip("()") or None,
                    line=int(line) if isinstance(line, (int, float)) else None,
                    version=item.get("version") or None,
                    cve=(item.get("cve") or "").upper() or None,
                    symbol=item.get("symbol") or None,
                    extracted_by="llm",
                )
            await ctx.event(
                "claims", "progress",
                f"Nemotron Nano added {len(claims) - before} claims", model=calls[-1].model,
            )
        except Exception as exc:  # noqa: BLE001 - deterministic claims still stand
            await ctx.event("claims", "progress", f"LLM extraction skipped: {exc}")

    ctx.run.claims = claims
    counts: dict[str, int] = {}
    for c in claims:
        counts[c.kind] = counts.get(c.kind, 0) + 1
    await ctx.event(
        "claims", "done", f"{len(claims)} checkable claims",
        counts=counts, claims=[c.model_dump(exclude_none=True) for c in claims],
    )
