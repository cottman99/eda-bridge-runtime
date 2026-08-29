"""Small dependency-free MCP stdio facade over registered Runtime connections."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from typing import Any, TextIO

from ._version import __version__
from .connections import ConnectionRegistry
from .context import EDAContext
from .protocol import ActorIdentity, RequestEnvelope, project_run

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
                "context": {"type": "string"},
                "connection_id": {"type": "string"},
            },
            ["context"],
        ),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "eda.connections.list",
        "title": "List EDA Connections",
        "description": "List configured connection identifiers and EDA types without opening them.",
        "inputSchema": _object_schema({}),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
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
                "connection_id": {"type": "string"},
                "eda": {"type": "string"},
            },
            ["purpose"],
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
            "idempotency_key and are never blindly replayed."
        ),
        "inputSchema": _object_schema(
            {
                "purpose": {"type": "string", "minLength": 3, "maxLength": 240},
                "operation": {"type": "string"},
                "payload": {"type": "object"},
                "target": {"type": "object"},
                "context": {"type": "string"},
                "connection_id": {"type": "string"},
                "eda": {"type": "string"},
                "expected_effect": {"type": "string"},
                "idempotency_key": {"type": "string"},
            },
            ["purpose", "operation", "payload"],
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
                "connection_id": {"type": "string"},
                "eda": {"type": "string"},
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
                "connection_id": {"type": "string"},
                "eda": {"type": "string"},
            },
            ["purpose", "job_id"],
        ),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
]


class MCPRuntimeServer:
    def __init__(self, registry: ConnectionRegistry | None = None):
        self.registry = registry or ConnectionRegistry()
        self._transports: dict[str, Any] = {}
        self._client = "mcp-client"
        self._client_version = "unknown"

    def close(self) -> None:
        for transport in self._transports.values():
            transport.close()
        self._transports.clear()

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
        try:
            value = self._call(str(name), arguments, message)
            result = self._tool_result(value)
        except Exception as exc:
            result = self._tool_result(
                {"status": "error", "error": {"code": type(exc).__name__, "message": str(exc)}},
                is_error=True,
            )
        return self._result(message["id"], result, modern=self._modern(message))

    def _call(
        self, name: str, arguments: dict[str, Any], message: dict[str, Any]
    ) -> dict[str, Any]:
        if name == "eda.connections.list":
            return {
                "status": "ready",
                "connections": [
                    {"connection_id": item.connection_id, "eda": item.eda, "kind": item.kind}
                    for item in self.registry.list()
                ],
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
        context = EDAContext.decode(str(arguments["context"])) if arguments.get("context") else None
        eda = str(arguments.get("eda") or (context.eda if context else "")) or None
        hinted = context.locator.get("connection_id") if context else None
        origin_id = str(context.origin.get("origin_id") or "") or None if context else None
        spec = self.registry.resolve(
            connection_id=str(arguments.get("connection_id") or hinted or "") or None,
            eda=eda,
            origin_id=origin_id,
        )
        if name in {"eda.submit", "eda.capabilities"}:
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
        else:
            operation = "runtime.job_status" if name == "eda.job.status" else "runtime.job_events"
            payload = {"mutating": False, "job_id": str(arguments["job_id"])}
            if name == "eda.job.events":
                payload["after_cursor"] = int(arguments.get("after_cursor", 0))
            target = {"eda": spec.eda}
        client_name, client_version = self._client_info(message)
        actor = ActorIdentity.detect(
            observed={
                "client": client_name,
                "client_version": client_version,
                "harness": "mcp",
            }
        )
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
        except Exception:
            # The failed request is never replayed. Discard only the broken
            # connection so a later, explicit call can establish a new one.
            self._transports.pop(spec.connection_id, None)
            transport.close()
            raise
        response_value = response.to_dict()
        return {
            "connection_id": spec.connection_id,
            "client_transport_ms": round((time.monotonic() - started) * 1000, 3),
            "run": project_run(response_value),
            "response": response_value,
        }

    def _client_info(self, message: dict[str, Any]) -> tuple[str, str]:
        meta = (message.get("params") or {}).get("_meta") or {}
        info = meta.get("io.modelcontextprotocol/clientInfo") or {}
        return (
            str(info.get("name") or self._client),
            str(info.get("version") or self._client_version),
        )

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
) -> None:
    server = MCPRuntimeServer(registry)
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
