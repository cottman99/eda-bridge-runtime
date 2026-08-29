import hashlib
import json

from eda_bridge_runtime.agent_audit import audit_events, record_codex_hook
from eda_bridge_runtime.ledger import ExecutionLedger
from eda_bridge_runtime.protocol import RUN_VIEW_PROTOCOL


def _event(tool_call_id="tool-one"):
    return {
        "session_id": "session-one",
        "turn_id": "turn-one",
        "cwd": "/workspace",
        "hook_event_name": "PreToolUse",
        "model": "gpt-test",
        "permission_mode": "dontAsk",
        "tool_name": "mcp__eda_bridge_runtime__eda_submit",
        "tool_use_id": tool_call_id,
        "tool_input": {
            "purpose": "Inspect one synthetic design",
            "operation": "status",
            "payload": {"mutating": False, "private_value": "not-recorded"},
        },
    }


def test_codex_hook_records_hash_chained_identity_without_raw_payload(tmp_path):
    database = tmp_path / "agent-audit.sqlite3"
    pre = _event()
    assert record_codex_hook(pre, phase="pre", database=database) is True
    post = {
        **pre,
        "hook_event_name": "PostToolUse",
        "tool_response": {
            "structuredContent": {
                "run": {
                    "protocol": RUN_VIEW_PROTOCOL,
                    "run_id": "run-one",
                    "request_id": "request-one",
                    "job_id": "job-one",
                    "state": "passed",
                    "terminal": True,
                }
            }
        },
    }
    assert record_codex_hook(post, phase="post", database=database) is True

    events = audit_events(database)
    assert [item["event_type"] for item in events] == [
        "agent.tool.requested",
        "agent.tool.completed",
    ]
    payload = events[0]["payload"]
    assert payload["actor"]["model"] == {"value": "gpt-test", "provenance": "observed"}
    assert payload["actor"]["session_id"]["value"] == "session-one"
    assert payload["purpose"] == "Inspect one synthetic design"
    assert "not-recorded" not in json.dumps(events)
    assert events[1]["payload"]["execution"]["run_id"] == "run-one"
    run_id = "agent_" + hashlib.sha256(b"tool-one").hexdigest()[:32]
    with ExecutionLedger(database) as ledger:
        assert ledger.verify(run_id) is True


def test_codex_hook_ignores_unrelated_tools(tmp_path):
    event = {**_event(), "tool_name": "Bash"}
    database = tmp_path / "agent-audit.sqlite3"
    assert record_codex_hook(event, phase="pre", database=database) is False
    assert not database.exists()


def test_codex_hook_records_diagnostic_runtime_calls(tmp_path):
    event = {
        **_event("tool-diagnostic"),
        "tool_name": "mcp__eda_bridge_runtime__eda_connections_list",
        "tool_input": {},
    }
    database = tmp_path / "agent-audit.sqlite3"
    assert record_codex_hook(event, phase="pre", database=database) is True
    assert audit_events(database)[0]["payload"]["tool"] == "eda.connections.list"


def test_codex_hook_accepts_protocol_native_mcp_names(tmp_path):
    event = {
        **_event("tool-native-name"),
        "tool_name": "mcp__eda-bridge-runtime__eda.connections.list",
        "tool_input": {},
    }
    database = tmp_path / "agent-audit.sqlite3"
    assert record_codex_hook(event, phase="pre", database=database) is True
    assert audit_events(database)[0]["payload"]["tool"] == "eda.connections.list"
