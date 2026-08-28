import io
import json
from types import SimpleNamespace

import pytest

from eda_bridge_runtime import EDAContext, ResponseEnvelope
from eda_bridge_runtime.connections import ConnectionRegistry, ConnectionSpec
from eda_bridge_runtime.mcp_server import MCPRuntimeServer, serve_mcp


def test_connection_registry_round_trip_and_deterministic_resolution(tmp_path):
    registry = ConnectionRegistry(tmp_path / "connections.json")
    local = ConnectionSpec(
        connection_id="ads-local",
        eda="keysight-ads",
        kind="local",
        command=("ads-agent", "runtime", "serve"),
    )
    registry.upsert(local)
    assert registry.resolve(eda="keysight-ads") == local
    assert registry.resolve(connection_id="ads-local") == local
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

    def resolve(self, *, connection_id=None, eda=None):
        assert connection_id in {None, "ansys-one"}
        assert eda in {None, "ansys-electronics-desktop"}
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


def test_mcp_context_resolution_and_submit_preserve_purpose():
    registry = FakeRegistry()
    server = MCPRuntimeServer(registry)
    token = EDAContext(
        eda="ansys-electronics-desktop",
        target_kind="design",
        locator={"context_id": "ctx1", "connection_id": "ansys-one"},
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
    assert registry.transport.requests[0].actor.harness.value == "mcp"


def test_mcp_stdio_bad_frame_does_not_kill_server():
    source = io.StringIO("bad\n" + json.dumps(_rpc(1, "tools/list")) + "\n")
    destination = io.StringIO()
    serve_mcp(source, destination, registry=FakeRegistry())
    responses = [json.loads(line) for line in destination.getvalue().splitlines()]
    assert responses[0]["error"]["code"] == -32700
    assert len(responses[1]["result"]["tools"]) == 5


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
