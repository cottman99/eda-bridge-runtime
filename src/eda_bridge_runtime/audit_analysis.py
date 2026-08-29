"""Bounded efficiency analysis over the Runtime's existing fact log."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

_DISCOVERY_TOOLS = {
    "eda.capabilities",
    "eda.connections.list",
    "eda.context.resolve",
}


def _known_actor_value(actor: dict[str, Any], name: str) -> str | None:
    sourced = actor.get(name) if isinstance(actor.get(name), dict) else {}
    value = str(sourced.get("value") or "").strip()
    provenance = str(sourced.get("provenance") or "unknown")
    if not value or value == "unknown" or provenance == "unknown":
        return None
    return value


def _calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: dict[str, dict[str, Any]] = {}
    for event in events:
        run_id = str(event.get("run_id") or "")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        if event.get("event_type") == "agent.tool.requested":
            actor = payload.get("actor") if isinstance(payload.get("actor"), dict) else {}
            calls[run_id] = {
                "tool": str(payload.get("tool") or "unknown"),
                "action_sha256": str(
                    payload.get("action_sha256") or payload.get("input_sha256") or ""
                ),
                "session_id": _known_actor_value(actor, "session_id"),
                "completed": False,
                "state": "unknown",
                "execution_run_id": None,
                "job_id": None,
                "mcp_server_ms": None,
                "client_transport_ms": None,
            }
        elif event.get("event_type") == "agent.tool.completed" and run_id in calls:
            execution = (
                payload.get("execution") if isinstance(payload.get("execution"), dict) else {}
            )
            timing = payload.get("timing") if isinstance(payload.get("timing"), dict) else {}
            calls[run_id].update(
                {
                    "completed": True,
                    "state": str(execution.get("state") or "unknown"),
                    "execution_run_id": execution.get("run_id"),
                    "job_id": execution.get("job_id"),
                    "mcp_server_ms": timing.get("mcp_server_ms"),
                    "client_transport_ms": timing.get("client_transport_ms"),
                }
            )
    return list(calls.values())


def analyze_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Return aggregate facts and conservative findings without raw inputs or identifiers."""
    calls = _calls(events)
    replay_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    scoped_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for call in calls:
        replay_groups[(call["tool"], call["action_sha256"])].append(call)
        if call["session_id"]:
            scoped_groups[(call["session_id"], call["tool"], call["action_sha256"])].append(call)

    idempotent_replays = sum(
        len(grouped) - 1
        for grouped in replay_groups.values()
        if len(grouped) > 1
        and len({call["execution_run_id"] for call in grouped if call["execution_run_id"]}) == 1
        and all(call["completed"] for call in grouped)
    )
    redundant_discovery = 0
    redundant_discovery_ms = 0.0
    repeated_failures = 0
    repeated_failure_ms = 0.0
    for (_, tool, _), grouped in scoped_groups.items():
        if len(grouped) < 2:
            continue
        execution_runs = {call["execution_run_id"] for call in grouped if call["execution_run_id"]}
        is_replay = len(execution_runs) == 1 and all(call["completed"] for call in grouped)
        if tool in _DISCOVERY_TOOLS and not is_replay:
            redundant_discovery += len(grouped) - 1
            redundant_discovery_ms += sum(float(call["mcp_server_ms"] or 0) for call in grouped[1:])
        failed = [call for call in grouped if call["state"] == "failed"]
        if len(failed) > 1:
            repeated_failures += len(failed) - 1
            repeated_failure_ms += sum(float(call["mcp_server_ms"] or 0) for call in failed[1:])

    status_by_job: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for call in calls:
        if call["tool"] == "eda.job.status" and call["job_id"] and call["session_id"]:
            status_by_job[(call["session_id"], str(call["job_id"]))].append(call)
    avoidable_status_polls = sum(max(0, len(grouped) - 1) for grouped in status_by_job.values())
    avoidable_status_poll_ms = sum(
        float(call["mcp_server_ms"] or 0)
        for grouped in status_by_job.values()
        for call in grouped[1:]
    )

    timing_by_tool: dict[str, dict[str, float | int]] = {}
    for tool in sorted({call["tool"] for call in calls}):
        selected = [call for call in calls if call["tool"] == tool]
        server = [
            float(call["mcp_server_ms"]) for call in selected if call["mcp_server_ms"] is not None
        ]
        transport = [
            float(call["client_transport_ms"])
            for call in selected
            if call["client_transport_ms"] is not None
        ]
        timing_by_tool[tool] = {
            "calls": len(selected),
            "mcp_server_ms_total": round(sum(server), 3),
            "client_transport_ms_total": round(sum(transport), 3),
        }

    findings = []
    for code, count in (
        ("potential_redundant_discovery", redundant_discovery),
        ("repeated_failed_action", repeated_failures),
        ("avoidable_status_poll", avoidable_status_polls),
    ):
        if count:
            findings.append({"code": code, "count": count})
    return {
        "schema_version": "eda-runtime.audit-analysis/v1",
        "event_count": len(events),
        "tool_calls": len(calls),
        "completed_calls": sum(call["completed"] for call in calls),
        "failed_calls": sum(call["state"] == "failed" for call in calls),
        "idempotent_replays": idempotent_replays,
        "potential_avoidable_mcp_ms": round(
            redundant_discovery_ms + repeated_failure_ms + avoidable_status_poll_ms,
            3,
        ),
        "findings": findings,
        "timing_by_tool": timing_by_tool,
    }
