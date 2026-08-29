import json

from eda_bridge_runtime.audit_analysis import analyze_events
from eda_bridge_runtime.cli import main
from eda_bridge_runtime.ledger import ExecutionLedger


def pair(
    run_id,
    tool,
    action,
    state="passed",
    execution_run=None,
    job_id=None,
    ms=10,
    session="session-one",
    source="mcp-runtime",
):
    return [
        {
            "run_id": run_id,
            "event_type": "agent.tool.requested",
            "source": source,
            "payload": {
                "tool": tool,
                "action_sha256": action,
                "actor": {"session_id": {"value": session, "provenance": "declared"}},
            },
        },
        {
            "run_id": run_id,
            "event_type": "agent.tool.completed",
            "source": source,
            "payload": {
                "execution": {
                    "state": state,
                    "run_id": execution_run,
                    "job_id": job_id,
                },
                "timing": {"mcp_server_ms": ms, "client_transport_ms": ms - 1},
            },
        },
    ]


def test_analysis_separates_idempotent_replay_from_waste():
    events = [
        *pair("a", "eda.submit", "same", execution_run="execution-one"),
        *pair("b", "eda.submit", "same", execution_run="execution-one"),
        *pair("c", "eda.capabilities", "caps", execution_run="caps-one"),
        *pair("d", "eda.capabilities", "caps", execution_run="caps-two"),
    ]

    result = analyze_events(events)

    assert result["idempotent_replays"] == 1
    assert result["findings"] == [{"code": "potential_redundant_discovery", "count": 1}]
    assert result["potential_avoidable_mcp_ms"] == 10
    assert result["timing_totals"] == {
        "mcp_server_ms": 40.0,
        "paired_mcp_server_ms": 40.0,
        "client_transport_ms": 36.0,
        "runtime_nontransport_ms": 4.0,
        "unpaired_mcp_server_ms": 0,
        "paired_calls": 4,
        "unpaired_calls": 0,
        "transport_share_percent": 90.0,
    }
    assert result["timing_by_tool"]["eda.capabilities"] == {
        "calls": 2,
        "completed_calls": 2,
        "failed_calls": 0,
        "paired_timing_calls": 2,
        "unpaired_timing_calls": 0,
        "mcp_server_ms_total": 20.0,
        "mcp_server_ms_median": 10.0,
        "paired_mcp_server_ms_total": 20.0,
        "client_transport_ms_total": 18.0,
        "client_transport_ms_median": 9.0,
        "runtime_nontransport_ms_total": 2.0,
        "runtime_nontransport_ms_median": 1.0,
        "unpaired_mcp_server_ms_total": 0,
        "transport_share_percent": 90.0,
    }


def test_analysis_finds_repeated_failure_and_status_polling_without_ids():
    events = [
        *pair("a", "eda.submit", "bad", state="failed"),
        *pair("b", "eda.submit", "bad", state="failed"),
        *pair("c", "eda.job.status", "one", job_id="private-job"),
        *pair("d", "eda.job.status", "two", job_id="private-job"),
        *pair("e", "eda.job.status", "three", job_id="private-job"),
    ]

    result = analyze_events(events)

    assert {item["code"]: item["count"] for item in result["findings"]} == {
        "repeated_failed_action": 1,
        "avoidable_status_poll": 2,
    }
    assert result["potential_avoidable_mcp_ms"] == 30
    assert "private-job" not in str(result)


def test_analysis_does_not_call_cross_session_or_unscoped_repetition_waste():
    events = [
        *pair("a", "eda.capabilities", "caps", session="session-one"),
        *pair("b", "eda.capabilities", "caps", session="session-two"),
        *pair("c", "eda.capabilities", "caps", session=None),
        *pair("d", "eda.capabilities", "caps", session=None),
        *pair("e", "eda.job.status", "poll", job_id="job", session="session-one"),
        *pair("f", "eda.job.status", "poll", job_id="job", session="session-two"),
    ]

    result = analyze_events(events)

    assert result["findings"] == []
    assert result["potential_avoidable_mcp_ms"] == 0


def test_analysis_treats_unknown_actor_session_as_unscoped():
    events = [
        *pair("a", "eda.capabilities", "caps", session="unknown"),
        *pair("b", "eda.capabilities", "caps", session="unknown"),
    ]

    result = analyze_events(events)

    assert result["findings"] == []


def test_analysis_scopes_repetition_to_inferred_mcp_lifecycle():
    events = [
        *pair("a", "eda.capabilities", "caps", session="mcp-one"),
        *pair("b", "eda.capabilities", "caps", session="mcp-one"),
    ]
    for event in events:
        if event["event_type"] == "agent.tool.requested":
            event["payload"]["actor"]["session_id"]["provenance"] = "inferred"

    result = analyze_events(events)

    assert result["findings"] == [{"code": "potential_redundant_discovery", "count": 1}]
    assert result["potential_avoidable_mcp_ms"] == 10


def test_analysis_prefers_runtime_observation_over_duplicate_hook_observation():
    events = [
        *pair("hook", "eda.read", "same", source="codex-hook"),
        *pair("runtime", "eda.read", "same", source="mcp-runtime"),
    ]

    result = analyze_events(events)

    assert result["source_policy"] == "mcp-runtime-preferred"
    assert result["tool_calls"] == 1
    assert result["completed_calls"] == 1
    assert result["event_count"] == 2


def test_audit_analyze_reads_complete_interleaved_runtime_calls(tmp_path, capsys):
    database = tmp_path / "interleaved.sqlite3"
    with ExecutionLedger(database) as ledger:
        for run_id in ("run-one", "run-two"):
            ledger.append(
                run_id=run_id,
                request_id=f"request-{run_id}",
                event_type="agent.tool.requested",
                source="mcp-runtime",
                payload={
                    "tool": "eda.read",
                    "action_sha256": run_id,
                    "actor": {"session_id": {"value": "session", "provenance": "declared"}},
                },
            )
        for run_id in ("run-one", "run-two"):
            ledger.append(
                run_id=run_id,
                request_id=f"request-{run_id}",
                event_type="agent.tool.completed",
                source="mcp-runtime",
                payload={
                    "execution": {"state": "passed", "run_id": run_id},
                    "timing": {"mcp_server_ms": 1.0},
                },
            )
            ledger.finalize(run_id)

    assert main(["audit", "analyze", "--database", str(database), "--limit", "2"]) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["tool_calls"] == 2
    assert result["completed_calls"] == 2
    assert result["failed_calls"] == 0
