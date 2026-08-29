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
from .protocol import RUN_VIEW_PROTOCOL, ActorIdentity

AGENT_AUDIT_PROTOCOL = "eda-runtime.agent-audit/v1"
_RUNTIME_TOOL = re.compile(r"^mcp__(?P<server>.+)__(?P<tool>.+)$")
_TOOL_NAMES = {
    "eda_capabilities": "eda.capabilities",
    "eda_submit": "eda.submit",
    "eda_job_status": "eda.job.status",
    "eda_job_events": "eda.job.events",
    "eda_connections_list": "eda.connections.list",
    "eda_context_resolve": "eda.context.resolve",
    "eda.capabilities": "eda.capabilities",
    "eda.submit": "eda.submit",
    "eda.job.status": "eda.job.status",
    "eda.job.events": "eda.job.events",
    "eda.connections.list": "eda.connections.list",
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


def audit_events(database: str | Path | None = None, *, limit: int = 20) -> list[dict[str, Any]]:
    with ExecutionLedger(database or default_agent_audit_path()) as ledger:
        events = ledger.events()
    return events[-max(1, min(limit, 1000)) :]


def _audit_run_id(tool_call_id: str) -> str:
    digest = hashlib.sha256(tool_call_id.encode("utf-8")).hexdigest()[:32]
    return f"agent_{digest}"


def _fingerprint(tool_name: str, tool_input: Mapping[str, Any]) -> str:
    material = {"tool_name": tool_name, "tool_input": tool_input}
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _execution_reference(value: Any) -> dict[str, Any]:
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
