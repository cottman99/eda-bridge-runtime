"""Recheck Worker-issued execution ownership at a vendor boundary."""

from __future__ import annotations

from .lease import Lease, LeaseStore


def assert_admission(ticket: dict) -> None:
    if not ticket or not ticket.get("leases"):
        raise ValueError("Native execution requires a Worker admission ticket")
    store = LeaseStore(ticket["store"])
    try:
        for value in ticket["leases"]:
            store.assert_current(Lease(**value))
    finally:
        store.connection.close()
