"""Small dependency-free MCP stdio facade over registered Runtime connections."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, TextIO

from ._version import __version__
from .agent_audit import AGENT_AUDIT_PROTOCOL
from .connections import ConnectionRegistry
from .context import EDAContext
from .ledger import ExecutionLedger
from .protocol import ActorIdentity, RequestEnvelope, new_id, project_run

MODERN_PROTOCOL = "2026-07-28"
LEGACY_PROTOCOL = "2025-11-25"
SERVER_INFO = {"name": "eda-bridge-runtime", "version": __version__}
SERVER_META = {"io.modelcontextprotocol/serverInfo": SERVER_INFO}


def _object_schema(properties: dict[str, Any], required: list[str] = ()) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


_RESULT_VIEW_SCHEMA = _object_schema(
    {
        "fields": {
            "type": "array",
            "minItems": 1,
            "maxItems": 16,
            "items": _object_schema(
                {
                    "name": {"type": "string", "minLength": 1, "maxLength": 64},
                    "pointer": {"type": "string", "maxLength": 256},
                    "mode": {"type": "string", "enum": ["value", "count", "exists"]},
                },
                ["name", "pointer"],
            ),
        }
    },
    ["fields"],
)
_RESULT_VIEW_SCHEMA["description"] = (
    "Advanced response-size optimization. Omit this field unless every JSON Pointer was "
    "verified from an earlier successful full response for the same operation and version. "
    "Pointers are relative to Bridge response.result, not names desired in the Agent's final "
    "answer; guessed value/count pointers fail the otherwise successful read."
)
_RESULT_VIEW_SCHEMA["properties"]["fields"]["items"]["properties"]["pointer"]["description"] = (
    "Verified RFC 6901 path inside Bridge response.result; never infer it from final-answer keys."
)

_WAIT_SCHEMA = _object_schema(
    {
        "timeout_ms": {"type": "integer", "minimum": 1000, "maximum": 90000},
        "poll_interval_ms": {"type": "integer", "minimum": 100, "maximum": 5000},
    }
)


_MISSING = object()


def _json_pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ValueError("result_view pointer must be an RFC 6901 JSON Pointer")
    selected = value
    for raw_part in pointer[1:].split("/"):
        for index, character in enumerate(raw_part):
            if character == "~" and (index + 1 == len(raw_part) or raw_part[index + 1] not in "01"):
                raise ValueError("result_view pointer contains an invalid JSON Pointer escape")
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(selected, dict):
            selected = selected.get(part, _MISSING)
        elif isinstance(selected, list) and part.isdigit():
            index = int(part)
            selected = selected[index] if index < len(selected) else _MISSING
        else:
            selected = _MISSING
        if selected is _MISSING:
            break
    return selected


def _result_view_fields(result_view: Any) -> list[tuple[str, str, str]]:
    if not isinstance(result_view, dict) or set(result_view) != {"fields"}:
        raise ValueError("result_view must contain only fields")
    fields = result_view.get("fields")
    if not isinstance(fields, list) or not 1 <= len(fields) <= 16:
        raise ValueError("result_view fields must contain 1..16 selectors")
    names: set[str] = set()
    normalized: list[tuple[str, str, str]] = []
    for field in fields:
        if not isinstance(field, dict) or not {"name", "pointer"} <= set(field):
            raise ValueError("every result_view field requires name and pointer")
        if set(field) - {"name", "pointer", "mode"}:
            raise ValueError("result_view field contains unknown keys")
        if not isinstance(field["name"], str) or not isinstance(field["pointer"], str):
            raise ValueError("result_view name and pointer must be strings")
        name = field["name"].strip()
        if not name or len(name) > 64 or name in names:
            raise ValueError("result_view field names must be unique and contain 1..64 characters")
        names.add(name)
        pointer = field["pointer"]
        if len(pointer) > 256:
            raise ValueError("result_view pointer must not exceed 256 characters")
        mode_value = field.get("mode", "value")
        if not isinstance(mode_value, str):
            raise ValueError("result_view mode must be a string")
        mode = mode_value
        if mode not in {"value", "count", "exists"}:
            raise ValueError("result_view mode must be value, count, or exists")
        _json_pointer({}, pointer)
        normalized.append((name, pointer, mode))
    return normalized


def _project_response_result(response: dict[str, Any], result_view: Any) -> dict[str, Any]:
    fields = _result_view_fields(result_view)
    selected: dict[str, Any] = {}
    result = response.get("result")
    for name, pointer, mode in fields:
        value = _json_pointer(result, pointer)
        if mode == "exists":
            selected[name] = value is not _MISSING
        elif value is _MISSING:
            raise ValueError(f"result_view pointer does not exist: {pointer}")
        elif mode == "count":
            if not isinstance(value, dict | list | str):
                raise ValueError(
                    f"result_view count requires an object, array, or string: {pointer}"
                )
            selected[name] = len(value)
        else:
            selected[name] = value
    return {
        **{key: value for key, value in response.items() if key != "result"},
        "result": selected,
        "result_view": {"projected": True, "field_count": len(selected)},
    }


_CONNECTION_ID_SCHEMA = {
    "type": "string",
    "description": (
        "Exact registered connection identifier, for example ads-display4. "
        "When the request names a connection, put it here rather than in eda."
    ),
}
_EDA_SELECTOR_SCHEMA = {
    "type": "string",
    "description": (
        "EDA vendor type, for example keysight-ads or ansys-electronics-desktop; "
        "use only when exactly one registered connection has that type."
    ),
}


TOOLS = [
    {
        "name": "eda.context.resolve",
        "title": "Resolve EDA Context",
        "description": (
            "Validate a secret-free EDA_CONTEXT token and deterministically select its registered "
            "local or SSH connection. Does not contact the EDA."
        ),
        "inputSchema": _object_schema(
            {
                "purpose": {"type": "string", "minLength": 3, "maxLength": 240},
                "context": {"type": "string"},
                "connection_id": _CONNECTION_ID_SCHEMA,
            },
            ["purpose", "context"],
        ),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "eda.connections.list",
        "title": "List EDA Connections",
        "description": "List configured connection identifiers and EDA types without opening them.",
        "inputSchema": _object_schema(
            {"purpose": {"type": "string", "minLength": 3, "maxLength": 240}},
            ["purpose"],
        ),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "eda.connection.reset",
        "title": "Reset One EDA Transport",
        "description": (
            "Close one Runtime-owned local or SSH transport so the next explicit call starts a "
            "fresh Bridge process. Does not close or modify the EDA application."
        ),
        "inputSchema": _object_schema(
            {
                "purpose": {"type": "string", "minLength": 3, "maxLength": 240},
                "connection_id": _CONNECTION_ID_SCHEMA,
            },
            ["purpose", "connection_id"],
        ),
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "eda.capabilities",
        "title": "Discover EDA Capabilities",
        "description": (
            "Read typed operations when the selected Skill and Context do not already establish "
            "the operation contract, or when a capability digest is stale. Does not mutate the EDA."
        ),
        "inputSchema": _object_schema(
            {
                "purpose": {"type": "string", "minLength": 3, "maxLength": 240},
                "target": {"type": "object"},
                "context": {"type": "string"},
                "connection_id": _CONNECTION_ID_SCHEMA,
                "eda": _EDA_SELECTOR_SCHEMA,
            },
            ["purpose"],
        ),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "eda.read",
        "title": "Run Typed Read-Only EDA Operation",
        "description": (
            "Run one operation that the selected Bridge has advertised as non-mutating. "
            "Runtime discovers missing safety metadata mechanically; unknown or mutating "
            "operations are rejected before execution. Add wait to return a durable operation's "
            "terminal result in this same tool call."
        ),
        "inputSchema": _object_schema(
            {
                "purpose": {"type": "string", "minLength": 3, "maxLength": 240},
                "operation": {"type": "string"},
                "payload": {"type": "object"},
                "target": {"type": "object"},
                "context": {"type": "string"},
                "connection_id": _CONNECTION_ID_SCHEMA,
                "eda": _EDA_SELECTOR_SCHEMA,
                "result_view": _RESULT_VIEW_SCHEMA,
                "wait": _WAIT_SCHEMA,
            },
            ["purpose", "operation", "payload"],
        ),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "eda.submit",
        "title": "Submit Typed EDA Operation",
        "description": (
            "Submit one typed operation through a registered Runtime connection. When Context and "
            "the selected Skill establish the operation, call this directly without separate "
            "resolve "
            "or capability probes. A concise purpose is mandatory; mutations require a stable "
            "idempotency_key and are never blindly replayed. Add wait to return a durable "
            "operation's terminal result in this same tool call."
        ),
        "inputSchema": _object_schema(
            {
                "purpose": {"type": "string", "minLength": 3, "maxLength": 240},
                "operation": {"type": "string"},
                "payload": {"type": "object"},
                "target": {"type": "object"},
                "context": {"type": "string"},
                "connection_id": _CONNECTION_ID_SCHEMA,
                "eda": _EDA_SELECTOR_SCHEMA,
                "expected_effect": {"type": "string"},
                "idempotency_key": {"type": "string"},
                "wait": _WAIT_SCHEMA,
            },
            ["purpose", "operation", "payload"],
        ),
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": False},
    },
    {
        "name": "eda.run_plan",
        "title": "Run Validated EDA Operation Plan",
        "description": (
            "Execute 2..16 already-decided typed Bridge operations in order through one Runtime "
            "connection. Runtime discovers and validates every operation before the first "
            "mutation, preserves a purpose and idempotency boundary per step, waits for durable "
            "jobs when requested, and stops at the first failure. This executes a plan; it does "
            "not invent or choose EDA work."
        ),
        "inputSchema": _object_schema(
            {
                "purpose": {"type": "string", "minLength": 3, "maxLength": 240},
                "steps": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 16,
                    "items": _object_schema(
                        {
                            "step_id": {"type": "string", "minLength": 1, "maxLength": 64},
                            "purpose": {"type": "string", "minLength": 3, "maxLength": 240},
                            "operation": {"type": "string"},
                            "payload": {
                                "type": "object",
                                "description": (
                                    "Vendor Bridge operation payload only. Do not place Runtime "
                                    "step controls such as wait, idempotency_key, purpose, or "
                                    "result_view inside payload."
                                ),
                            },
                            "target": {"type": "object"},
                            "expected_effect": {"type": "string"},
                            "idempotency_key": {"type": "string"},
                            "wait": {
                                **_object_schema(
                                    {
                                        "timeout_ms": {
                                            "type": "integer",
                                            "minimum": 1000,
                                            "maximum": 90000,
                                        },
                                        "poll_interval_ms": {
                                            "type": "integer",
                                            "minimum": 100,
                                            "maximum": 5000,
                                        },
                                    }
                                ),
                                "description": (
                                    "Runtime durable-job wait policy for this plan step. This is "
                                    "a sibling of payload and must never be nested inside payload."
                                ),
                            },
                            "result_view": _RESULT_VIEW_SCHEMA,
                        },
                        ["step_id", "purpose", "operation", "payload"],
                    ),
                },
                "target": {"type": "object"},
                "context": {"type": "string"},
                "connection_id": _CONNECTION_ID_SCHEMA,
                "eda": _EDA_SELECTOR_SCHEMA,
            },
            ["purpose", "steps"],
        ),
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": False},
    },
    {
        "name": "eda.job.status",
        "title": "Get Durable EDA Job Status",
        "description": (
            "Read one durable job after reconnecting; never restarts or replays the job."
        ),
        "inputSchema": _object_schema(
            {
                "purpose": {"type": "string", "minLength": 3, "maxLength": 240},
                "job_id": {"type": "string"},
                "connection_id": _CONNECTION_ID_SCHEMA,
                "eda": _EDA_SELECTOR_SCHEMA,
            },
            ["purpose", "job_id"],
        ),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "eda.job.wait",
        "title": "Wait for Durable EDA Job",
        "description": (
            "Wait for one existing durable job to become terminal without replaying it or "
            "spending one Agent turn per status poll. Returns the latest state on timeout."
        ),
        "inputSchema": _object_schema(
            {
                "purpose": {"type": "string", "minLength": 3, "maxLength": 240},
                "job_id": {"type": "string"},
                "connection_id": _CONNECTION_ID_SCHEMA,
                "eda": _EDA_SELECTOR_SCHEMA,
                "result_view": _RESULT_VIEW_SCHEMA,
                "timeout_ms": {"type": "integer", "minimum": 1000, "maximum": 90000},
                "poll_interval_ms": {"type": "integer", "minimum": 100, "maximum": 5000},
            },
            ["purpose", "job_id"],
        ),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "eda.job.events",
        "title": "Read Durable EDA Job Events",
        "description": "Read incremental durable-job events after a cursor without replaying work.",
        "inputSchema": _object_schema(
            {
                "purpose": {"type": "string", "minLength": 3, "maxLength": 240},
                "job_id": {"type": "string"},
                "after_cursor": {"type": "integer", "minimum": 0},
                "connection_id": _CONNECTION_ID_SCHEMA,
                "eda": _EDA_SELECTOR_SCHEMA,
            },
            ["purpose", "job_id"],
        ),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
]


class MCPRuntimeServer:
    def __init__(
        self,
        registry: ConnectionRegistry | None = None,
        *,
        audit_database: str | Path | None = None,
    ):
        self.registry = registry or ConnectionRegistry()
        self._transports: dict[str, Any] = {}
        self._client = "mcp-client"
        self._client_version = "unknown"
        # One server instance belongs to one MCP client lifecycle.  Preserve a
        # cheap, non-identifying correlation key even when the client cannot
        # declare its own Agent session identifier.
        self._mcp_session_id = new_id("mcp")
        self._audit = ExecutionLedger(audit_database) if audit_database else None
        self._operation_metadata: dict[str, dict[str, dict[str, Any]]] = {}

    def close(self) -> None:
        for transport in self._transports.values():
            transport.close()
        self._transports.clear()
        if self._audit is not None:
            self._audit.close()
            self._audit = None

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        if message.get("jsonrpc") != "2.0":
            return self._error(message.get("id"), -32600, "Invalid JSON-RPC request")
        if "id" not in message:
            return None
        method = message.get("method")
        if method == "initialize":
            client_info = message.get("params", {}).get("clientInfo") or {}
            self._client = str(client_info.get("name") or self._client)
            self._client_version = str(client_info.get("version") or self._client_version)
            requested = message.get("params", {}).get("protocolVersion")
            selected = (
                requested if requested in {LEGACY_PROTOCOL, "2025-06-18"} else LEGACY_PROTOCOL
            )
            return self._result(
                message["id"],
                {
                    "protocolVersion": selected,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": SERVER_INFO,
                    "instructions": (
                        "Use captured EDA context when available; every operation needs purpose."
                    ),
                },
                modern=False,
            )
        if method == "server/discover":
            return self._result(
                message["id"],
                {
                    "supportedVersions": [MODERN_PROTOCOL],
                    "capabilities": {"tools": {"listChanged": False}},
                    "instructions": (
                        "Use captured EDA context when available; every operation needs purpose."
                    ),
                    "ttlMs": 60_000,
                    "cacheScope": "private",
                },
                modern=True,
            )
        if method == "ping":
            return self._result(message["id"], {}, modern=self._modern(message))
        if method == "tools/list":
            return self._result(message["id"], {"tools": TOOLS}, modern=self._modern(message))
        if method != "tools/call":
            return self._error(message["id"], -32601, f"Method not found: {method}")
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in {item["name"] for item in TOOLS} or not isinstance(arguments, dict):
            return self._error(message["id"], -32602, f"Unknown or malformed tool: {name}")
        audit = self._audit_start(str(name), arguments, message)
        started = time.monotonic()
        try:
            value = self._call(str(name), arguments, message)
            error_code = (
                str((value.get("error") or {}).get("code") or "")
                if isinstance(value.get("error"), dict)
                else ""
            )
            result = self._tool_result(
                value,
                is_error=value.get("status") == "interrupted" or error_code == "wait_interrupted",
            )
        except Exception as exc:
            value = {"status": "error", "error": {"code": type(exc).__name__, "message": str(exc)}}
            result = self._tool_result(
                value,
                is_error=True,
            )
        self._audit_finish(audit, value, round((time.monotonic() - started) * 1000, 3))
        return self._result(message["id"], result, modern=self._modern(message))

    def _call(
        self, name: str, arguments: dict[str, Any], message: dict[str, Any]
    ) -> dict[str, Any]:
        purpose = str(arguments.get("purpose") or "").strip()
        if len(purpose) < 3 or len(purpose) > 240:
            raise ValueError("purpose must contain 3..240 non-whitespace characters")
        if name == "eda.connections.list":
            return {
                "status": "ready",
                "connections": [
                    {"connection_id": item.connection_id, "eda": item.eda, "kind": item.kind}
                    for item in self.registry.list()
                ],
            }
        if name == "eda.connection.reset":
            spec = self.registry.resolve(connection_id=str(arguments["connection_id"]))
            transport = self._transports.pop(spec.connection_id, None)
            self._operation_metadata.pop(spec.connection_id, None)
            if transport is not None:
                transport.close()
            return {
                "status": "reset" if transport is not None else "idle",
                "connection_id": spec.connection_id,
                "eda": spec.eda,
                "next_call": "fresh_transport",
            }
        if name == "eda.context.resolve":
            context = EDAContext.decode(str(arguments["context"]))
            hinted = context.locator.get("connection_id")
            origin_id = str(context.origin.get("origin_id") or "") or None
            spec = self.registry.resolve(
                connection_id=str(arguments.get("connection_id") or hinted or "") or None,
                eda=context.eda,
                origin_id=origin_id,
            )
            return {
                "status": "ready",
                "context": asdict(context),
                "connection": {
                    "connection_id": spec.connection_id,
                    "eda": spec.eda,
                    "kind": spec.kind,
                },
            }
        if name == "eda.run_plan":
            return self._run_plan(arguments, message)
        context = EDAContext.decode(str(arguments["context"])) if arguments.get("context") else None
        eda = str(arguments.get("eda") or (context.eda if context else "")) or None
        hinted = context.locator.get("connection_id") if context else None
        origin_id = str(context.origin.get("origin_id") or "") or None if context else None
        selected_connection = str(arguments.get("connection_id") or hinted or "") or None
        # An exact connection id is the deterministic selector. A redundant Agent-guessed EDA
        # label must not veto it; Context identity remains strict because it is captured evidence.
        selected_eda = context.eda if context else (None if selected_connection else eda)
        spec = self.registry.resolve(
            connection_id=selected_connection,
            eda=selected_eda,
            origin_id=origin_id,
        )
        preflight_transport_ms = 0.0
        if name in {"eda.read", "eda.submit", "eda.capabilities"}:
            supplied_target = arguments.get("target") or {}
            if not isinstance(supplied_target, dict):
                raise ValueError("target must be an object")
            supplied_eda = supplied_target.get("eda")
            if supplied_eda and supplied_eda != spec.eda:
                raise ValueError("target EDA does not match the selected connection")
            target: dict[str, Any] = {
                **supplied_target,
                "eda": spec.eda,
                "connection_id": spec.connection_id,
            }
            if context:
                target["context"] = arguments["context"]
                for key, value in context.locator.items():
                    if key != "connection_id":
                        target.setdefault(key, value)
            if name == "eda.capabilities":
                operation = "runtime.capabilities"
                payload = {"mutating": False}
            else:
                operation = str(arguments["operation"])
                payload = dict(arguments["payload"])
                metadata = self._operation_metadata.get(spec.connection_id, {}).get(operation)
                if name == "eda.read":
                    if metadata is None:
                        preflight = self._call(
                            "eda.capabilities",
                            {
                                "purpose": (f"Verify read-only metadata for operation {operation}")[
                                    :240
                                ],
                                "connection_id": spec.connection_id,
                                "target": supplied_target,
                            },
                            message,
                        )
                        preflight_transport_ms = float(preflight.get("client_transport_ms") or 0)
                        metadata = self._operation_metadata.get(spec.connection_id, {}).get(
                            operation
                        )
                    if metadata is None:
                        raise ValueError(f"operation {operation!r} is not advertised by the Bridge")
                    if bool(metadata.get("mutates", True)):
                        raise PermissionError(
                            f"operation {operation!r} is not advertised as read-only"
                        )
                    if payload.get("mutating") not in {None, False}:
                        raise ValueError("eda.read payload cannot declare a mutation")
                    payload["mutating"] = False
                elif "mutating" not in payload and metadata is not None:
                    payload["mutating"] = bool(metadata.get("mutates", True))
        else:
            operation = "runtime.job_events" if name == "eda.job.events" else "runtime.job_status"
            payload = {"mutating": False, "job_id": str(arguments["job_id"])}
            if name == "eda.job.events":
                payload["after_cursor"] = int(arguments.get("after_cursor", 0))
            target = {"eda": spec.eda}
        actor = self._actor(message)
        request = RequestEnvelope(
            purpose=str(arguments["purpose"]),
            target=target,
            operation=operation,
            payload=payload,
            expected_effect=arguments.get("expected_effect"),
            idempotency_key=arguments.get("idempotency_key"),
            actor=actor,
        )
        transport = self._transports.get(spec.connection_id)
        if transport is None:
            transport = spec.open()
            self._transports[spec.connection_id] = transport
        started = time.monotonic()
        try:
            response = transport.request(request)
            response_value = response.to_dict()
            inline_wait = arguments.get("wait") if name in {"eda.read", "eda.submit"} else None
            if name == "eda.job.wait" or inline_wait is not None:
                wait_options = inline_wait if isinstance(inline_wait, dict) else arguments
                timeout_ms = int(wait_options.get("timeout_ms", 60_000))
                interval_ms = int(wait_options.get("poll_interval_ms", 1_000))
                deadline = time.monotonic() + timeout_ms / 1000
                while not project_run(response_value).get("terminal", False):
                    job_id = project_run(response_value).get("job_id")
                    if not job_id:
                        raise ValueError("non-terminal operation returned no durable job_id")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    time.sleep(min(interval_ms / 1000, remaining))
                    request = RequestEnvelope(
                        purpose=(f"Wait for durable result: {arguments['purpose']}")[:240],
                        target={"eda": spec.eda},
                        operation="runtime.job_status",
                        payload={"mutating": False, "job_id": str(job_id)},
                        actor=actor,
                    )
                    response = transport.request(request)
                    response_value = response.to_dict()
        except Exception:
            # The failed request is never replayed. Discard only the broken
            # connection so a later, explicit call can establish a new one.
            self._transports.pop(spec.connection_id, None)
            transport.close()
            raise
        if name == "eda.capabilities":
            self._remember_capabilities(spec.connection_id, response_value)
        projected = project_run(response_value)
        client_response = response_value
        if (
            name in {"eda.read", "eda.job.wait"}
            and arguments.get("result_view") is not None
            and response_value.get("status") == "passed"
        ):
            client_response = _project_response_result(response_value, arguments["result_view"])
        return {
            "connection_id": spec.connection_id,
            "client_transport_ms": round(
                preflight_transport_ms + (time.monotonic() - started) * 1000, 3
            ),
            "run": projected,
            "response": client_response,
            **(
                {"wait_timed_out": True}
                if (name == "eda.job.wait" or inline_wait is not None)
                and not projected.get("terminal", False)
                else {}
            ),
        }

    def _run_plan(self, arguments: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
        raw_steps = arguments.get("steps")
        if not isinstance(raw_steps, list) or not 2 <= len(raw_steps) <= 16:
            raise ValueError("steps must contain 2..16 operation steps")
        if not all(isinstance(step, dict) for step in raw_steps):
            raise ValueError("every plan step must be an object")
        if len(json.dumps(raw_steps, ensure_ascii=False, separators=(",", ":"))) > 262_144:
            raise ValueError("serialized plan steps must not exceed 256 KiB")
        step_ids = [str(step.get("step_id") or "").strip() for step in raw_steps]
        if any(not step_id or len(step_id) > 64 for step_id in step_ids):
            raise ValueError("every step_id must contain 1..64 characters")
        if len(set(step_ids)) != len(step_ids):
            raise ValueError("step_id values must be unique")

        shared_target = arguments.get("target") or {}
        if not isinstance(shared_target, dict):
            raise ValueError("plan target must be an object")
        effective_targets: list[dict[str, Any]] = []
        for step in raw_steps:
            step_target = step.get("target") or {}
            if not isinstance(step_target, dict):
                raise ValueError(f"step {step.get('step_id')!r} target must be an object")
            effective_targets.append({**shared_target, **step_target})

        selector = {
            key: arguments[key]
            for key in ("context", "connection_id", "eda")
            if arguments.get(key) is not None
        }
        metadata_by_target: dict[str, dict[str, dict[str, Any]]] = {}
        preflight_transport_ms = 0.0
        connection_id = ""
        for target in effective_targets:
            target_key = json.dumps(target, sort_keys=True, separators=(",", ":"))
            if target_key in metadata_by_target:
                continue
            preflight = self._call(
                "eda.capabilities",
                {
                    **selector,
                    "target": target,
                    "purpose": (
                        "Validate registered operations before executing the operation plan"
                    ),
                },
                message,
            )
            observed_connection = str(preflight["connection_id"])
            if connection_id and observed_connection != connection_id:
                raise ValueError("all plan steps must resolve to one Runtime connection")
            connection_id = observed_connection
            preflight_transport_ms += float(preflight.get("client_transport_ms") or 0)
            metadata_by_target[target_key] = {
                key: dict(value)
                for key, value in self._operation_metadata.get(connection_id, {}).items()
            }
        validated: list[tuple[dict[str, Any], bool, str, dict[str, Any]]] = []
        allowed_step_keys = {
            "step_id",
            "purpose",
            "operation",
            "payload",
            "target",
            "expected_effect",
            "idempotency_key",
            "wait",
            "result_view",
        }
        mutation_keys: set[str] = set()
        for step, effective_target in zip(raw_steps, effective_targets, strict=True):
            unknown_keys = set(step) - allowed_step_keys
            if unknown_keys:
                raise ValueError(
                    f"step {step.get('step_id')!r} contains unknown fields: "
                    + ", ".join(sorted(unknown_keys))
                )
            purpose = str(step.get("purpose") or "").strip()
            if not 3 <= len(purpose) <= 240:
                raise ValueError(
                    f"step {step.get('step_id')!r} purpose must contain 3..240 characters"
                )
            operation = str(step.get("operation") or "").strip()
            if operation != step.get("operation"):
                raise ValueError(
                    f"step {step.get('step_id')!r} operation must not contain "
                    "surrounding whitespace"
                )
            target_key = json.dumps(effective_target, sort_keys=True, separators=(",", ":"))
            metadata = metadata_by_target[target_key]
            if operation not in metadata:
                raise ValueError(
                    f"step {step.get('step_id')!r} uses unknown operation {operation!r}"
                )
            payload = step.get("payload")
            if not isinstance(payload, dict):
                raise ValueError(f"step {step.get('step_id')!r} payload must be an object")
            mutates = bool(metadata[operation].get("mutates", True))
            if step.get("result_view") is not None:
                _result_view_fields(step["result_view"])
                if mutates:
                    raise ValueError(
                        f"step {step.get('step_id')!r} result_view is allowed only for read steps"
                    )
            if "mutating" in payload and bool(payload["mutating"]) != mutates:
                raise ValueError(
                    f"step {step.get('step_id')!r} mutating flag contradicts capability metadata"
                )
            if mutates and not str(step.get("idempotency_key") or "").strip():
                raise ValueError(f"step {step.get('step_id')!r} mutation requires idempotency_key")
            if mutates:
                idempotency_key = str(step["idempotency_key"]).strip()
                if idempotency_key in mutation_keys:
                    raise ValueError("mutating plan steps must use unique idempotency_key values")
                mutation_keys.add(idempotency_key)
            wait = step.get("wait")
            if wait is not None and not isinstance(wait, dict):
                raise ValueError(f"step {step.get('step_id')!r} wait must be an object")
            if isinstance(wait, dict):
                unknown_wait_keys = set(wait) - {"timeout_ms", "poll_interval_ms"}
                if unknown_wait_keys:
                    raise ValueError(f"step {step.get('step_id')!r} wait contains unknown fields")
                timeout_ms = int(wait.get("timeout_ms", 60_000))
                poll_interval_ms = int(wait.get("poll_interval_ms", 1_000))
                if not 1_000 <= timeout_ms <= 90_000:
                    raise ValueError(f"step {step.get('step_id')!r} timeout_ms is out of range")
                if not 100 <= poll_interval_ms <= 5_000:
                    raise ValueError(
                        f"step {step.get('step_id')!r} poll_interval_ms is out of range"
                    )
            validated.append((step, mutates, operation, effective_target))

        results: list[dict[str, Any]] = []
        transport_ms = preflight_transport_ms
        status = "passed"
        plan_error: dict[str, Any] | None = None
        for index, (step, mutates, operation, effective_target) in enumerate(validated):
            step_arguments: dict[str, Any] = {
                "purpose": str(step["purpose"]),
                "operation": operation,
                "payload": {**step["payload"], "mutating": mutates},
                "connection_id": connection_id,
            }
            if arguments.get("context") is not None:
                step_arguments["context"] = arguments["context"]
            if effective_target:
                step_arguments["target"] = effective_target
            for key in ("expected_effect", "idempotency_key"):
                if step.get(key) is not None:
                    step_arguments[key] = step[key]
            try:
                # The plan itself is a mutation-capable, explicitly approved tool. Mutability was
                # frozen from the target-specific capability snapshots before the first step.
                value = self._call("eda.submit", step_arguments, message)
            except Exception as exc:
                status = "interrupted"
                plan_error = {"code": type(exc).__name__, "message": str(exc)}
                break
            transport_ms += float(value.get("client_transport_ms") or 0)
            run = value["run"]
            if not run.get("terminal") and step.get("wait") is not None:
                job_id = run.get("job_id")
                if not job_id:
                    results.append(
                        {
                            "step_id": str(step["step_id"]),
                            "purpose": str(step["purpose"]),
                            "operation": operation,
                            "mutates": mutates,
                            **value,
                        }
                    )
                    status = "interrupted"
                    plan_error = {
                        "code": "durable_job_id_missing",
                        "message": (
                            "non-terminal run cannot be waited because it returned no job_id"
                        ),
                    }
                    break
                wait = step.get("wait") or {}
                try:
                    value = self._call(
                        "eda.job.wait",
                        {
                            "purpose": (f"Wait for step {step['step_id']}: {step['purpose']}")[
                                :240
                            ],
                            "connection_id": connection_id,
                            "job_id": job_id,
                            "timeout_ms": int(wait.get("timeout_ms", 60_000)),
                            "poll_interval_ms": int(wait.get("poll_interval_ms", 1_000)),
                        },
                        message,
                    )
                except Exception as exc:
                    results.append(
                        {
                            "step_id": str(step["step_id"]),
                            "purpose": str(step["purpose"]),
                            "operation": operation,
                            "mutates": mutates,
                            **value,
                            "wait_error": {
                                "code": type(exc).__name__,
                                "message": str(exc),
                            },
                        }
                    )
                    status = "waiting"
                    plan_error = {
                        "code": "wait_interrupted",
                        "message": "durable job remains observable by its returned job_id",
                    }
                    break
                transport_ms += float(value.get("client_transport_ms") or 0)
                run = value["run"]
            if step.get("result_view") is not None and run.get("state") == "passed":
                try:
                    value = {
                        **value,
                        "response": _project_response_result(
                            value["response"], step["result_view"]
                        ),
                    }
                except Exception as exc:
                    results.append(
                        {
                            "step_id": str(step["step_id"]),
                            "purpose": str(step["purpose"]),
                            "operation": operation,
                            "mutates": mutates,
                            **value,
                            "result_view_error": {
                                "code": type(exc).__name__,
                                "message": str(exc),
                            },
                        }
                    )
                    status = "interrupted"
                    plan_error = {
                        "code": "result_view_failed",
                        "message": "read step completed but its result view could not be applied",
                    }
                    break
            results.append(
                {
                    "step_id": str(step["step_id"]),
                    "purpose": str(step["purpose"]),
                    "operation": operation,
                    "mutates": mutates,
                    **value,
                }
            )
            state = str(run.get("state") or "unknown")
            if run.get("terminal") and state != "passed":
                status = "failed"
                break
            if not run.get("terminal"):
                status = "waiting"
                break
            if index == len(validated) - 1:
                status = "passed"
        return {
            "status": status,
            "connection_id": connection_id,
            "step_count": len(results),
            "planned_step_count": len(validated),
            "client_transport_ms": round(transport_ms, 3),
            "steps": results,
            **({"error": plan_error} if plan_error else {}),
        }

    def _remember_capabilities(self, connection_id: str, response: dict[str, Any]) -> None:
        result = response.get("result") or {}
        data = result.get("data") if isinstance(result, dict) else {}
        capabilities = data.get("capabilities") if isinstance(data, dict) else {}
        operations = capabilities.get("operations") if isinstance(capabilities, dict) else []
        if not isinstance(operations, list):
            return
        self._operation_metadata[connection_id] = {
            str(item["id"]): dict(item)
            for item in operations
            if isinstance(item, dict) and item.get("id")
        }

    def _client_info(self, message: dict[str, Any]) -> tuple[str, str]:
        meta = (message.get("params") or {}).get("_meta") or {}
        info = meta.get("io.modelcontextprotocol/clientInfo") or {}
        return (
            str(info.get("name") or self._client),
            str(info.get("version") or self._client_version),
        )

    def _actor(self, message: dict[str, Any]) -> ActorIdentity:
        client_name, client_version = self._client_info(message)
        meta = (message.get("params") or {}).get("_meta") or {}
        raw_declared = meta.get("io.eda-runtime/actor") or {}
        allowed = {
            "agent_family",
            "agent_version",
            "model",
            "provider",
            "reasoning",
            "skill",
            "session_id",
            "turn_id",
            "tool_call_id",
            "permission_mode",
        }
        declared = (
            {
                key: str(value)[:240]
                for key, value in raw_declared.items()
                if key in allowed and value is not None and str(value).strip()
            }
            if isinstance(raw_declared, dict)
            else {}
        )
        return ActorIdentity.detect(
            declared=declared,
            observed={
                "client": client_name,
                "client_version": client_version,
                "harness": "mcp",
            },
            inferred={"session_id": self._mcp_session_id},
        )

    def _audit_start(
        self, name: str, arguments: dict[str, Any], message: dict[str, Any]
    ) -> tuple[str, str] | None:
        if self._audit is None:
            return None
        run_id = new_id("agent")
        request_id = new_id("req")
        canonical = json.dumps(
            {"tool": name, "arguments": arguments},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        action_arguments = {key: value for key, value in arguments.items() if key != "purpose"}
        action_canonical = json.dumps(
            {"tool": name, "arguments": action_arguments},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        audit_payload: dict[str, Any] = {
            "protocol": AGENT_AUDIT_PROTOCOL,
            "actor": self._actor(message).to_dict(),
            "tool": name,
            "purpose": str(arguments.get("purpose") or "unspecified EDA operation")[:240],
            "input_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "action_sha256": hashlib.sha256(action_canonical.encode("utf-8")).hexdigest(),
        }
        if name == "eda.run_plan" and isinstance(arguments.get("steps"), list):
            audit_payload["plan_steps"] = [
                {
                    "step_id": str(step.get("step_id") or "")[:64],
                    "operation": str(step.get("operation") or "")[:160],
                    "purpose": str(step.get("purpose") or "")[:240],
                }
                for step in arguments["steps"][:16]
                if isinstance(step, dict)
            ]
        self._audit.append(
            run_id=run_id,
            request_id=request_id,
            event_type="agent.tool.requested",
            source="mcp-runtime",
            payload=audit_payload,
        )
        return run_id, request_id

    def _audit_finish(
        self,
        audit: tuple[str, str] | None,
        value: dict[str, Any],
        elapsed_ms: float,
    ) -> None:
        if self._audit is None or audit is None:
            return
        run_id, request_id = audit
        run = value.get("run") if isinstance(value.get("run"), dict) else None
        execution: dict[str, Any] = {
            "linked": run is not None,
            "run_id": run.get("run_id") if run else None,
            "request_id": run.get("request_id") if run else None,
            "job_id": run.get("job_id") if run else None,
            "state": run.get("state") if run else value.get("status"),
            "terminal": bool(run.get("terminal")) if run else True,
        }
        if isinstance(value.get("steps"), list):
            execution["steps"] = [
                {
                    "step_id": str(step.get("step_id") or "")[:64],
                    "operation": str(step.get("operation") or "")[:160],
                    "run_id": (step.get("run") or {}).get("run_id"),
                    "request_id": (step.get("run") or {}).get("request_id"),
                    "job_id": (step.get("run") or {}).get("job_id"),
                    "state": (step.get("run") or {}).get("state"),
                    "terminal": bool((step.get("run") or {}).get("terminal")),
                }
                for step in value["steps"][:16]
                if isinstance(step, dict) and isinstance(step.get("run"), dict)
            ]
            execution["linked"] = bool(execution["steps"])
            execution["state"] = value.get("status")
            execution["terminal"] = value.get("status") in {"passed", "failed", "cancelled"}
        self._audit.append(
            run_id=run_id,
            request_id=request_id,
            event_type="agent.tool.completed",
            source="mcp-runtime",
            payload={
                "protocol": AGENT_AUDIT_PROTOCOL,
                "timing": {
                    "mcp_server_ms": elapsed_ms,
                    "client_transport_ms": value.get("client_transport_ms"),
                },
                "execution": execution,
            },
        )
        self._audit.finalize(run_id)

    @staticmethod
    def _modern(message: dict[str, Any]) -> bool:
        meta = (message.get("params") or {}).get("_meta") or {}
        return meta.get("io.modelcontextprotocol/protocolVersion") == MODERN_PROTOCOL

    @staticmethod
    def _tool_result(value: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
        text = MCPRuntimeServer._summary(value)
        return {
            "content": [{"type": "text", "text": text}],
            "structuredContent": value,
            "isError": is_error,
        }

    @staticmethod
    def _summary(value: dict[str, Any]) -> str:
        status = str(value.get("status") or "")
        connection_id = str(value.get("connection_id") or "")
        run = value.get("run") if isinstance(value.get("run"), dict) else {}
        response = value.get("response") if isinstance(value.get("response"), dict) else {}
        response_status = str(run.get("state") or response.get("status") or "")
        run_id = str(run.get("run_id") or response.get("run_id") or "")
        job_id = str(run.get("job_id") or "")
        identity = (status or response_status, connection_id, run_id, job_id)
        parts = [item for item in identity if item]
        if parts:
            return "EDA Runtime result: " + " | ".join(parts)
        if "connections" in value:
            return f"EDA Runtime connections: {len(value.get('connections') or [])}"
        if "context" in value:
            return "EDA Runtime context resolved"
        if "error" in value:
            error = value.get("error") or {}
            return f"EDA Runtime error: {error.get('code', 'error')}"
        return "EDA Runtime result available in structured content"

    @staticmethod
    def _result(request_id: Any, result: dict[str, Any], *, modern: bool) -> dict[str, Any]:
        if modern:
            result = {**result, "_meta": {**result.get("_meta", {}), **SERVER_META}}
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def serve_mcp(
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
    *,
    registry: ConnectionRegistry | None = None,
    audit_database: str | Path | None = None,
) -> None:
    server = MCPRuntimeServer(registry, audit_database=audit_database)
    try:
        for line in input_stream:
            try:
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError("MCP frame must be a JSON object")
                response = server.handle(message)
            except Exception as exc:
                response = MCPRuntimeServer._error(None, -32700, str(exc)[:500])
            if response is not None:
                output_stream.write(json.dumps(response, separators=(",", ":")) + "\n")
                output_stream.flush()
    finally:
        server.close()
