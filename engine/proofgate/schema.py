"""Data model shared by the pipeline, the API, the bench and the frontend."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    UNGROUNDED = "UNGROUNDED"
    DUPLICATE = "DUPLICATE"
    NEEDS_INFO = "NEEDS_INFO"
    REPRODUCED = "REPRODUCED"


ClaimKind = Literal[
    "file", "function", "line", "code", "version", "cve", "symbol", "option", "crash", "behavior"
]
EvidenceStatus = Literal["verified", "contradicted", "partial", "unverifiable"]
StageName = Literal[
    "intake", "claims", "grounding", "prior_art", "rules", "repro", "adjudicate", "fix", "card"
]
STAGES: tuple[StageName, ...] = (
    "intake", "claims", "grounding", "prior_art", "rules", "repro", "adjudicate", "fix", "card"
)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Attachment(BaseModel):
    name: str
    mime: str = "text/plain"
    text: str | None = None
    data_b64: str | None = None  # images: screenshots, terminal captures


class Report(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rpt"))
    project: str = "curl"
    title: str
    body: str
    source_url: str | None = None
    submitted_at: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)


class Claim(BaseModel):
    id: str
    kind: ClaimKind
    text: str  # the claim as the reporter stated it
    file: str | None = None
    function: str | None = None
    line: int | None = None
    version: str | None = None
    code: str | None = None
    cve: str | None = None
    symbol: str | None = None
    extracted_by: Literal["rules", "llm"] = "rules"


class Evidence(BaseModel):
    claim_id: str
    status: EvidenceStatus
    method: str  # git-show, git-grep, pickaxe, tree-sitter, osv, tavily, llm, sandbox...
    detail: str
    deterministic: bool = True
    rev: str | None = None
    file: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    claimed_code: str | None = None
    actual_code: str | None = None
    url: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class PriorArt(BaseModel):
    source: Literal["curl-advisory", "osv", "tavily", "hackerone"]
    id: str
    title: str
    url: str
    score: float  # 0..1 similarity to the report
    fixed_in: str | None = None
    snippet: str | None = None


class ModelCall(BaseModel):
    stage: str
    role: str  # nano / omni / super / ultra
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    ms: int = 0
    cached: bool = False


class SandboxResult(BaseModel):
    backend: str
    ran: bool
    exit_code: int | None = None
    timed_out: bool = False
    network: str = "none"
    duration_ms: int = 0
    log: str = ""
    sanitizer: dict[str, Any] | None = None  # parsed crash report
    attribution: Literal["project", "reporter", "none", "unknown"] = "none"


class FixAttempt(BaseModel):
    iteration: int
    patch: str
    test: str
    build_ok: bool
    repro_fixed: bool
    suite_passed: bool
    log: str = ""


class Decision(BaseModel):
    verdict: Verdict
    confidence: float
    headline: str
    reasons: list[str]
    challenge: str | None = None  # adversarial second pass
    challenge_upheld: bool | None = None
    reply_draft: str | None = None


class StageEvent(BaseModel):
    run_id: str
    stage: StageName
    status: Literal["start", "progress", "done", "skipped", "error"]
    message: str
    t: float = Field(default_factory=time.time)
    elapsed_ms: int = 0
    cost_usd: float = 0.0
    data: dict[str, Any] = Field(default_factory=dict)


class Run(BaseModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    report: Report
    started_at: float = Field(default_factory=time.time)
    finished_at: float | None = None
    resolved_rev: str | None = None
    resolved_version: str | None = None
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    prior_art: list[PriorArt] = Field(default_factory=list)
    rules_hit: list[dict[str, Any]] = Field(default_factory=list)
    sandbox: SandboxResult | None = None
    fix: list[FixAttempt] = Field(default_factory=list)
    decision: Decision | None = None
    calls: list[ModelCall] = Field(default_factory=list)
    events: list[StageEvent] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)  # e.g. prompt-injection-detected

    @property
    def cost_usd(self) -> float:
        return round(sum(c.cost_usd for c in self.calls), 6)
