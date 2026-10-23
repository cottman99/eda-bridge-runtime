"""Durable Worker resource admission. Expiry never permits overlapping calls."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .errors import ExecutionError


@dataclass(frozen=True)
class Lease:
    resource: str
    owner: str
    fencing_token: int
    expires_at: float


class LeaseStore:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(path, timeout=30, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS resource_ownership (
            resource TEXT PRIMARY KEY, owner TEXT NOT NULL, fencing_token INTEGER NOT NULL,
            expires_at REAL NOT NULL, state TEXT NOT NULL)"""
        )
        self.connection.commit()
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS reconciliations "
            "(resource TEXT, owner TEXT, fencing_token INTEGER, observed_at REAL, observation TEXT)"
        )
        self.connection.commit()

    def acquire_many(self, resources, owner: str, *, wait_seconds: float = 30) -> list[Lease]:
        deadline = time.monotonic() + max(0, wait_seconds)
        resources = sorted(set(resources))
        while True:
            acquired = []
            try:
                for resource in resources:
                    acquired.append(self.acquire(resource, owner))
                return acquired
            except BaseException as exc:
                for lease in reversed(acquired):
                    self.release(lease)
                if (
                    not isinstance(exc, ExecutionError)
                    or exc.code != "resource_busy"
                    or time.monotonic() >= deadline
                ):
                    raise
                time.sleep(min(0.1, max(0, deadline - time.monotonic())))

    def acquire(self, resource: str, owner: str, ttl_seconds: float = 60) -> Lease:
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                row = self.connection.execute(
                    "SELECT * FROM resource_ownership WHERE resource = ?", (resource,)
                ).fetchone()
                if row and row["state"] != "idle":
                    code = "execution_uncertain" if row["state"] == "uncertain" else "resource_busy"
                    raise ExecutionError(
                        code,
                        "Target is leased by an unfinished execution",
                        phase="admission",
                        evidence={"owner": row["owner"]},
                    )
                token = 1 if row is None else int(row["fencing_token"]) + 1
                expires = time.time() + ttl_seconds
                self.connection.execute(
                    "INSERT OR REPLACE INTO resource_ownership VALUES (?, ?, ?, ?, 'active')",
                    (resource, owner, token, expires),
                )
                self.connection.commit()
                return Lease(resource, owner, token, expires)
            except BaseException:
                self.connection.rollback()
                raise

    def renew(self, lease: Lease, ttl_seconds: float = 60) -> Lease:
        expires = time.time() + ttl_seconds
        with self._lock, self.connection:
            cursor = self.connection.execute(
                """UPDATE resource_ownership SET expires_at = ?
                WHERE resource = ? AND owner = ? AND fencing_token = ? AND state = 'active'""",
                (expires, lease.resource, lease.owner, lease.fencing_token),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("stale lease cannot be renewed")
        return Lease(lease.resource, lease.owner, lease.fencing_token, expires)

    def release(self, lease: Lease) -> bool:
        with self._lock, self.connection:
            cursor = self.connection.execute(
                """UPDATE resource_ownership SET state = 'idle', expires_at = 0
                WHERE resource = ? AND owner = ? AND fencing_token = ? AND state = 'active'""",
                (lease.resource, lease.owner, lease.fencing_token),
            )
        return cursor.rowcount == 1

    def assert_current(self, lease: Lease) -> None:
        with self._lock:
            row = self.connection.execute(
                "SELECT owner, fencing_token, state FROM resource_ownership WHERE resource = ?",
                (lease.resource,),
            ).fetchone()
        if row is None or tuple(row) != (lease.owner, lease.fencing_token, "active"):
            raise ExecutionError("stale_execution", "Target ownership changed before execution")

    def mark_uncertain(self, lease: Lease) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                """UPDATE resource_ownership SET state = 'uncertain'
                WHERE resource = ? AND owner = ? AND fencing_token = ? AND state = 'active'""",
                (lease.resource, lease.owner, lease.fencing_token),
            )

    def mark_owner_uncertain(self, owner: str) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                "UPDATE resource_ownership SET state = 'uncertain' "
                "WHERE owner = ? AND state = 'active'",
                (owner,),
            )

    def status(self) -> list[dict]:
        with self._lock:
            return [
                dict(row)
                for row in self.connection.execute(
                    "SELECT * FROM resource_ownership WHERE state != 'idle' ORDER BY resource"
                )
            ]

    def reconcile(self, lease: Lease, *, observation: str) -> bool:
        """Worker administration after fresh vendor evidence proves execution stopped."""
        if not observation.strip():
            raise ValueError("Reconciliation requires a fresh observation")
        with self._lock, self.connection:
            cursor = self.connection.execute(
                """UPDATE resource_ownership SET state = 'idle', expires_at = 0
                WHERE resource = ? AND owner = ? AND fencing_token = ?
                AND state IN ('uncertain', 'active')""",
                (lease.resource, lease.owner, lease.fencing_token),
            )
            if cursor.rowcount:
                self.connection.execute(
                    "INSERT INTO reconciliations VALUES (?, ?, ?, ?, ?)",
                    (
                        lease.resource,
                        lease.owner,
                        lease.fencing_token,
                        time.time(),
                        json.dumps({"observation": observation}),
                    ),
                )
        return cursor.rowcount == 1
