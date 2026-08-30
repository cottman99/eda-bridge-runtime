import hashlib
import json

import pytest

from eda_bridge_runtime.agent_audit import (
    audit_events,
    compact_audit_calls,
    compact_audit_calls_from_database,
    record_codex_hook,
    record_runtime_bypass,
)
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


def test_compact_audit_calls_preserve_motive_and_identity_without_forensic_noise(tmp_path):
    database = tmp_path / "agent-audit.sqlite3"
    pre = _event("tool-compact")
    record_codex_hook(pre, phase="pre", database=database)
    record_codex_hook(
        {
            **pre,
            "tool_response": {
                "structuredContent": {
                    "run": {
                        "protocol": RUN_VIEW_PROTOCOL,
                        "run_id": "run-compact",
                        "request_id": "request-compact",
                        "state": "passed",
                        "terminal": True,
                    }
                }
            },
        },
        phase="post",
        database=database,
    )

    calls = compact_audit_calls(audit_events(database))

    assert calls == [
        {
            "timestamp": calls[0]["timestamp"],
            "source": "codex-hook",
            "status": "passed",
            "tool": "eda.submit",
            "purpose": "Inspect one synthetic design",
            "actor": {
                "agent_family": "codex",
                "model": "gpt-test",
                "session_id": "session-one",
            },
            "terminal": True,
            "execution_run_id": "run-compact",
        }
    ]
    assert "input_sha256" not in json.dumps(calls)


def test_runtime_bypass_is_visible_but_never_records_a_raw_command(tmp_path):
    database = tmp_path / "agent-audit.sqlite3"
    run_id = record_runtime_bypass(
        purpose="Close a legacy user interface safely",
        lane="gui",
        reason="No typed lifecycle operation was available in the installed Bridge",
        outcome="passed",
        database=database,
    )
    calls = compact_audit_calls(audit_events(database))
    assert calls == [
        {
            "timestamp": calls[0]["timestamp"],
            "source": "runtime-bypass",
            "status": "passed",
            "tool": "external.gui",
            "purpose": "Close a legacy user interface safely",
            "reason": "No typed lifecycle operation was available in the installed Bridge",
            "terminal": True,
        }
    ]
    assert run_id.startswith("bypass_")
    assert "legacy user interface safely" in json.dumps(calls)
    assert "taskkill" not in json.dumps(audit_events(database))


def test_audit_list_cli_is_compact_by_default_and_full_only_when_requested(tmp_path, capsys):
    from eda_bridge_runtime.cli import main

    database = tmp_path / "agent-audit.sqlite3"
    record_codex_hook(_event("tool-cli"), phase="pre", database=database)

    assert main(["audit", "list", "--database", str(database), "--limit", "1"]) == 0
    compact = json.loads(capsys.readouterr().out)
    assert compact["schema_version"] == "eda-runtime.audit-calls/v1"
    assert compact["source_policy"] == "mcp-runtime-preferred"
    assert compact["calls"][0]["purpose"] == "Inspect one synthetic design"
    assert "input_sha256" not in json.dumps(compact)

    assert main(["audit", "list", "--database", str(database), "--limit", "1", "--full"]) == 0
    full = json.loads(capsys.readouterr().out)
    assert full["events"][0]["payload"]["input_sha256"]


def test_compact_audit_calls_prefer_runtime_facts_over_duplicate_hook_observation():
    actor = {
        "client": {"value": "codex", "provenance": "observed"},
    }
    events = [
        {
            "run_id": "hook-one",
            "timestamp": "2026-01-01T00:00:00Z",
            "event_type": "agent.tool.requested",
            "source": "codex-hook",
            "payload": {
                "tool": "eda.read",
                "purpose": "Inspect design",
                "actor": actor,
            },
        },
        {
            "run_id": "runtime-one",
            "timestamp": "2026-01-01T00:00:01Z",
            "event_type": "agent.tool.requested",
            "source": "mcp-runtime",
            "payload": {
                "tool": "eda.read",
                "purpose": "Inspect design",
                "actor": actor,
            },
        },
        {
            "run_id": "runtime-one",
            "timestamp": "2026-01-01T00:00:02Z",
            "event_type": "agent.tool.completed",
            "source": "mcp-runtime",
            "payload": {
                "execution": {
                    "state": "passed",
                    "terminal": True,
                    "connection_id": "ansys-one",
                    "eda": "ansys-electronics-desktop",
                    "operation": "runtime.snapshot",
                    "evidence_refs": [{"kind": "snapshot", "sha256": "abc"}],
                    "resource": {
                        "resource_id": "session-one",
                        "kind": "aedt-desktop",
                        "ownership": "runtime-owned",
                        "state": "active",
                        "release_operation": "session.release",
                    },
                },
                "timing": {
                    "mcp_server_ms": 12.0,
                    "bridge": {"adapter_total_ms": 8.5},
                },
            },
        },
    ]

    calls = compact_audit_calls(events)

    assert len(calls) == 1
    assert calls[0]["source"] == "mcp-runtime"
    assert calls[0]["status"] == "passed"
    assert calls[0]["connection_id"] == "ansys-one"
    assert calls[0]["operation"] == "runtime.snapshot"
    assert calls[0]["evidence_count"] == 1
    assert calls[0]["resource"]["state"] == "active"
    assert calls[0]["bridge_timing"] == {"adapter_total_ms": 8.5}


