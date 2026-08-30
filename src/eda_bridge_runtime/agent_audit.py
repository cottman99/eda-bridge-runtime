"""Agent-host audit events captured outside the model context."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .ledger import ExecutionLedger
from .protocol import RUN_VIEW_PROTOCOL, ActorIdentity, new_id

AGENT_AUDIT_PROTOCOL = "eda-runtime.agent-audit/v1"
_RUNTIME_TOOL = re.compile(r"^mcp__(?P<server>.+)__(?P<tool>.+)$")
_TOOL_NAMES = {
    "eda_capabilities": "eda.capabilities",
    "eda_read": "eda.read",
    "eda_submit": "eda.submit",
    "eda_run_plan": "eda.run_plan",
    "eda_job_status": "eda.job.status",
    "eda_job_wait": "eda.job.wait",
    "eda_job_events": "eda.job.events",
    "eda_connections_list": "eda.connections.list",
    "eda_connection_reset": "eda.connection.reset",
    "eda_context_resolve": "eda.context.resolve",
    "eda.capabilities": "eda.capabilities",
    "eda.read": "eda.read",
    "eda.submit": "eda.submit",
    "eda.run_plan": "eda.run_plan",
    "eda.job.status": "eda.job.status",
    "eda.job.wait": "eda.job.wait",
    "eda.job.events": "eda.job.events",
    "eda.connections.list": "eda.connections.list",
    "eda.connection.reset": "eda.connection.reset",
    "eda.context.resolve": "eda.context.resolve",
}


def default_agent_audit_path() -> Path:
    root = Path(os.environ.get("EDA_RUNTIME_HOME", Path.home() / ".eda-bridge-runtime"))
    return root / "agent-audit.sqlite3"


def record_codex_hook(
    event: Mapping[str, Any],
    *,
    phase: str,
    database: str | Path | None = None,
) -> bool:
    """Record one Codex lifecycle fact without changing the pending tool call."""
    if phase not in {"pre", "post"}:
        raise ValueError(f"unsupported hook phase: {phase}")
    tool_name = str(event.get("tool_name") or "")
    match = _RUNTIME_TOOL.fullmatch(tool_name)
    if match is None:
        return False
    server_name = match.group("server").lower().replace("-", "_")
    native_tool_name = match.group("tool")
    if server_name != "eda_bridge_runtime" or native_tool_name not in _TOOL_NAMES:
        return False
    tool_call_id = str(event.get("tool_use_id") or "").strip()
    session_id = str(event.get("session_id") or "").strip()
    if not tool_call_id or not session_id:
        return False
    tool_input = event.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, Mapping) else {}
    purpose = str(tool_input.get("purpose") or "unspecified EDA operation")[:240]
    fingerprint = _fingerprint(tool_name, tool_input)
    action_fingerprint = _fingerprint(
        tool_name, {key: value for key, value in tool_input.items() if key != "purpose"}
    )
    actor = ActorIdentity.detect(
        observed={
            key: value
            for key, value in {
                "agent_family": "codex",
                "model": event.get("model"),
                "session_id": session_id,
                "turn_id": event.get("turn_id"),
                "tool_call_id": tool_call_id,
                "permission_mode": event.get("permission_mode"),
            }.items()
            if value
        },
        inferred={"harness": "mcp"},
    )
    run_id = _audit_run_id(tool_call_id)
    request_id = str(event.get("turn_id") or session_id)
    payload: dict[str, Any] = {
        "protocol": AGENT_AUDIT_PROTOCOL,
        "actor": actor.to_dict(),
        "tool": _TOOL_NAMES[native_tool_name],
        "purpose": purpose,
        "input_sha256": fingerprint,
        "action_sha256": action_fingerprint,
    }
    event_type = "agent.tool.requested"
    if phase == "post":
        event_type = "agent.tool.completed"
        payload["execution"] = _execution_reference(event.get("tool_response"))
    with ExecutionLedger(database or default_agent_audit_path()) as ledger:
        ledger.append(
            run_id=run_id,
            request_id=request_id,
            event_type=event_type,
            source="codex-hook",
            payload=payload,
        )
        if phase == "post":
            ledger.finalize(run_id)
    return True


def record_runtime_bypass(
    *,
    purpose: str,
    lane: str,
    reason: str,
    outcome: str,
    database: str | Path | None = None,
) -> str:
    """Record an unavoidable operation outside Runtime without storing its command."""
    purpose = purpose.strip()
    reason = reason.strip()
    if not 3 <= len(purpose) <= 240:
        raise ValueError("purpose must contain 3..240 non-whitespace characters")
    if not 3 <= len(reason) <= 240:
        raise ValueError("reason must contain 3..240 non-whitespace characters")
    if lane not in {"shell", "gui", "vendor-cli", "other"}:
        raise ValueError("unsupported bypass lane")
    if outcome not in {"passed", "failed", "blocked", "unknown"}:
        raise ValueError("unsupported bypass outcome")
    run_id = new_id("bypass")
    request_id = new_id("req")
    action = json.dumps(
        {"lane": lane, "reason": reason, "outcome": outcome},
        sort_keys=True,
        separators=(",", ":"),
    )
    actor = ActorIdentity.detect(inferred={"harness": "external-bypass"})
    with ExecutionLedger(database or default_agent_audit_path()) as ledger:
        ledger.append(
            run_id=run_id,
            request_id=request_id,
            event_type="agent.tool.requested",
            source="runtime-bypass",
            payload={
                "protocol": AGENT_AUDIT_PROTOCOL,
                "actor": actor.to_dict(),
                "tool": f"external.{lane}",
                "purpose": purpose,
                "reason": reason,
                "action_sha256": hashlib.sha256(action.encode("utf-8")).hexdigest(),
            },
        )
        ledger.append(
            run_id=run_id,
            request_id=request_id,
            event_type="agent.tool.completed",
            source="runtime-bypass",
            payload={
                "protocol": AGENT_AUDIT_PROTOCOL,
                "execution": {"linked": False, "state": outcome, "terminal": True},
            },
        )
        ledger.finalize(run_id)
    return run_id


def audit_events(database: str | Path | None = None, *, limit: int = 20) -> list[dict[str, Any]]:
    with ExecutionLedger(database or default_agent_audit_path()) as ledger:
        events = ledger.events()
    return events[-max(1, min(limit, 1000)) :]


def compact_audit_calls_from_database(
    database: str | Path | None = None,
    *,
    limit: int = 20,
    session_id: str | None = None,
    execution_run_id: str | None = None,
) -> list[dict[str, Any]]:
    """Read complete recent Runtime calls without assuming adjacent event writes."""
    events = recent_audit_run_events(
        database,
        limit=limit,
        session_id=session_id,
        execution_run_id=execution_run_id,
    )
    return compact_audit_calls(events)[-max(1, min(limit, 1000)) :]


def recent_audit_run_events(
    database: str | Path | None = None,
    *,
    limit: int = 20,
    session_id: str | None = None,
    execution_run_id: str | None = None,
) -> list[dict[str, Any]]:
    """Read complete recent call groups from the authoritative observation source."""
    scan_limit = 1000 if session_id or execution_run_id else limit
    with ExecutionLedger(database or default_agent_audit_path()) as ledger:
        events = ledger.recent_run_events(limit=min(1000, max(20, scan_limit * 3)))
    canonical = [
        event for event in events if event.get("source") in {"mcp-runtime", "runtime-bypass"}
    ]
    if canonical:
        events = canonical
    selected = select_audit_run_events(
        events,
        session_id=session_id,
        execution_run_id=execution_run_id,
    )
    return _last_run_groups(selected, limit=limit)


def select_audit_run_events(
    events: list[dict[str, Any]],
    *,
    session_id: str | None = None,
    execution_run_id: str | None = None,
) -> list[dict[str, Any]]:
    """Select complete audit call groups using stable Runtime-observed identities."""
    if not session_id and not execution_run_id:
        return events
    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for event in events:
        audit_run_id = str(event.get("run_id") or "")
        if not audit_run_id:
            continue
        if audit_run_id not in grouped:
            grouped[audit_run_id] = []
            order.append(audit_run_id)
        grouped[audit_run_id].append(event)
    selected: list[dict[str, Any]] = []
    for audit_run_id in order:
        call_events = grouped[audit_run_id]
        sessions: set[str] = set()
        execution_runs: set[str] = set()
        for event in call_events:
            payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
            actor = payload.get("actor") if isinstance(payload.get("actor"), Mapping) else {}
            actor_session = _actor_value(actor, "session_id")
            if actor_session:
                sessions.add(actor_session)
            execution = (
                payload.get("execution") if isinstance(payload.get("execution"), Mapping) else {}
            )
            execution_run = str(execution.get("run_id") or "")
            if execution_run:
                execution_runs.add(execution_run)
            for step in execution.get("steps") or []:
                if isinstance(step, Mapping) and step.get("run_id"):
                    execution_runs.add(str(step["run_id"]))
        if session_id and session_id not in sessions:
            continue
        if execution_run_id and execution_run_id not in execution_runs:
            continue
        selected.extend(call_events)
    return selected


def _last_run_groups(events: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    bounded = max(1, min(int(limit), 1000))
    order = list(dict.fromkeys(str(event.get("run_id") or "") for event in events))
    selected = set(run_id for run_id in order[-bounded:] if run_id)
    return [event for event in events if str(event.get("run_id") or "") in selected]


def compact_audit_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project full events into authoritative, context-light Runtime calls.

    Codex hooks and MCP can both observe one invocation without exposing a shared
    correlation id. Runtime observations are therefore canonical when present;
    hook-only rows are a fallback for databases that contain no Runtime records.
    """
    calls: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for event in events:
        run_id = str(event.get("run_id") or "")
        if not run_id:
            continue
        event_type = str(event.get("event_type") or "")
        payload = event.get("payload")
        payload = payload if isinstance(payload, Mapping) else {}
        if run_id not in calls:
            calls[run_id] = {
                "timestamp": event.get("timestamp"),
                "source": event.get("source"),
                "status": "observed",
            }
            order.append(run_id)
        row = calls[run_id]
        if event_type == "agent.tool.requested":
            row.update(
                {
                    "timestamp": event.get("timestamp"),
                    "source": event.get("source"),
                    "tool": payload.get("tool"),
                    "purpose": payload.get("purpose"),
                    "status": "requested",
                }
            )
            actor = _compact_actor(payload.get("actor"))
            if actor:
                row["actor"] = actor
            if event.get("source") == "runtime-bypass" and payload.get("reason"):
                row["reason"] = payload["reason"]
            plan_steps = payload.get("plan_steps")
            if isinstance(plan_steps, list):
                row["plan_step_count"] = len(plan_steps)
        elif event_type == "agent.tool.completed":
            execution = payload.get("execution")
            execution = execution if isinstance(execution, Mapping) else {}
            row["status"] = execution.get("state") or "completed"
            row["terminal"] = bool(execution.get("terminal", False))
            if execution.get("run_id"):
                row["execution_run_id"] = execution["run_id"]
            if execution.get("job_id"):
                row["job_id"] = execution["job_id"]
            for key in ("connection_id", "eda", "operation"):
                if execution.get(key):
                    row[key] = execution[key]
            evidence_refs = execution.get("evidence_refs")
            if isinstance(evidence_refs, list):
                row["evidence_count"] = len(evidence_refs)
            resource = execution.get("resource")
            if isinstance(resource, Mapping):
                row["resource"] = {
                    key: resource[key]
                    for key in (
                        "resource_id",
                        "kind",
                        "ownership",
                        "state",
                        "release_operation",
                    )
                    if resource.get(key) is not None
                }
            steps = execution.get("steps")
            if isinstance(steps, list):
                row["completed_step_count"] = len(steps)
                execution_run_ids = [
                    str(step["run_id"])
                    for step in steps
                    if isinstance(step, Mapping) and step.get("run_id")
                ]
                if execution_run_ids:
                    row["execution_run_ids"] = execution_run_ids
            timing = payload.get("timing")
            timing = timing if isinstance(timing, Mapping) else {}
            if timing.get("mcp_server_ms") is not None:
                row["elapsed_ms"] = timing["mcp_server_ms"]
            bridge = timing.get("bridge")
            if isinstance(bridge, Mapping):
                row["bridge_timing"] = dict(bridge)
    rows = [calls[run_id] for run_id in order]
    runtime_rows = [row for row in rows if row.get("source") in {"mcp-runtime", "runtime-bypass"}]
    return runtime_rows or rows


