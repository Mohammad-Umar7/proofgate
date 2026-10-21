"""FastAPI server: submit reports, stream stage events (SSE), fetch cards, graph, arena, bench."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import __version__, store
from .codeindex import get_index
from .config import ENGINE_DIR, get_settings
from .llm import get_llm
from .pipeline import execute
from .repo import get_repo
from .sandbox import get_sandbox
from .schema import Report, StageEvent
from .stages.base import Options

ROOT = ENGINE_DIR.parent
BENCH_DIR = ROOT / "bench"
DAILY_BUDGET = float(os.environ.get("PG_DAILY_BUDGET", "3.0"))
PER_IP_PER_HOUR = int(os.environ.get("PG_RUNS_PER_IP_HOUR", "12"))

app = FastAPI(title="ProofGate", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("PG_CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class Hub:
    """In-memory fan-out of events per run; late subscribers get a replay first."""

    def __init__(self) -> None:
        self.events: dict[str, list[dict]] = defaultdict(list)
        self.done: set[str] = set()
        self.listeners: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def publish(self, run_id: str, event: dict) -> None:
        self.events[run_id].append(event)
        for queue in list(self.listeners[run_id]):
            await queue.put(event)

    async def finish(self, run_id: str) -> None:
        self.done.add(run_id)
        for queue in list(self.listeners[run_id]):
            await queue.put(None)


hub = Hub()
_spend = {"day": time.strftime("%Y-%m-%d"), "usd": 0.0}
_ip_runs: dict[str, deque] = defaultdict(deque)


def _guard(request: Request) -> None:
    today = time.strftime("%Y-%m-%d")
    if _spend["day"] != today:
        _spend.update(day=today, usd=0.0)
    if _spend["usd"] >= DAILY_BUDGET:
        raise HTTPException(429, "Daily demo budget reached; replays still work.")
    ip = request.client.host if request.client else "?"
    window = _ip_runs[ip]
    now = time.time()
    while window and now - window[0] > 3600:
        window.popleft()
    if len(window) >= PER_IP_PER_HOUR:
        raise HTTPException(429, "Too many runs from this address; try again later.")
    window.append(now)


class ReportIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    body: str = Field(min_length=20, max_length=60_000)
    project: str = "curl"
    source_url: str | None = None
    attachments: list[dict] = Field(default_factory=list, max_length=4)
    options: dict = Field(default_factory=dict)


async def _launch(report: Report, options: Options, source: str) -> str:
    holder: dict[str, str] = {}
    started = asyncio.Event()

    async def emit(event: StageEvent) -> None:
        if "id" not in holder:
            holder["id"] = event.run_id
            started.set()
        await hub.publish(event.run_id, json.loads(event.model_dump_json()))

    async def job() -> None:
        run = await execute(report, options, emit)
        _spend["usd"] += run.cost_usd
        store.save(run, source=source)
        holder.setdefault("id", run.id)
        started.set()
        await hub.finish(run.id)

    asyncio.create_task(job())
    await asyncio.wait_for(started.wait(), timeout=30)
    return holder["id"]


@app.get("/api/health")
async def health() -> dict:
    llm = get_llm()
    models = await llm.resolve_models() if llm.enabled else {}
    sandbox = get_sandbox()
    return {
        "version": __version__,
        "token_factory": llm.enabled,
        "base_url": get_settings().nebius_base_url,
        "models": models,
        "tavily": get_settings().tavily_enabled,
        "sandbox": sandbox.name,
        "sandbox_ready": await sandbox.available(),
        "budget_left_usd": round(max(0.0, DAILY_BUDGET - _spend["usd"]), 4),
    }


@app.post("/api/runs")
async def create_run(body: ReportIn, request: Request) -> dict:
    _guard(request)
    allowed = {"grounding", "routed", "prior_art_web"}
    options = Options(**{k: bool(v) for k, v in body.options.items() if k in allowed})
    options.fix = False if request.client and request.client.host != "127.0.0.1" else options.fix
    report = Report(title=body.title, body=body.body, project=body.project,
                    source_url=body.source_url, attachments=body.attachments)
    run_id = await _launch(report, options, source="api")
    return {"run_id": run_id}


@app.get("/api/runs")
async def list_runs() -> list[dict]:
    return store.recent()


@app.get("/api/runs/{run_id}")
async def get_card(run_id: str) -> dict:
    card = store.get_card(run_id)
    if card is None:
        if run_id in hub.events:
            return {"run_id": run_id, "pending": True}
        raise HTTPException(404, "unknown run")
    return card


@app.get("/api/runs/{run_id}/events")
async def stream(run_id: str) -> StreamingResponse:
    if run_id not in hub.events and store.get_card(run_id) is None:
        raise HTTPException(404, "unknown run")

    async def gen():
        queue: asyncio.Queue = asyncio.Queue()
        hub.listeners[run_id].append(queue)
        try:
            for event in list(hub.events.get(run_id, [])):
                yield f"data: {json.dumps(event)}\n\n"
            if run_id in hub.done or run_id not in hub.events:
                yield "event: end\ndata: {}\n\n"
                return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if event is None:
                    yield "event: end\ndata: {}\n\n"
                    return
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            hub.listeners[run_id].remove(queue)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/graph")
async def graph(version: str | None = None) -> dict:
    repo = get_repo("curl")
    rev, label = repo.resolve(version)
    cache = get_settings().cache_dir / "graphs" / f"curl-{rev}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    data = await asyncio.to_thread(lambda: get_index(repo, rev).export_graph())
    data["version"] = label
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


@app.get("/api/samples")
async def samples() -> list[dict]:
    folder = BENCH_DIR / "samples"
    out = []
    for path in sorted(folder.glob("*.json")) if folder.exists() else []:
        out.append(json.loads(path.read_text(encoding="utf-8")))
    return out


@app.get("/api/bench")
async def bench() -> dict:
    path = BENCH_DIR / "results" / "latest.json"
    if not path.exists():
        raise HTTPException(404, "no benchmark results yet")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/api/arena/round")
async def arena_round(request: Request, level: int = 1) -> dict:
    from .arena import red_team_report

    _guard(request)
    report = await red_team_report(max(1, min(level, 5)))
    run_id = await _launch(report, Options(fix=False), source="arena")
    return {"run_id": run_id, "level": level, "title": report.title, "body": report.body}


def main() -> None:
    import uvicorn

    uvicorn.run("proofgate.server:app", host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", "8000")), log_level="info")
