import io
import json
from types import SimpleNamespace

import pytest

from eda_bridge_runtime import EDAContext, ResponseEnvelope
from eda_bridge_runtime.connections import (
    ConnectionRegistry,
    ConnectionSpec,
    discover_connection_origin,
)
from eda_bridge_runtime.mcp_server import MCPRuntimeServer, serve_mcp


def test_connection_registry_round_trip_and_deterministic_resolution(tmp_path):
    registry = ConnectionRegistry(tmp_path / "connections.json")
    local = ConnectionSpec(
        connection_id="ads-local",
        eda="keysight-ads",
        kind="local",
        command=("ads-agent", "runtime", "serve"),
        origin_id="origin-ads",
    )
    registry.upsert(local)
    assert registry.resolve(eda="keysight-ads") == local
    assert registry.resolve(connection_id="ads-local") == local
    assert registry.resolve(origin_id="origin-ads", eda="keysight-ads") == local
    assert registry.remove("ads-local") is True
    assert registry.list() == []


def test_connection_registry_refuses_ambiguous_eda(tmp_path):
    registry = ConnectionRegistry(tmp_path / "connections.json")
    for suffix in ("a", "b"):
        registry.upsert(
            ConnectionSpec(
                connection_id=f"ansys-{suffix}",
                eda="ansys-electronics-desktop",
                kind="local",
                command=("ansysem-agent", "runtime", "serve"),
            )
        )
    with pytest.raises(ValueError, match="2 connections"):
        registry.resolve(eda="ansys-electronics-desktop")


def test_connection_registry_resolves_same_eda_by_origin(tmp_path):
    registry = ConnectionRegistry(tmp_path / "connections.json")
    for suffix in ("a", "b"):
        registry.upsert(
            ConnectionSpec(
                connection_id=f"ansys-{suffix}",
                eda="ansys-electronics-desktop",
                kind="local",
                command=("ansysem-agent", "runtime", "serve"),
                origin_id=f"origin-{suffix}",
            )
        )
    assert (
        registry.resolve(eda="ansys-electronics-desktop", origin_id="origin-b").connection_id
        == "ansys-b"
    )


class FakeTransport:
    def __init__(self):
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        return ResponseEnvelope(
            request_id=request.request_id,
            run_id=request.run_id,
            status="passed",
            result={"observed": True},
        )

    def close(self):
        return None


class OriginTransport(FakeTransport):
    def request(self, request):
        self.requests.append(request)
        return ResponseEnvelope(
            request_id=request.request_id,
            run_id=request.run_id,
            status="passed",
            result={"data": {"capabilities": {"origin_id": "origin-remote"}}},
        )


def test_connection_setup_can_bind_origin_without_user_metadata():
    spec = ConnectionSpec(
        connection_id="ads-remote",
        eda="keysight-ads",
        kind="ssh",
        host="eda-host",
        command=("ads-agent", "runtime", "serve"),
    )
    transport = OriginTransport()
    bound = discover_connection_origin(spec, transport=transport)
    assert bound.origin_id == "origin-remote"
    assert transport.requests[0].operation == "runtime.capabilities"


class FakeRegistry:
    def __init__(self):
        self.transport = FakeTransport()
        self.spec = SimpleNamespace(
            connection_id="ansys-one",
            eda="ansys-electronics-desktop",
            kind="ssh",
            open=lambda: self.transport,
        )

    def list(self):
        return [self.spec]

    def resolve(self, *, connection_id=None, eda=None, origin_id=None):
        assert connection_id in {None, "ansys-one"}
        assert eda in {None, "ansys-electronics-desktop"}
        assert origin_id in {None, "origin-ansys"}
        return self.spec


class FailingTransport(FakeTransport):
    def __init__(self):
        super().__init__()
        self.closed = False

    def request(self, request):
        self.requests.append(request)
        raise ConnectionError("connection dropped")

    def close(self):
        self.closed = True


class DurableTransport(FakeTransport):
    def request(self, request):
        self.requests.append(request)
        return ResponseEnvelope(
            request_id=request.request_id,
            run_id=request.run_id,
            status="passed",
            result={
                "job": {
                    "job_id": "job-one",
                    "request_id": "original-request",
                    "run_id": "original-run",
                    "state": "running",
                }
            },
        )


def _rpc(request_id, method, params=None):
    value = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        value["params"] = params
    return value