def _compact_actor(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    actor: dict[str, Any] = {}
    for key in (
        "agent_family",
        "agent_version",
        "client",
        "client_version",
        "model",
        "reasoning",
        "skill",
        "session_id",
    ):
        field = value.get(key)
        if not isinstance(field, Mapping):
            continue
        item = field.get("value")
        if item not in {None, "", "unknown"}:
            actor[key] = item
    return actor


def _actor_value(actor: Mapping[str, Any], name: str) -> str | None:
    field = actor.get(name)
    if not isinstance(field, Mapping):
        return None
    value = str(field.get("value") or "").strip()
    return value if value and value != "unknown" else None


def _audit_run_id(tool_call_id: str) -> str:
    digest = hashlib.sha256(tool_call_id.encode("utf-8")).hexdigest()[:32]
    return f"agent_{digest}"


def _fingerprint(tool_name: str, tool_input: Mapping[str, Any]) -> str:
    material = {"tool_name": tool_name, "tool_input": tool_input}
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _execution_reference(value: Any) -> dict[str, Any]:
    if plan := _find_plan_view(value):
        steps = []
        for item in plan.get("steps") or []:
            run = _find_run_view(item)
            if run is not None:
                steps.append(
                    {
                        "step_id": str(item.get("step_id") or "")[:64],
                        "operation": str(item.get("operation") or "")[:160],
                        "run_id": str(run.get("run_id") or "") or None,
                        "request_id": str(run.get("request_id") or "") or None,
                        "job_id": str(run.get("job_id") or "") or None,
                        "state": str(run.get("state") or "unknown"),
                        "terminal": bool(run.get("terminal", False)),
                    }
                )
        status = str(plan.get("status") or "unknown")
        return {
            "linked": bool(steps),
            "run_id": None,
            "request_id": None,
            "job_id": next((step["job_id"] for step in reversed(steps) if step["job_id"]), None),
            "state": status,
            "terminal": status in {"passed", "failed", "cancelled"},
            "steps": steps,
        }
    run = _find_run_view(value)
    if run is None:
        return {"linked": False}
    return {
        "linked": True,
        "run_id": str(run.get("run_id") or "") or None,
        "request_id": str(run.get("request_id") or "") or None,
        "job_id": str(run.get("job_id") or "") or None,
        "state": str(run.get("state") or "unknown"),
        "terminal": bool(run.get("terminal", False)),
    }


def _find_plan_view(value: Any, *, depth: int = 0) -> Mapping[str, Any] | None:
    if depth > 8:
        return None
    if isinstance(value, Mapping):
        if (
            isinstance(value.get("steps"), list)
            and "planned_step_count" in value
            and "status" in value
        ):
            return value
        for item in value.values():
            if found := _find_plan_view(item, depth=depth + 1):
                return found
    elif isinstance(value, list):
        for item in value:
            if found := _find_plan_view(item, depth=depth + 1):
                return found
    return None


def _find_run_view(value: Any, *, depth: int = 0) -> Mapping[str, Any] | None:
    if depth > 8:
        return None
    if isinstance(value, Mapping):
        if value.get("protocol") == RUN_VIEW_PROTOCOL:
            return value
        run = value.get("run")
        if isinstance(run, Mapping) and run.get("protocol") == RUN_VIEW_PROTOCOL:
            return run
        for item in value.values():
            if found := _find_run_view(item, depth=depth + 1):
                return found
    elif isinstance(value, list):
        for item in value:
            if found := _find_run_view(item, depth=depth + 1):
                return found
    return None
