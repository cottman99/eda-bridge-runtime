"""SQLite-backed resource leases with monotonically increasing fencing tokens."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Lease:
    resource: str
    owner: str
    fencing_token: int
    expires_at: float


class LeaseStore:
    def __init__(self, path: str | Path):
        self.connection = sqlite3.connect(path, timeout=30)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS leases (
            resource TEXT PRIMARY KEY, owner TEXT NOT NULL, fencing_token INTEGER NOT NULL,
            expires_at REAL NOT NULL)"""
        )
        self.connection.commit()

    def acquire(self, resource: str, owner: str, ttl_seconds: float = 60) -> Lease:
        now = time.time()
        with self.connection:
            row = self.connection.execute(
                "SELECT owner, fencing_token, expires_at FROM leases WHERE resource = ?",
                (resource,),
            ).fetchone()
            if row and row[2] > now and row[0] != owner:
                raise RuntimeError(f"resource is leased: {resource}")
            token = 1 if row is None else int(row[1]) + 1
            expires = now + ttl_seconds
            self.connection.execute(
                "INSERT OR REPLACE INTO leases VALUES (?, ?, ?, ?)",
                (resource, owner, token, expires),
            )
        return Lease(resource, owner, token, expires)

    def renew(self, lease: Lease, ttl_seconds: float = 60) -> Lease:
        expires = time.time() + ttl_seconds
        with self.connection:
            cursor = self.connection.execute(
                """UPDATE leases SET expires_at = ?
                WHERE resource = ? AND owner = ? AND fencing_token = ?""",
                (expires, lease.resource, lease.owner, lease.fencing_token),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("stale lease cannot be renewed")
        return Lease(lease.resource, lease.owner, lease.fencing_token, expires)

    def release(self, lease: Lease) -> bool:
        with self.connection:
            cursor = self.connection.execute(
                "DELETE FROM leases WHERE resource = ? AND owner = ? AND fencing_token = ?",
                (lease.resource, lease.owner, lease.fencing_token),
            )
        return cursor.rowcount == 1
