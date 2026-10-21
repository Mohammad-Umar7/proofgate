"""curl's own advisory feed (OSV format, https://curl.se/docs/vuln.json) and OSV.dev lookups."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from functools import lru_cache

import httpx

from .config import get_settings
from .repo import parse_version

FEED_URL = "https://curl.se/docs/vuln.json"
OSV_URL = "https://api.osv.dev/v1/vulns/{id}"
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_STOP = set(
    "the and for with that this from when curl libcurl can not are was has have into its use "
    "used using which will been also may could would via than then them they there their".split()
)


@dataclass
class Advisory:
    id: str
    cve: str
    summary: str
    details: str
    issue_url: str | None
    www: str | None
    cwe: str | None
    severity: str | None
    published: str
    ranges: list[tuple[tuple[int, int, int], tuple[int, int, int] | None]]

    def affects(self, version: str | None) -> bool | None:
        ver = parse_version(version or "")
        if ver is None:
            return None
        return any(lo <= ver and (hi is None or ver < hi) for lo, hi in self.ranges)

    @property
    def fixed_in(self) -> str | None:
        fixed = [hi for _, hi in self.ranges if hi]
        return ".".join(map(str, max(fixed))) if fixed else None


def _ranges(entry: dict) -> list:
    out = []
    for affected in entry.get("affected", []):
        for rng in affected.get("ranges", []):
            if rng.get("type") not in ("SEMVER", "ECOSYSTEM"):
                continue  # GIT ranges carry commit hashes, not versions
            lo = None
            for event in rng.get("events", []):
                if "introduced" in event:
                    lo = parse_version(event["introduced"]) or (0, 0, 0)
                elif "fixed" in event and lo is not None:
                    out.append((lo, parse_version(event["fixed"])))
                    lo = None
            if lo is not None:
                out.append((lo, None))
    return out


def _load_feed() -> list[dict]:
    path = get_settings().cache_dir / "curl_vuln.json"
    if not path.exists() or time.time() - path.stat().st_mtime > 86400:
        try:
            resp = httpx.get(FEED_URL, timeout=30)
            resp.raise_for_status()
            path.write_text(resp.text, encoding="utf-8")
        except httpx.HTTPError:
            if not path.exists():
                return []
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def curl_advisories() -> list[Advisory]:
    out = []
    for entry in _load_feed():
        db = entry.get("database_specific", {})
        cwe = db.get("CWE")
        out.append(
            Advisory(
                id=entry["id"],
                cve=next((a for a in entry.get("aliases", []) if a.startswith("CVE-")), entry["id"]),
                summary=entry.get("summary", ""),
                details=entry.get("details", ""),
                issue_url=db.get("issue"),
                www=db.get("www"),
                cwe=cwe.get("id") if isinstance(cwe, dict) else cwe,
                severity=db.get("severity"),
                published=entry.get("published", "")[:10],
                ranges=_ranges(entry),
            )
        )
    return out


def by_cve(cve: str) -> Advisory | None:
    cve = cve.upper()
    return next((a for a in curl_advisories() if a.cve == cve or a.id == f"CURL-{cve}"), None)


def tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN.findall(text)} - _STOP


def similarity(report_tokens: set[str], identifiers: set[str], adv: Advisory) -> float:
    adv_tokens = tokens(f"{adv.summary} {adv.details}")
    if not adv_tokens or not report_tokens:
        return 0.0
    overlap = len(report_tokens & adv_tokens) / (len(report_tokens | adv_tokens) ** 0.5 * 6)
    ident_hits = {i.lower() for i in identifiers} & adv_tokens
    return min(1.0, overlap + 0.25 * len(ident_hits))


async def osv_lookup(vuln_id: str) -> dict | None:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(OSV_URL.format(id=vuln_id))
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
