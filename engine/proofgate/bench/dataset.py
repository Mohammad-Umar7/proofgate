"""Build the SlopBench index from two public, curl-maintained sources.

* slop  - every report on Daniel Stenberg's public list of AI slop submitted to curl's HackerOne
          program (gist bagder/07f7581f6e3d78ef37dfbfc81fd1d1cd).
* valid - every curl CVE whose advisory (curl.se/docs/vuln.json) links the original HackerOne
          report.
Only ids, URLs, labels and titles are committed (bench/slopbench.jsonl). Report text is fetched
from HackerOne's public JSON for disclosed reports into the local cache and is not redistributed.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import httpx

from ..advisories import curl_advisories
from ..config import ENGINE_DIR, get_settings

GIST_API = "https://api.github.com/gists/07f7581f6e3d78ef37dfbfc81fd1d1cd"
GIST_URL = "https://gist.github.com/bagder/07f7581f6e3d78ef37dfbfc81fd1d1cd"
INDEX = ENGINE_DIR.parent / "bench" / "slopbench.jsonl"
_ENTRY = re.compile(r"^\s*\d+\.\s+(.*?)\s*\[#(\d+)\]\((https://hackerone\.com/reports/\d+)\)", re.M)


def cache_dir() -> Path:
    path = get_settings().cache_dir / "bench" / "h1"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_index() -> list[dict]:
    gist = httpx.get(GIST_API, timeout=30).json()
    text = "\n".join(f.get("content", "") for f in gist["files"].values())
    rows = []
    for title, rid, url in _ENTRY.findall(text):
        rows.append({"id": f"h1-{rid}", "h1": int(rid), "url": url, "label": "slop",
                     "title": title.strip(), "source": GIST_URL})
    for adv in curl_advisories():
        match = re.search(r"hackerone\.com/reports/(\d+)", adv.issue_url or "")
        if not match:
            continue
        rows.append({"id": f"h1-{match.group(1)}", "h1": int(match.group(1)),
                     "url": f"https://hackerone.com/reports/{match.group(1)}", "label": "valid",
                     "title": adv.summary, "cve": adv.cve, "published": adv.published,
                     "source": adv.www})
    seen, unique = set(), []
    for row in rows:
        if row["id"] not in seen:
            seen.add(row["id"])
            unique.append(row)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text("\n".join(json.dumps(r) for r in unique) + "\n", encoding="utf-8")
    return unique


def load_index() -> list[dict]:
    return [json.loads(line) for line in INDEX.read_text(encoding="utf-8").splitlines() if line]


async def fetch_reports(rows: list[dict], delay: float = 1.0) -> dict[str, int]:
    """Download disclosed report JSON (polite: one request per `delay` seconds)."""
    stats = {"cached": 0, "fetched": 0, "unavailable": 0}
    async with httpx.AsyncClient(timeout=30, headers={"Accept": "application/json",
                                                       "User-Agent": "ProofGate-SlopBench/0.1"}) as client:
        for row in rows:
            target = cache_dir() / f"{row['h1']}.json"
            if target.exists():
                stats["cached"] += 1
                continue
            resp = await client.get(f"https://hackerone.com/reports/{row['h1']}.json")
            if resp.status_code == 200 and resp.json().get("vulnerability_information"):
                data = resp.json()
                keep = {k: data.get(k) for k in ("id", "title", "vulnerability_information",
                                                 "created_at", "disclosed_at", "substate",
                                                 "weakness", "severity_rating")}
                target.write_text(json.dumps(keep), encoding="utf-8")
                stats["fetched"] += 1
            else:
                stats["unavailable"] += 1
            await asyncio.sleep(delay)
    return stats


async def fetch_one(h1: str) -> dict | None:
    """One disclosed report, live from HackerOne's public JSON (used by the console's link box)."""
    async with httpx.AsyncClient(timeout=20, headers={"Accept": "application/json",
                                                       "User-Agent": "ProofGate/0.1"}) as client:
        resp = await client.get(f"https://hackerone.com/reports/{h1}.json")
    if resp.status_code != 200:
        return None
    data = resp.json()
    return data if data.get("vulnerability_information") else None


def load_report(row: dict) -> dict | None:
    path = cache_dir() / f"{row['h1']}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
