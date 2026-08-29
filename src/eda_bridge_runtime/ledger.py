"""Append-only, hash-chained execution ledger."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .protocol import EVENT_PROTOCOL, RequestEnvelope, utc_now
from .redaction import redact


class ExecutionLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._initialize()

    def _initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                previous_hash TEXT,
                event_hash TEXT NOT NULL UNIQUE,
                UNIQUE(run_id, sequence)
            );
            CREATE INDEX IF NOT EXISTS events_request_idx ON events(request_id, event_id);
            CREATE TABLE IF NOT EXISTS finalized_runs (
                run_id TEXT PRIMARY KEY,
                finalized_at TEXT NOT NULL,
                final_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency_state (
                idempotency_key TEXT PRIMARY KEY,
                request_fingerprint TEXT NOT NULL,
                state TEXT NOT NULL,
                first_request_id TEXT NOT NULL,
                response_json TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TRIGGER IF NOT EXISTS events_no_update
            BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'ledger events are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS events_no_delete
            BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'ledger events are append-only'); END;
            """
        )
        self._connection.commit()

    @staticmethod
    def request_fingerprint(request: RequestEnvelope) -> str:
        material = {
            "target": request.target,
            "operation": request.operation,
            "payload": redact(request.payload),
            "expected_effect": request.expected_effect,
        }
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def claim_idempotency(self, request: RequestEnvelope) -> dict[str, Any]:
        if not request.idempotency_key:
            raise ValueError("idempotency key is required")
        fingerprint = self.request_fingerprint(request)
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT * FROM idempotency_state WHERE idempotency_key = ?",
                (request.idempotency_key,),
            ).fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO idempotency_state VALUES (?, ?, 'in_progress', ?, NULL, ?)",
                    (
                        request.idempotency_key,
                        fingerprint,
                        request.request_id,
                        utc_now(),
                    ),
                )
                return {"state": "claimed", "fingerprint": fingerprint}
            if row["request_fingerprint"] != fingerprint:
                return {"state": "conflict", "fingerprint": fingerprint}
            if row["state"] == "completed":
                return {"state": "completed", "response": json.loads(row["response_json"])}
            return {"state": "in_progress", "first_request_id": row["first_request_id"]}

    def complete_idempotency(self, request: RequestEnvelope, response: dict[str, Any]) -> None:
        if not request.idempotency_key:
            return
        fingerprint = self.request_fingerprint(request)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """UPDATE idempotency_state
                SET state = 'completed', response_json = ?, updated_at = ?
                WHERE idempotency_key = ? AND request_fingerprint = ? AND state = 'in_progress'""",
                (
                    json.dumps(redact(response), sort_keys=True, ensure_ascii=False),
                    utc_now(),
                    request.idempotency_key,
                    fingerprint,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("idempotency claim is missing or stale")

    def append(
        self,
        *,
        run_id: str,
        request_id: str,
        event_type: str,
        source: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock, self._connection:
            if self._connection.execute(
                "SELECT 1 FROM finalized_runs WHERE run_id = ?", (run_id,)
            ).fetchone():
                raise ValueError(f"run is finalized: {run_id}")
            previous = self._connection.execute(
                """SELECT sequence, event_hash FROM events
                WHERE run_id = ? ORDER BY sequence DESC LIMIT 1""",
                (run_id,),
            ).fetchone()
            sequence = 1 if previous is None else int(previous["sequence"]) + 1
            previous_hash = None if previous is None else str(previous["event_hash"])
            record = {
                "protocol": EVENT_PROTOCOL,
                "run_id": run_id,
                "request_id": request_id,
                "sequence": sequence,
                "timestamp": utc_now(),
                "event_type": event_type,
                "source": source,
                "payload": redact(payload),
                "previous_hash": previous_hash,
            }
            canonical = json.dumps(
                record, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
            event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            record["event_hash"] = event_hash
            self._connection.execute(
                """INSERT INTO events
                (run_id, request_id, sequence, timestamp, event_type, source,
                 payload_json, previous_hash, event_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    request_id,
                    sequence,
                    record["timestamp"],
                    event_type,
                    source,
                    json.dumps(record["payload"], sort_keys=True, ensure_ascii=False),
                    previous_hash,
                    event_hash,
                ),
            )
            return record

    def record_request(self, request: RequestEnvelope, runtime: dict[str, Any]) -> dict[str, Any]:
        return self.append(
            run_id=request.run_id,
            request_id=request.request_id,
            event_type="request.received",
            source="runtime",
            payload={"declared_intent": request.to_dict(), "runtime": runtime},
        )

    def finalize(self, run_id: str) -> str:
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT event_hash FROM events WHERE run_id = ? ORDER BY sequence DESC LIMIT 1",
                (run_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"cannot finalize empty run: {run_id}")
            final_hash = str(row["event_hash"])
            self._connection.execute(
                "INSERT OR IGNORE INTO finalized_runs VALUES (?, ?, ?)",
                (run_id, utc_now(), final_hash),
            )
            return final_hash

    def events(
        self, *, run_id: str | None = None, request_id: str | None = None
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[str] = []
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)
        if request_id:
            clauses.append("request_id = ?")
            params.append(request_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"SELECT * FROM events {where} ORDER BY event_id",
            params,  # noqa: S608
        ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def recent_run_events(
        self, *, limit: int = 20, source: str | None = None
    ) -> list[dict[str, Any]]:
        """Return complete event groups for the most recently active runs."""
        bounded = max(1, min(int(limit), 1000))
        where = "WHERE source = ?" if source else ""
        params: list[Any] = [source] if source else []
        rows = self._connection.execute(
            f"""SELECT run_id, MAX(event_id) AS last_event_id
            FROM events {where}
            GROUP BY run_id
            ORDER BY last_event_id DESC
            LIMIT ?""",  # noqa: S608
            [*params, bounded],
        ).fetchall()
        run_ids = [str(row["run_id"]) for row in rows]
        if not run_ids:
            return []
        placeholders = ",".join("?" for _ in run_ids)
        events = self._connection.execute(
            f"SELECT * FROM events WHERE run_id IN ({placeholders}) ORDER BY event_id",  # noqa: S608
            run_ids,
        ).fetchall()
        return [self._row_to_event(row) for row in events]

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "protocol": EVENT_PROTOCOL,
            "run_id": row["run_id"],
            "request_id": row["request_id"],
            "sequence": row["sequence"],
            "timestamp": row["timestamp"],
            "event_type": row["event_type"],
            "source": row["source"],
            "payload": json.loads(row["payload_json"]),
            "previous_hash": row["previous_hash"],
            "event_hash": row["event_hash"],
        }

    def verify(self, run_id: str) -> bool:
        previous_hash: str | None = None
        for event in self.events(run_id=run_id):
            claimed = event.pop("event_hash")
            if event["previous_hash"] != previous_hash:
                return False
            canonical = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if claimed != actual:
                return False
            previous_hash = claimed
        return previous_hash is not None

    def export_ndjson(
        self, destination: str | Path, events: Iterable[dict[str, Any]] | None = None
    ) -> None:
        rows = list(events) if events is not None else self.events()
        Path(destination).write_text(
            "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> ExecutionLedger:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