def test_compact_database_read_keeps_interleaved_request_and_completion_together(tmp_path):
    database = tmp_path / "interleaved.sqlite3"
    with ExecutionLedger(database) as ledger:
        for run_id, purpose in (("run-one", "First call"), ("run-two", "Second call")):
            ledger.append(
                run_id=run_id,
                request_id=f"request-{run_id}",
                event_type="agent.tool.requested",
                source="mcp-runtime",
                payload={"tool": "eda.read", "purpose": purpose},
            )
        for run_id in ("run-one", "run-two"):
            ledger.append(
                run_id=run_id,
                request_id=f"request-{run_id}",
                event_type="agent.tool.completed",
                source="mcp-runtime",
                payload={
                    "execution": {"state": "passed", "terminal": True},
                    "timing": {"mcp_server_ms": 1.0},
                },
            )
            ledger.finalize(run_id)

    calls = compact_audit_calls_from_database(database, limit=2)

    assert [call["purpose"] for call in calls] == ["First call", "Second call"]
    assert all(call["status"] == "passed" for call in calls)


def test_compact_database_read_filters_complete_calls_by_session_and_execution_run(tmp_path):
    database = tmp_path / "filtered.sqlite3"
    with ExecutionLedger(database) as ledger:
        for suffix in ("one", "two"):
            ledger.append(
                run_id=f"audit-{suffix}",
                request_id=f"request-{suffix}",
                event_type="agent.tool.requested",
                source="mcp-runtime",
                payload={
                    "tool": "eda.read",
                    "purpose": f"Call {suffix}",
                    "actor": {
                        "session_id": {
                            "value": f"session-{suffix}",
                            "provenance": "declared",
                        }
                    },
                },
            )
            ledger.append(
                run_id=f"audit-{suffix}",
                request_id=f"request-{suffix}",
                event_type="agent.tool.completed",
                source="mcp-runtime",
                payload={
                    "execution": {
                        "state": "passed",
                        "terminal": True,
                        "run_id": f"execution-{suffix}",
                        "job_id": f"job-{suffix}",
                    },
                    "timing": {"mcp_server_ms": 1.0},
                },
            )
            ledger.finalize(f"audit-{suffix}")

    by_session = compact_audit_calls_from_database(database, limit=20, session_id="session-one")
    by_execution = compact_audit_calls_from_database(
        database, limit=20, execution_run_id="execution-two"
    )

    assert [call["purpose"] for call in by_session] == ["Call one"]
    assert by_session[0]["execution_run_id"] == "execution-one"
    assert by_session[0]["job_id"] == "job-one"
    assert [call["purpose"] for call in by_execution] == ["Call two"]


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


@pytest.mark.parametrize(
    ("codex_name", "runtime_name"),
    [
        ("eda_read", "eda.read"),
        ("eda_run_plan", "eda.run_plan"),
        ("eda_job_wait", "eda.job.wait"),
    ],
)
def test_codex_hook_covers_read_and_wait_tools(tmp_path, codex_name, runtime_name):
    event = {
        **_event(f"tool-{codex_name}"),
        "tool_name": f"mcp__eda_bridge_runtime__{codex_name}",
    }
    database = tmp_path / f"{codex_name}.sqlite3"

    assert record_codex_hook(event, phase="pre", database=database) is True
    assert audit_events(database)[0]["payload"]["tool"] == runtime_name


def test_codex_hook_aggregates_plan_state_instead_of_first_successful_step(tmp_path):
    event = {
        **_event("tool-plan"),
        "tool_name": "mcp__eda_bridge_runtime__eda_run_plan",
    }
    database = tmp_path / "plan.sqlite3"
    assert record_codex_hook(event, phase="pre", database=database) is True
    post = {
        **event,
        "tool_response": {
            "structuredContent": {
                "status": "waiting",
                "planned_step_count": 2,
                "steps": [
                    {
                        "step_id": "create",
                        "operation": "project.create",
                        "run": {
                            "protocol": RUN_VIEW_PROTOCOL,
                            "run_id": "run-create",
                            "request_id": "request-create",
                            "job_id": "job-create",
                            "state": "running",
                            "terminal": False,
                        },
                    }
                ],
            }
        },
    }
    assert record_codex_hook(post, phase="post", database=database) is True

    execution = audit_events(database)[1]["payload"]["execution"]
    assert execution["state"] == "waiting"
    assert execution["terminal"] is False
    assert execution["run_id"] is None
    assert execution["job_id"] == "job-create"
    assert execution["steps"][0]["state"] == "running"
