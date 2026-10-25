"""Build FixBench instances from curl's advisory feed and git history.

An instance, per CVE:
  base          parent of curl's fix commit: the vulnerable code
  fix_commit    the commit the advisory names as the fix
  test_patch    the fix commit's changes under tests/ (the regression test the maintainers wrote)
  gold_patch    the rest of the fix (lib/, src/, include/ ...). Used for validation only,
                never shown to the agent
  fail_to_pass  tests the fix added or changed; must fail on base and pass with the fix
  pass_to_pass  tests sharing a keyword with them; must pass before and after (set by validation)
  issue         the public advisory text, the way a reporter would describe the flaw
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from ..config import ENGINE_DIR, get_settings
from ..repo import get_repo

INDEX = ENGINE_DIR.parent / "bench" / "fixbench.jsonl"
VULN_FEED = "https://curl.se/docs/vuln.json"
SINCE = "2023-01-01"  # older trees predate the toolchain in the sandbox image
MAX_SOURCE_FILES = 5  # keep instances to focused fixes, like a single bug report
_TEST_FILE = re.compile(r"tests/data/test(\d+)$")
_KEYWORDS = re.compile(r"<keywords>\s*(.*?)\s*</keywords>", re.S)


def _feed() -> list[dict]:
    path = get_settings().cache_dir / "curl_vuln.json"
    if not path.exists():
        import httpx

        path.write_bytes(httpx.get(VULN_FEED, timeout=60).content)
    return json.loads(path.read_text(encoding="utf-8"))


def _fix_commit(advisory: dict) -> str | None:
    for affected in advisory.get("affected", []):
        for rng in affected.get("ranges", []):
            if rng.get("type") != "GIT":
                continue
            for event in rng.get("events", []):
                if event.get("fixed"):
                    return event["fixed"]
    return None


def keywords(text: str) -> list[str]:
    match = _KEYWORDS.search(text or "")
    return [k.strip() for k in match.group(1).splitlines() if k.strip()] if match else []


def _diff(base: str, fix: str, *paths: str) -> str:
    # bytes, not text mode: test data can carry literal CRLFs that must survive into the patch
    out = subprocess.run(["git", "-C", str(get_repo().path), "diff", "--no-color", "--no-ext-diff",
                          base, fix, "--", *paths], capture_output=True, check=True)
    return out.stdout.decode("utf-8", "replace")


def test_patch(base: str, fix: str) -> str:
    return _diff(base, fix, "tests/")


def gold_patch(base: str, fix: str) -> str:
    return _diff(base, fix, ".", ":(exclude)tests", ":(exclude)docs", ":(exclude)RELEASE-NOTES")


def build_index() -> list[dict]:
    repo = get_repo()
    rows = []
    for adv in _feed():
        fix = _fix_commit(adv)
        if not fix or not repo.git("cat-file", "-t", fix, check=False).strip() == "commit":
            continue
        date = repo.git("show", "-s", "--format=%cs", fix).strip()
        if date < SINCE:
            continue
        status = [line.split("\t") for line in
                  repo.git("show", "--name-status", "--format=", fix).splitlines() if "\t" in line]
        tests = sorted({m.group(1) for s in status if (m := _TEST_FILE.match(s[-1]))}, key=int)
        source = [s[-1] for s in status
                  if s[-1].startswith(("lib/", "src/", "include/")) and s[0][0] in "AMD"]
        if not tests or not source or len(source) > MAX_SOURCE_FILES:
            continue
        base = repo.git("rev-parse", f"{fix}^").strip()
        kws = sorted({k for t in tests for k in keywords(repo.git("show", f"{fix}:tests/data/test{t}"))})
        cve = next((a for a in adv.get("aliases", []) if a.startswith("CVE-")), adv["id"])
        meta = adv.get("database_specific", {})
        rows.append({
            "id": cve,
            "summary": adv.get("summary", ""),
            "severity": meta.get("severity"),
            "cwe": (meta.get("CWE") or {}).get("desc"),
            "published": (adv.get("published") or "")[:10],
            "advisory_url": meta.get("www"),
            "fix_commit": fix,
            "fix_date": date,
            "base": base,
            "source_files": source,
            "fail_to_pass": tests,
            "keywords": kws,
            "issue": f"{adv.get('summary', '')}\n\n{adv.get('details', '').strip()}",
        })
    rows.sort(key=lambda r: r["fix_date"], reverse=True)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return rows


def load_index(path: Path = INDEX) -> list[dict]:
    if not path.exists():
        return build_index()
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_index(rows: list[dict], path: Path = INDEX) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def area_tests(row: dict, limit: int = 30) -> list[str]:
    """Existing tests that share a keyword with the regression test: pass-to-pass candidates."""
    repo = get_repo()
    wanted = {k.lower() for k in row["keywords"]} - {"http", "https", "curl", "--libcurl"}
    if not wanted:
        return []
    found: list[str] = []
    names = repo.git("ls-tree", "--name-only", f"{row['base']}:tests/data").split()
    numbers = sorted((n[4:] for n in names if n.startswith("test") and n[4:].isdigit()), key=int)
    numbers = [n for n in numbers if n not in row["fail_to_pass"]]
    blobs = repo.show_many(row["base"], [f"tests/data/test{n}" for n in numbers])
    for n in numbers:
        text = blobs.get(f"tests/data/test{n}", "")
        if wanted & {k.lower() for k in keywords(text)} and "<disable>" not in text:
            found.append(n)
        if len(found) >= limit:
            break
    return found
