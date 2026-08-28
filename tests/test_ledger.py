import json
import sqlite3

import pytest

from eda_bridge_runtime.ledger import ExecutionLedger
from eda_bridge_runtime.protocol import RequestEnvelope


def test_ledger_hash_chain_and_finalization(tmp_path):
    ledger = ExecutionLedger(tmp_path / "ledger.sqlite3")
    first = ledger.append(
        run_id="run-1", request_id="req-1", event_type="started", source="test", payload={}
    )
    second = ledger.append(
        run_id="run-1", request_id="req-1", event_type="done", source="test", payload={}
    )
    assert second["previous_hash"] == first["event_hash"]
    assert ledger.verify("run-1")
    ledger.finalize("run-1")
    with pytest.raises(ValueError, match="finalized"):
        ledger.append(
            run_id="run-1", request_id="req-1", event_type="late", source="test", payload={}
        )


def test_ledger_redacts_secrets(tmp_path):
    ledger = ExecutionLedger(tmp_path / "ledger.sqlite3")
    ledger.append(
        run_id="run-1",
        request_id="req-1",
        event_type="test",
        source="test",
        payload={"auth_token": "abc", "message": "Bearer abc.def"},
    )
    payload = ledger.events()[0]["payload"]
    assert payload == {"auth_token": "[REDACTED]", "message": "Bearer [REDACTED]"}


def test_events_are_database_append_only(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    ledger = ExecutionLedger(path)
    ledger.append(run_id="run-1", request_id="req-1", event_type="test", source="test", payload={})
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        ledger._connection.execute("DELETE FROM events")


def test_export_is_valid_ndjson(tmp_path):
    ledger = ExecutionLedger(tmp_path / "ledger.sqlite3")
    ledger.append(
        run_id="run-1", request_id="req-1", event_type="test", source="test", payload={"x": 1}
    )
    destination = tmp_path / "events.ndjson"
    ledger.export_ndjson(destination)
    assert json.loads(destination.read_text())["payload"] == {"x": 1}


def test_idempotency_claim_is_persistent_and_detects_conflict(tmp_path):
    ledger = ExecutionLedger(tmp_path / "ledger.sqlite3")
    request = RequestEnvelope(
        purpose="Change one property",
        target={"eda": "fake"},
        operation="set",
        payload={"value": 1},
        idempotency_key="property-1",
    )
    assert ledger.claim_idempotency(request)["state"] == "claimed"
    assert ledger.claim_idempotency(request)["state"] == "in_progress"
    ledger.complete_idempotency(request, {"status": "passed", "request_id": request.request_id})
    assert ledger.claim_idempotency(request)["state"] == "completed"
    conflicting = RequestEnvelope(
        purpose="Change another property",
        target={"eda": "fake"},
        operation="set",
        payload={"value": 2},
        idempotency_key="property-1",
    )
    assert ledger.claim_idempotency(conflicting)["state"] == "conflict"
