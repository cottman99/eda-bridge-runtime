"""Durable job state independent of a client connection."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .protocol import RequestEnvelope, utc_now
from .redaction import redact

_TRANSITIONS = {
    "queued": {"running", "cancelled", "orphaned"},
    "running": {"passed", "failed", "cancelled", "orphaned"},
    "orphaned": {"running", "failed", "cancelled"},
    "passed": set(),
    "failed": set(),
    "cancelled": set(),
}


class JobStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
                idempotency_key TEXT UNIQUE, state TEXT NOT NULL, request_json TEXT NOT NULL,
                result_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS job_events (
                cursor INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
                timestamp TEXT NOT NULL, state TEXT NOT NULL, detail_json TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def submit(self, request: RequestEnvelope) -> dict[str, Any]:
        request.require_idempotency()
        if request.idempotency_key:
            existing = self.connection.execute(
                "SELECT * FROM jobs WHERE idempotency_key = ?", (request.idempotency_key,)
            ).fetchone()
            if existing:
                return self._job(existing)
        job_id = f"job_{uuid.uuid4().hex}"
        now = utc_now()
        with self.connection:
            self.connection.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, 'queued', ?, NULL, ?, ?)",
                (
                    job_id,
                    request.request_id,
                    request.idempotency_key,
                    json.dumps(redact(request.to_dict()), sort_keys=True),
                    now,
                    now,
                ),
            )
            self._event(job_id, "queued", {"request_id": request.request_id})
        return self.get(job_id)

    def transition(
        self, job_id: str, state: str, detail: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        row = self.connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        current = str(row["state"])
        if state not in _TRANSITIONS[current]:
            raise ValueError(f"invalid job transition: {current} -> {state}")
        now = utc_now()
        result_json = (
            json.dumps(redact(detail), sort_keys=True) if state in {"passed", "failed"} else None
        )
        with self.connection:
            self.connection.execute(
                """UPDATE jobs
                SET state = ?, result_json = COALESCE(?, result_json), updated_at = ?
                WHERE job_id = ?""",
                (state, result_json, now, job_id),
            )
            self._event(job_id, state, detail or {})
        return self.get(job_id)

    def _event(self, job_id: str, state: str, detail: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO job_events (job_id, timestamp, state, detail_json) VALUES (?, ?, ?, ?)",
            (job_id, utc_now(), state, json.dumps(redact(detail), sort_keys=True)),
        )

    def get(self, job_id: str) -> dict[str, Any]:
        row = self.connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._job(row)

    def events(self, job_id: str, after_cursor: int = 0) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM job_events WHERE job_id = ? AND cursor > ? ORDER BY cursor",
            (job_id, after_cursor),
        ).fetchall()
        return [
            {
                "cursor": row["cursor"],
                "timestamp": row["timestamp"],
                "state": row["state"],
                "detail": json.loads(row["detail_json"]),
            }
            for row in rows
        ]

    def request(self, job_id: str) -> RequestEnvelope:
        row = self.connection.execute(
            "SELECT request_json FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return RequestEnvelope.from_dict(json.loads(row["request_json"]))

    def record_event(self, job_id: str, detail: dict[str, Any]) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT state FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            raise KeyError(job_id)
        with self.connection:
            self._event(job_id, str(row["state"]), detail)
        return self.events(job_id)[-1]

    def recover_orphans(self) -> list[dict[str, Any]]:
        """Mark jobs whose recorded detached worker no longer exists.

        Recovery is deliberately observational: it never replays a job. An adapter or
        operator must explicitly decide whether an orphan is safe to resume.
        """
        rows = self.connection.execute(
            "SELECT job_id, state FROM jobs WHERE state IN ('queued', 'running')"
        ).fetchall()
        recovered = []
        for row in rows:
            job_id = str(row["job_id"])
            worker = self.connection.execute(
                """SELECT detail_json FROM job_events
                WHERE job_id = ? ORDER BY cursor DESC""",
                (job_id,),
            ).fetchall()
            pid = None
            for event in worker:
                detail = json.loads(event["detail_json"])
                if detail.get("event") in {"worker.started", "worker.spawned"}:
                    pid = detail.get("pid")
                    break
            if pid is None or _pid_is_alive(int(pid)):
                continue
            recovered.append(
                self.transition(
                    job_id,
                    "orphaned",
                    {"event": "worker.orphaned", "last_pid": int(pid)},
                )
            )
        return recovered

    @staticmethod
    def _job(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "job_id": row["job_id"],
            "request_id": row["request_id"],
            "idempotency_key": row["idempotency_key"],
            "state": row["state"],
            "request": json.loads(row["request_json"]),
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
