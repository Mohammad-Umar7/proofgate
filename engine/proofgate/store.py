"""SQLite persistence for runs and their evidence cards."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import closing

from .config import get_settings
from .schema import Run

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  created REAL NOT NULL,
  title TEXT NOT NULL,
  verdict TEXT,
  cost_usd REAL,
  seconds REAL,
  source TEXT,
  card TEXT,
  run TEXT
);
CREATE INDEX IF NOT EXISTS runs_created ON runs(created DESC);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_settings().db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save(run: Run, source: str = "api") -> None:
    card = run.notes.get("card") or {}
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
            (run.id, run.started_at or time.time(), run.report.title,
             run.decision.verdict.value if run.decision else None, run.cost_usd,
             card.get("seconds"), source, json.dumps(card), run.model_dump_json()),
        )


def get_card(run_id: str) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT card FROM runs WHERE id=?", (run_id,)).fetchone()
    return json.loads(row["card"]) if row and row["card"] else None


def get_run(run_id: str) -> Run | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT run FROM runs WHERE id=?", (run_id,)).fetchone()
    return Run.model_validate_json(row["run"]) if row else None


def recent(limit: int = 30) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, created, title, verdict, cost_usd, seconds, source FROM runs "
            "ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
