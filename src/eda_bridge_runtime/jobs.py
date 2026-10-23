"""Durable job state independent of a client connection."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .errors import ExecutionError
from .ledger import ExecutionLedger
from .protocol import RequestEnvelope, utc_now
from .redaction import redact

_TRANSITIONS = {
    "queued": {"running", "cancelled", "orphaned"},
    "running": {"passed", "failed", "cancelled", "orphaned", "uncertain"},
    "uncertain": {"passed", "failed"},
    "orphaned": {"failed", "cancelled"},
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
            CREATE TABLE IF NOT EXISTS job_cancellations (
                job_id TEXT PRIMARY KEY, purpose TEXT NOT NULL, requested_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def submit(self, request: RequestEnvelope) -> dict[str, Any]:
        request.require_idempotency()
        job_id = f"job_{uuid.uuid4().hex}"
        now = utc_now()
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            if request.idempotency_key:
                existing = self.connection.execute(
                    "SELECT * FROM jobs WHERE idempotency_key = ?", (request.idempotency_key,)
                ).fetchone()
                if existing:
                    original = RequestEnvelope.from_dict(json.loads(existing["request_json"]))
                    if ExecutionLedger.request_fingerprint(
                        original
                    ) != ExecutionLedger.request_fingerprint(request):
                        raise ExecutionError(
                            "idempotency_conflict",
                            "Idempotency key belongs to a different request",
                            phase="admission",
                        )
                    self.connection.commit()
                    return self._job(existing)
            self.connection.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, 'queued', ?, NULL, ?, ?)",
                (
                    job_id,
                    request.request_id,
                    request.idempotency_key,
                    json.dumps(request.to_dict(), sort_keys=True),
                    now,
                    now,
                ),
            )
            self._event(job_id, "queued", {"request_id": request.request_id})
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise
        return self.get(job_id)

    def transition(
        self, job_id: str, state: str, detail: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self.connection.execute("BEGIN IMMEDIATE")
        with self.connection:
            row = self.connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise KeyError(job_id)
            current = str(row["state"])
            if state not in _TRANSITIONS[current]:
                raise ValueError(f"invalid job transition: {current} -> {state}")
            now = utc_now()
            result_json = (
                json.dumps(redact(detail), sort_keys=True)
                if state in {"passed", "failed", "uncertain"}
                else None
            )
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

    def cancel(self, job_id: str, purpose: str) -> dict[str, Any]:
        if not purpose.strip():
            raise ValueError("Cancellation requires a purpose")
        self.connection.execute("BEGIN IMMEDIATE")
        with self.connection:
            job = self.get(job_id)
            if job["state"] not in {"queued", "running"}:
                return job
            self.connection.execute(
                "INSERT OR IGNORE INTO job_cancellations VALUES (?, ?, ?)",
                (job_id, purpose, utc_now()),
            )
            if job["state"] == "queued":
                self.connection.execute(
                    "UPDATE jobs SET state = 'cancelled', updated_at = ? WHERE job_id = ?",
                    (utc_now(), job_id),
                )
            self._event(
                job_id,
                "cancelled" if job["state"] == "queued" else "running",
                {"event": "cancellation.requested", "purpose": purpose},
            )
        return self.get(job_id)

    def cancellation_requested(self, job_id: str) -> bool:
        return (
            self.connection.execute(
                "SELECT 1 FROM job_cancellations WHERE job_id = ?", (job_id,)
            ).fetchone()
            is not None
        )

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
            # Recheck under the same write lock used to claim/finish a job.
            # A duplicate submitter can record a losing spawn after the actual
            # worker started; only the claimed owner represents a running job.
            self.connection.execute("BEGIN IMMEDIATE")
            with self.connection:
                current = self.get(job_id)
                if current["state"] not in {"queued", "running"}:
                    continue
                events = self.events(job_id)
                owners = [
                    event["detail"]["pid"]
                    for event in events
                    if event["detail"].get("event") == "worker.started"
                ]
                pids = (
                    owners[-1:]
                    if current["state"] == "running"
                    else [
                        event["detail"]["pid"]
                        for event in events
                        if event["detail"].get("event") == "worker.spawned"
                    ]
                )
                if not pids or any(_pid_is_alive(int(pid)) for pid in pids):
                    continue
                self.connection.execute(
                    "UPDATE jobs SET state = 'orphaned', updated_at = ? WHERE job_id = ?",
                    (utc_now(), job_id),
                )
                self._event(
                    job_id, "orphaned", {"event": "worker.orphaned", "last_pid": int(pids[-1])}
                )
            recovered.append(self.get(job_id))
            from .connections import runtime_home
            from .lease import LeaseStore

            resources = LeaseStore(runtime_home() / "resources.sqlite3")
            try:
                resources.mark_owner_uncertain(self.request(job_id).run_id)
            finally:
                resources.connection.close()
        return recovered

    @staticmethod
    def _job(row: sqlite3.Row) -> dict[str, Any]:
        request = json.loads(row["request_json"])
        return {
            "job_id": row["job_id"],
            "request_id": row["request_id"],
            "run_id": request["run_id"],
            "idempotency_key": row["idempotency_key"],
            "state": row["state"],
            "request": redact(request),
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5
        try:
            exit_code = wintypes.DWORD()
            return (
                bool(kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)))
                and exit_code.value == 259
            )
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # Windows reports an invalid or stale PID as a generic OSError
        # (commonly WinError 87) rather than ProcessLookupError.
        return False
    return True
