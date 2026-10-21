"""The orchestrator's only outward-facing action: open a DRAFT pull request on a fork.

Separation of duties: the reasoning stages never see GITHUB_TOKEN; only this module does, and
only after a run is finished. PRs go to PG_PR_REPO (a fork the operator owns), never upstream,
and they are always drafts for a human maintainer to review.
"""

from __future__ import annotations

import base64
import os
import re

import httpx

from .config import get_settings
from .schema import Run

API = "https://api.github.com"


class PublishError(RuntimeError):
    pass


def _files_from_patch(patch: str) -> list[str]:
    return sorted(set(re.findall(r"^\+\+\+ b/(\S+)", patch, re.M)))


async def open_draft_pr(run: Run, patched_files: dict[str, str]) -> str:
    token = get_settings().github_token
    repo = os.environ.get("PG_PR_REPO", "")
    if not token or not repo:
        raise PublishError("set GITHUB_TOKEN and PG_PR_REPO (owner/name of your fork)")
    if repo.lower().startswith("curl/"):
        raise PublishError("refusing to open PRs upstream; use a fork you own")
    attempt = next((f for f in reversed(run.fix) if f.repro_fixed and f.suite_passed), None)
    if attempt is None:
        raise PublishError("no verified patch on this run")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    branch = f"proofgate/{run.id}"
    async with httpx.AsyncClient(base_url=API, headers=headers, timeout=30) as gh:
        meta = (await gh.get(f"/repos/{repo}")).json()
        base = meta["default_branch"]
        sha = (await gh.get(f"/repos/{repo}/git/ref/heads/{base}")).json()["object"]["sha"]
        await gh.post(f"/repos/{repo}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": sha})
        for path in _files_from_patch(attempt.patch):
            if path not in patched_files:
                continue
            current = (await gh.get(f"/repos/{repo}/contents/{path}", params={"ref": branch})).json()
            await gh.put(f"/repos/{repo}/contents/{path}", json={
                "message": run.notes.get("fix_message") or f"Fix for {run.report.title}",
                "content": base64.b64encode(patched_files[path].encode()).decode(),
                "sha": current.get("sha"), "branch": branch,
            })
        body = (f"Draft fix proposed by ProofGate for: **{run.report.title}**\n\n"
                f"- Verdict: {run.decision.verdict.value if run.decision else '?'}\n"
                f"- Verified in sandbox on attempt {attempt.iteration}: builds, reproduction "
                "is clean, area tests pass.\n\nA maintainer must review before anything merges.")
        resp = await gh.post(f"/repos/{repo}/pulls", json={
            "title": f"[ProofGate draft] {run.report.title}"[:120], "head": branch,
            "base": base, "body": body, "draft": True,
        })
        if resp.status_code >= 300:
            raise PublishError(resp.text[:300])
        return resp.json()["html_url"]
