from eda_bridge_runtime.audit_analysis import analyze_events


def pair(run_id, tool, action, state="passed", execution_run=None, job_id=None, ms=10):
    return [
        {
            "run_id": run_id,
            "event_type": "agent.tool.requested",
            "payload": {"tool": tool, "action_sha256": action},
        },
        {
            "run_id": run_id,
            "event_type": "agent.tool.completed",
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
