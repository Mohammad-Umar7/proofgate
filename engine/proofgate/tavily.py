"""Tavily web search, used at runtime to find prior art: disclosed reports, advisories, issues."""

from __future__ import annotations

import logging

import httpx

from .config import get_settings

SEARCH_URL = "https://api.tavily.com/search"
PRIOR_ART_DOMAINS = [
    "hackerone.com",
    "curl.se",
    "github.com",
    "daniel.haxx.se",
    "lists.haxx.se",
    "seclists.org",
    "nvd.nist.gov",
]


class TavilyError(RuntimeError):
    pass


async def search(
    query: str,
    *,
    max_results: int = 6,
    include_domains: list[str] | None = None,
    depth: str = "basic",
) -> list[dict]:
    key = get_settings().tavily_api_key
    if not key:
        raise TavilyError("TAVILY_API_KEY is not set")
    payload = {
        "query": query[:400],
        "search_depth": depth,
        "max_results": max_results,
        "include_domains": include_domains or PRIOR_ART_DOMAINS,
        "include_answer": False,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            SEARCH_URL, json=payload, headers={"Authorization": f"Bearer {key}"}
        )
        if resp.status_code >= 400:
            raise TavilyError(f"Tavily {resp.status_code}: {resp.text[:200]}")
        results = resp.json().get("results", [])
        logging.getLogger("proofgate.tavily").info("tavily search %d results: %s", len(results), query[:90])
        return results