def test_mcp_supports_legacy_and_modern_discovery():
    server = MCPRuntimeServer(FakeRegistry())
    legacy = server.handle(
        _rpc(
            1,
            "initialize",
            {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {}},
        )
    )
    assert legacy["result"]["protocolVersion"] == "2025-11-25"
    modern = server.handle(_rpc(2, "server/discover"))
    assert modern["result"]["supportedVersions"] == ["2026-07-28"]
    assert modern["result"]["_meta"]["io.modelcontextprotocol/serverInfo"]["name"]
    tools = server.handle(_rpc(3, "tools/list"))["result"]["tools"]
    assert [item["name"] for item in tools] == [
        "eda.context.resolve",
        "eda.connections.list",
        "eda.capabilities",
        "eda.submit",
        "eda.job.status",
        "eda.job.events",
    ]


def test_mcp_context_resolution_and_submit_preserve_purpose():
    registry = FakeRegistry()
    server = MCPRuntimeServer(registry)
    token = EDAContext(
        eda="ansys-electronics-desktop",
        target_kind="design",
        locator={"context_id": "ctx1", "connection_id": "ansys-one"},
        origin={"origin_id": "origin-ansys"},
    ).encode()
    resolved = server.handle(
        _rpc(1, "tools/call", {"name": "eda.context.resolve", "arguments": {"context": token}})
    )
    assert resolved["result"]["structuredContent"]["connection"]["connection_id"] == "ansys-one"
    response = server.handle(
        _rpc(
            2,
            "tools/call",
            {
                "name": "eda.submit",
                "arguments": {
                    "purpose": "Inspect the selected design",
                    "operation": "capabilities",
                    "payload": {"mutating": False},
                    "target": {"profile": "de"},
                    "context": token,
                },
            },
        )
    )
    assert response["result"]["isError"] is False
    assert registry.transport.requests[0].purpose == "Inspect the selected design"
    assert registry.transport.requests[0].target["context_id"] == "ctx1"
    assert registry.transport.requests[0].target["profile"] == "de"
    assert registry.transport.requests[0].target["connection_id"] == "ansys-one"
    assert registry.transport.requests[0].actor.harness.value == "mcp"


def test_mcp_initialize_supplies_client_identity_and_compact_run_projection():
    registry = FakeRegistry()
    registry.transport = DurableTransport()
    server = MCPRuntimeServer(registry)
    server.handle(
        _rpc(
            1,
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "codex-desktop", "version": "1"},
            },
        )
    )
    response = server.handle(
        _rpc(
            2,
            "tools/call",
            {
                "name": "eda.job.status",
                "arguments": {
                    "purpose": "Observe durable operation",
                    "job_id": "job-one",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    request = registry.transport.requests[0]
    value = response["result"]["structuredContent"]
    assert request.actor.client.value == "codex-desktop"
    assert request.actor.client.provenance == "observed"
    assert request.actor.client_version.value == "1"
    assert request.actor.client_version.provenance == "observed"
    assert value["run"]["state"] == "running"
    assert value["run"]["run_id"] == "original-run"
    assert value["run"]["job_id"] == "job-one"
    assert response["result"]["content"][0]["text"].endswith("ansys-one | original-run | job-one")


def test_mcp_capability_discovery_is_read_only_and_summary_is_bounded():
    registry = FakeRegistry()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.capabilities",
                "arguments": {
                    "purpose": "Discover available operations",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    request = registry.transport.requests[0]
    assert request.operation == "runtime.capabilities"
    assert request.payload == {"mutating": False}
    text = response["result"]["content"][0]["text"]
    assert text == f"EDA Runtime result: passed | ansys-one | {request.run_id}"
    assert json.dumps(response["result"]["structuredContent"], sort_keys=True) not in text


def test_mcp_stdio_bad_frame_does_not_kill_server():
    source = io.StringIO("bad\n" + json.dumps(_rpc(1, "tools/list")) + "\n")
    destination = io.StringIO()
    serve_mcp(source, destination, registry=FakeRegistry())
    responses = [json.loads(line) for line in destination.getvalue().splitlines()]
    assert responses[0]["error"]["code"] == -32700
    assert len(responses[1]["result"]["tools"]) == 6


def test_mcp_discards_failed_connection_without_replaying_request():
    registry = FakeRegistry()
    transport = FailingTransport()
    registry.transport = transport
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.submit",
                "arguments": {
                    "purpose": "Observe the selected design",
                    "operation": "status",
                    "payload": {"mutating": False},
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    assert response["result"]["isError"] is True
    assert len(transport.requests) == 1
    assert transport.closed is True
    assert server._transports == {}
