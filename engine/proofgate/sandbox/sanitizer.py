"""Parse AddressSanitizer / UndefinedBehaviorSanitizer output and attribute the crash.

Attribution answers the question maintainers care about: did the crash happen inside the
project's code, or inside code the reporter wrote themselves?
"""

from __future__ import annotations

import re

_ERROR = re.compile(r"ERROR: (AddressSanitizer|LeakSanitizer|MemorySanitizer|ThreadSanitizer): "
                    r"([\w-]+)")
_UBSAN = re.compile(r"(\S+?):(\d+):(\d+): runtime error: (.+)")
_FRAME = re.compile(r"#(\d+) 0x[0-9a-f]+ in (\S+) (\S+?):(\d+)(?::\d+)?")
_SUMMARY = re.compile(r"SUMMARY: \w+Sanitizer: ([\w-]+) (\S+?):(\d+)")

RUNTIME_HINTS = ("compiler-rt", "sanitizer_common", "asan_", "libc.so", "libc-", "/usr/include",
                 "interceptors", "libgcc", "ld-linux")


def _owner(path: str, project_dirs: tuple[str, ...]) -> str:
    if any(hint in path for hint in RUNTIME_HINTS):
        return "runtime"
    norm = path.replace("\\", "/")
    for d in project_dirs:
        if f"/{d}/" in norm or norm.startswith(f"{d}/"):
            return "project"
    if "/work/" in norm or norm.startswith(("poc", "./poc", "repro")):
        return "reporter"
    return "other"


def parse_sanitizer(log: str, project_dirs: tuple[str, ...] = ("lib", "src")) -> dict | None:
    error = _ERROR.search(log)
    ubsan = _UBSAN.search(log)
    if not error and not ubsan:
        return None
    frames = []
    for match in _FRAME.finditer(log):
        index, func, path, line = match.groups()
        if index == "0" and frames:
            break  # only the first stack (the faulting access)
        frames.append({"n": int(index), "function": func, "file": path, "line": int(line),
                       "owner": _owner(path, project_dirs)})
    first_real = next((f for f in frames if f["owner"] != "runtime"), None)
    if ubsan and not error:
        path = ubsan.group(1)
        first_real = first_real or {"function": "?", "file": path, "line": int(ubsan.group(2)),
                                    "owner": _owner(path, project_dirs)}
    attribution = first_real["owner"] if first_real else "unknown"
    if attribution == "other":
        attribution = "unknown"
    summary = _SUMMARY.search(log)
    return {
        "tool": error.group(1) if error else "UndefinedBehaviorSanitizer",
        "kind": error.group(2) if error else ubsan.group(4)[:80],
        "frames": frames[:16],
        "top": first_real,
        "summary": summary.group(0) if summary else None,
        "attribution": attribution,
    }
