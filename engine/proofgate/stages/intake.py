"""Stage 1 - intake: normalize the report, split code blocks, read screenshots (Nemotron 3.5 Super VL)."""

from __future__ import annotations

import re

from ..schema import CodeBlock
from ..security import scan_injection
from .base import Context

_FENCE = re.compile(r"```([\w+-]*)[^\n]*\n(.*?)```", re.S)
_POC_HINTS = re.compile(r"\bint\s+main\s*\(|#include\s*<curl/curl\.h>|curl_easy_init\s*\(")
_SHELL_HINTS = re.compile(r"^\s*(\$\s*)?(curl|\./|gcc|clang|make|python3?|nc|echo)\b", re.M)
_OUTPUT_HINTS = re.compile(r"AddressSanitizer|Segmentation fault|SUMMARY:|==\d+==|Traceback")
_SOURCE_HINTS = re.compile(
    r"\bCURLcode\b|\bstruct Curl_easy\b|\bCurl_\w+\s*\(|\bdata->(set|state)\b|\bconn->"
)

OMNI_PROMPT = (
    "This image was attached to a security report. Transcribe every piece of text exactly as "
    "shown (terminal output, stack traces, code, file names, line numbers). Do not interpret "
    "or fix anything. Output plain text only."
)


_DIFF_LINE = re.compile(r"^(@@ |\+\+\+ |--- |[-+](?![-+]))", re.M)


def classify_block(lang: str, text: str) -> str:
    if _OUTPUT_HINTS.search(text):
        return "output"
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if lang in ("diff", "patch") or (lines and len(_DIFF_LINE.findall(text)) > 0.3 * len(lines)):
        return "other"  # a proposed patch, not a quote of the current code
    if _POC_HINTS.search(text):
        return "poc"
    if lang in ("sh", "bash", "shell", "console", "zsh") or _SHELL_HINTS.search(text):
        return "shell"
    if lang in ("c", "h", "cpp", "") and _SOURCE_HINTS.search(text):
        return "quoted-source"
    return "other"


def split_blocks(body: str) -> list[CodeBlock]:
    blocks = []
    for i, match in enumerate(_FENCE.finditer(body)):
        lang = (match.group(1) or "").lower()
        text = match.group(2).rstrip()
        blocks.append(CodeBlock(index=i, lang=lang, text=text, role=classify_block(lang, text)))
    return blocks


async def run(ctx: Context) -> None:
    report = ctx.run.report
    await ctx.event("intake", "start", "Reading report")

    hits = scan_injection(f"{report.title}\n{report.body}")
    if hits:
        ctx.run.flags.append("prompt-injection")
        ctx.run.notes["injection"] = hits
        await ctx.event(
            "intake", "progress",
            f"Report tries to instruct the triage model ({len(hits)} pattern(s)); treating as data",
            injection=hits,
        )

    ctx.run.code_blocks = split_blocks(report.body)

    images = [a for a in report.attachments if a.data_b64 and a.mime.startswith("image/")]
    for att in images:
        if not ctx.llm_on:
            break
        text, call = await ctx.llm.chat(
            stage="intake",
            role=ctx.role("omni"),
            system=OMNI_PROMPT,
            user=[
                {"type": "text", "text": f"Attachment: {att.name}"},
                {"type": "image_url", "image_url": {"url": f"data:{att.mime};base64,{att.data_b64}"}},
            ],
            max_tokens=1500,
            budget=ctx.budget,
        )
        ctx.record(call)
        att.text = text
        await ctx.event("intake", "progress", f"Transcribed {att.name} with Nemotron 3.5 Super VL")

    roles: dict[str, int] = {}
    for block in ctx.run.code_blocks:
        roles[block.role] = roles.get(block.role, 0) + 1
    words = len(report.body.split())
    await ctx.event(
        "intake", "done",
        f"{words} words, {len(ctx.run.code_blocks)} code blocks, {len(images)} images",
        words=words, blocks=roles, images=len(images),
    )


def full_text(ctx: Context) -> str:
    """Report text plus anything read from attachments."""
    parts = [ctx.run.report.title, ctx.run.report.body]
    parts += [a.text for a in ctx.run.report.attachments if a.text]
    return "\n\n".join(parts)
