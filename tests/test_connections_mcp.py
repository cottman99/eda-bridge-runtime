import io
import json
from types import SimpleNamespace

import pytest

from eda_bridge_runtime import EDAContext, ResponseEnvelope
from eda_bridge_runtime.agent_audit import audit_events
from eda_bridge_runtime.audit_analysis import analyze_events
from eda_bridge_runtime.connections import (
    ConnectionRegistry,
    ConnectionSpec,
    discover_connection_origin,
)
from eda_bridge_runtime.mcp_server import (
    MAX_WAIT_MS,
    TOOLS,
    MCPRuntimeServer,
    _bounded_timing,
    _find_resource,
    serve_mcp,
)


def test_nested_durable_resource_and_bridge_timing_are_projected_without_release_handle():
    value = {
        "response": {
            "result": {
                "job": {
                    "result": {
                        "result": {
                            "data": {
                                "bridge": {
                                    "resource": {
                                        "resource_id": "owned-one",
                                        "kind": "aedt-desktop",
                                        "ownership": "runtime-owned",
                                        "state": "active",
                                        "release_operation": "session.release",
                                        "release_handle": "never-in-audit",
                                    }
                                },
                                "timing": {"adapter_total_ms": 14.5},
                            }
                        }
                    }
                }
            }
        }
    }
    assert _find_resource(value) == {
        "protocol": "eda-runtime.resource-view/v1",
        "resource_id": "owned-one",
        "kind": "aedt-desktop",
        "ownership": "runtime-owned",
        "state": "active",
        "release_operation": "session.release",
    }
    assert _bounded_timing(value) == {"adapter_total_ms": 14.5}


def test_run_plan_schema_separates_vendor_payload_from_runtime_wait_policy():
    plan = next(tool for tool in TOOLS if tool["name"] == "eda.run_plan")
    step = plan["inputSchema"]["properties"]["steps"]["items"]["properties"]

    assert "Vendor Bridge operation payload only" in step["payload"]["description"]
    assert "sibling of payload" in step["wait"]["description"]
    assert step["wait"]["properties"]["timeout_ms"]["maximum"] == MAX_WAIT_MS


def test_all_wait_tools_expose_the_same_bounded_long_poll_limit():
    tools = {tool["name"]: tool for tool in TOOLS}
    for name in ("eda.read", "eda.submit"):
        wait = tools[name]["inputSchema"]["properties"]["wait"]
        assert wait["properties"]["timeout_ms"]["maximum"] == MAX_WAIT_MS
    timeout = tools["eda.job.wait"]["inputSchema"]["properties"]["timeout_ms"]
    assert timeout["maximum"] == MAX_WAIT_MS


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
        self.closed = False

    def request(self, request):
        self.requests.append(request)
        return ResponseEnvelope(
            request_id=request.request_id,
            run_id=request.run_id,
            status="passed",
            result={"observed": True},
        )

    def close(self):
        self.closed = True


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


class CapabilityAwareTransport(FakeTransport):
    def request(self, request):
        self.requests.append(request)
        if request.operation == "runtime.capabilities":
            result = {
                "data": {
                    "capabilities": {
                        "operations": [
                            {"id": "project.inspect", "mutates": False},
                            {"id": "project.create", "mutates": True},
                        ]
                    }
                }
            }
        else:
            request.require_idempotency()
            result = {"observed": True}
        return ResponseEnvelope(
            request_id=request.request_id,
            run_id=request.run_id,
            status="passed",
            result=result,
        )


class ResultViewTransport(CapabilityAwareTransport):
    def request(self, request):
        if request.operation == "project.inspect":
            self.requests.append(request)
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="passed",
                result={
                    "data": {
                        "sessions": [{"name": "one"}, {"name": "two"}],
                        "active": "one",
                    }
                },
            )
        return super().request(request)


class FailedResultViewTransport(ResultViewTransport):
    def request(self, request):
        if request.operation == "project.inspect":
            self.requests.append(request)
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="failed",
                error={"code": "native_failure", "message": "Preserve this Bridge failure"},
            )
        return super().request(request)


class PlanTransport(FakeTransport):
    def request(self, request):
        self.requests.append(request)
        if request.operation == "runtime.capabilities":
            result = {
                "data": {
                    "capabilities": {
                        "operations": [
                            {"id": "project.inspect", "mutates": False},
                            {"id": "project.create", "mutates": True},
                            {"id": "image.export", "mutates": True},
                        ]
                    }
                }
            }
            status = "passed"
        elif request.operation == "project.inspect":
            result = {"observed": request.payload.get("name")}
            status = "passed"
        else:
            request.require_idempotency()
            result = {"changed": request.operation}
            status = "passed"
        return ResponseEnvelope(
            request_id=request.request_id,
            run_id=request.run_id,
            status=status,
            result=result,
        )


class FailingPlanTransport(PlanTransport):
    def request(self, request):
        if request.operation == "project.inspect":
            self.requests.append(request)
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="failed",
                error={"code": "inspection_failed", "message": "synthetic failure"},
            )
        return super().request(request)


class TargetAwarePlanTransport(PlanTransport):
    def request(self, request):
        if request.operation == "runtime.capabilities":
            self.requests.append(request)
            operations = (
                [{"id": "project.inspect", "mutates": False}]
                if request.target.get("project") == "other"
                else [
                    {"id": "project.inspect", "mutates": False},
                    {"id": "project.create", "mutates": True},
                ]
            )
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="passed",
                result={"data": {"capabilities": {"operations": operations}}},
            )
        return super().request(request)


class DurablePlanTransport(PlanTransport):
    def request(self, request):
        if request.operation == "project.create":
            self.requests.append(request)
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="accepted",
                result={
                    "job": {
                        "job_id": "plan-job",
                        "request_id": request.request_id,
                        "run_id": request.run_id,
                        "state": "running",
                    }
                },
            )
        if request.operation == "runtime.job_status":
            self.requests.append(request)
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="passed",
                result={
                    "job": {
                        "job_id": "plan-job",
                        "request_id": "original-request",
                        "run_id": "original-run",
                        "state": "passed",
                    }
                },
            )
        return super().request(request)


class NonDurableAcceptedPlanTransport(PlanTransport):
    def request(self, request):
        if request.operation == "project.create":
            self.requests.append(request)
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="accepted",
                result={"accepted_without_job": True},
            )
        return super().request(request)


class SubmitInterruptedPlanTransport(PlanTransport):
    def request(self, request):
        if request.operation == "project.create":
            self.requests.append(request)
            raise ConnectionError("synthetic disconnect during submit")
        return super().request(request)


class EventuallyTerminalTransport(FakeTransport):
    def request(self, request):
        self.requests.append(request)
        state = "passed" if len(self.requests) >= 3 else "running"
        return ResponseEnvelope(
            request_id=request.request_id,
            run_id=request.run_id,
            status="passed",
            result={
                "job": {
                    "job_id": request.payload["job_id"],
                    "request_id": "original-request",
                    "run_id": "original-run",
                    "state": state,
                }
            },
        )


class DurableReadTransport(CapabilityAwareTransport):
    def request(self, request):
        if request.operation == "project.inspect":
            self.requests.append(request)
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="accepted",
                result={
                    "job": {
                        "job_id": "read-job",
                        "request_id": request.request_id,
                        "run_id": request.run_id,
                        "state": "running",
                    }
                },
            )
        if request.operation == "project.create":
            self.requests.append(request)
            request.require_idempotency()
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="accepted",
                result={
                    "job": {
                        "job_id": "write-job",
                        "request_id": request.request_id,
                        "run_id": request.run_id,
                        "state": "running",
                    }
                },
            )
        if request.operation == "runtime.job_status":
            self.requests.append(request)
            job_id = request.payload["job_id"]
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="passed",
                result={
                    "job": {
                        "job_id": job_id,
                        "request_id": "original-request",
                        "run_id": "original-run",
                        "state": "passed",
                    },
                    "data": {
                        "bundle_complete": True,
                        "created": job_id == "write-job",
                        "objects": ["one", "two"],
                    },
                },
            )
        return super().request(request)


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
        "eda.connection.reset",
        "eda.capabilities",
        "eda.read",
        "eda.submit",
        "eda.run_plan",
        "eda.job.status",
        "eda.job.wait",
        "eda.job.events",
    ]
    read_tool = next(item for item in tools if item["name"] == "eda.read")
    result_view = read_tool["inputSchema"]["properties"]["result_view"]
    assert "Omit this field unless every JSON Pointer was verified" in result_view["description"]
    pointer = result_view["properties"]["fields"]["items"]["properties"]["pointer"]
    assert "never infer it from final-answer keys" in pointer["description"]
    target_properties = read_tool["inputSchema"]["properties"]
    assert "registered connection identifier" in target_properties["connection_id"]["description"]
    assert "vendor type" in target_properties["eda"]["description"]
    assert "rather than in eda" in target_properties["connection_id"]["description"]


def test_mcp_requires_purpose_even_for_connection_discovery():
    server = MCPRuntimeServer(FakeRegistry())
    response = server.handle(
        _rpc(1, "tools/call", {"name": "eda.connections.list", "arguments": {}})
    )
    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["error"]["code"] == "ValueError"


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
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.context.resolve",
                "arguments": {"purpose": "Resolve the selected design", "context": token},
            },
        )
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
    assert request.actor.session_id.value.startswith("mcp_")
    assert request.actor.session_id.provenance == "inferred"
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


def test_exact_connection_id_ignores_redundant_agent_eda_alias():
    registry = FakeRegistry()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.capabilities",
                "arguments": {
                    "purpose": "Use the exact registered connection",
                    "connection_id": "ansys-one",
                    "eda": "ansysem",
                },
            },
        )
    )

    assert response["result"]["isError"] is False
    assert registry.transport.requests[0].target["eda"] == "ansys-electronics-desktop"


def test_mcp_stdio_bad_frame_does_not_kill_server():
    source = io.StringIO("bad\n" + json.dumps(_rpc(1, "tools/list")) + "\n")
    destination = io.StringIO()
    serve_mcp(source, destination, registry=FakeRegistry())
    responses = [json.loads(line) for line in destination.getvalue().splitlines()]
    assert responses[0]["error"]["code"] == -32700
    assert len(responses[1]["result"]["tools"]) == 10


def test_run_plan_prevalidates_then_executes_steps_with_individual_purposes():
    registry = FakeRegistry()
    registry.transport = PlanTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Build and verify one disposable project",
                    "connection_id": "ansys-one",
                    "steps": [
                        {
                            "step_id": "create",
                            "purpose": "Create the disposable project",
                            "operation": "project.create",
                            "payload": {"name": "scratch"},
                            "idempotency_key": "plan-create-scratch",
                        },
                        {
                            "step_id": "inspect",
                            "purpose": "Inspect the saved project",
                            "operation": "project.inspect",
                            "payload": {"name": "scratch"},
                        },
                    ],
                },
            },
        )
    )

    value = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert value["status"] == "passed"
    assert value["step_count"] == value["planned_step_count"] == 2
    assert [request.operation for request in registry.transport.requests] == [
        "runtime.capabilities",
        "project.create",
        "project.inspect",
    ]
    assert [request.purpose for request in registry.transport.requests[1:]] == [
        "Create the disposable project",
        "Inspect the saved project",
    ]
    assert registry.transport.requests[1].payload["mutating"] is True
    assert registry.transport.requests[2].payload["mutating"] is False


def test_run_plan_projects_each_read_step_without_returning_full_results():
    registry = FakeRegistry()
    registry.transport = PlanTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Inspect two targets with bounded results",
                    "connection_id": "ansys-one",
                    "steps": [
                        {
                            "step_id": "first",
                            "purpose": "Inspect the first target",
                            "operation": "project.inspect",
                            "payload": {"name": "first-full-value"},
                            "result_view": {"fields": [{"name": "name", "pointer": "/observed"}]},
                        },
                        {
                            "step_id": "second",
                            "purpose": "Inspect the second target",
                            "operation": "project.inspect",
                            "payload": {"name": "second-full-value"},
                            "result_view": {"fields": [{"name": "name", "pointer": "/observed"}]},
                        },
                    ],
                },
            },
        )
    )

    value = response["result"]["structuredContent"]
    assert value["status"] == "passed"
    assert [step["response"]["result"] for step in value["steps"]] == [
        {"name": "first-full-value"},
        {"name": "second-full-value"},
    ]
    assert all(step["response"]["result_view"]["projected"] for step in value["steps"])


def test_run_plan_rejects_a_result_view_on_mutation_before_first_change():
    registry = FakeRegistry()
    registry.transport = PlanTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Reject result projection on a mutation",
                    "connection_id": "ansys-one",
                    "steps": [
                        {
                            "step_id": "create",
                            "purpose": "Create the project",
                            "operation": "project.create",
                            "payload": {},
                            "idempotency_key": "view-create",
                            "result_view": {"fields": [{"name": "changed", "pointer": "/changed"}]},
                        },
                        {
                            "step_id": "inspect",
                            "purpose": "Inspect the project",
                            "operation": "project.inspect",
                            "payload": {},
                        },
                    ],
                },
            },
        )
    )

    assert response["result"]["isError"] is True
    assert (
        "allowed only for read steps" in response["result"]["structuredContent"]["error"]["message"]
    )
    assert [request.operation for request in registry.transport.requests] == [
        "runtime.capabilities"
    ]


def test_run_plan_rejects_all_invalid_steps_before_first_mutation():
    registry = FakeRegistry()
    registry.transport = PlanTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Reject an invalid operation plan",
                    "connection_id": "ansys-one",
                    "steps": [
                        {
                            "step_id": "create",
                            "purpose": "Create the disposable project",
                            "operation": "project.create",
                            "payload": {},
                            "idempotency_key": "plan-create-scratch",
                        },
                        {
                            "step_id": "unknown",
                            "purpose": "Attempt an unavailable operation",
                            "operation": "raw.python",
                            "payload": {},
                        },
                    ],
                },
            },
        )
    )

    assert response["result"]["isError"] is True
    assert "unknown operation" in response["result"]["structuredContent"]["error"]["message"]
    assert [request.operation for request in registry.transport.requests] == [
        "runtime.capabilities"
    ]


def test_run_plan_preflights_every_effective_target_before_first_mutation():
    registry = FakeRegistry()
    registry.transport = TargetAwarePlanTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Reject a target-specific unsupported operation",
                    "connection_id": "ansys-one",
                    "target": {"project": "primary"},
                    "steps": [
                        {
                            "step_id": "create-primary",
                            "purpose": "Create the primary project",
                            "operation": "project.create",
                            "payload": {},
                            "idempotency_key": "create-primary",
                        },
                        {
                            "step_id": "create-other",
                            "purpose": "Create the other project",
                            "operation": "project.create",
                            "payload": {},
                            "target": {"project": "other"},
                            "idempotency_key": "create-other",
                        },
                    ],
                },
            },
        )
    )

    assert response["result"]["isError"] is True
    assert [request.operation for request in registry.transport.requests] == [
        "runtime.capabilities",
        "runtime.capabilities",
    ]


def test_run_plan_rejects_duplicate_mutation_keys_before_first_mutation():
    registry = FakeRegistry()
    registry.transport = PlanTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Reject duplicate mutation identities",
                    "connection_id": "ansys-one",
                    "steps": [
                        {
                            "step_id": "create",
                            "purpose": "Create the disposable project",
                            "operation": "project.create",
                            "payload": {},
                            "idempotency_key": "duplicate-key",
                        },
                        {
                            "step_id": "export",
                            "purpose": "Export project evidence",
                            "operation": "image.export",
                            "payload": {},
                            "idempotency_key": "duplicate-key",
                        },
                    ],
                },
            },
        )
    )

    assert response["result"]["isError"] is True
    assert "unique idempotency_key" in response["result"]["structuredContent"]["error"]["message"]
    assert [request.operation for request in registry.transport.requests] == [
        "runtime.capabilities"
    ]


def test_run_plan_bounds_wait_purpose_after_durable_submission():
    registry = FakeRegistry()
    registry.transport = DurablePlanTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Complete a durable plan with a long step reason",
                    "connection_id": "ansys-one",
                    "steps": [
                        {
                            "step_id": "create",
                            "purpose": "x" * 240,
                            "operation": "project.create",
                            "payload": {},
                            "idempotency_key": "durable-create",
                            "wait": {"timeout_ms": 1000, "poll_interval_ms": 100},
                        },
                        {
                            "step_id": "inspect",
                            "purpose": "Inspect the completed project",
                            "operation": "project.inspect",
                            "payload": {},
                        },
                    ],
                },
            },
        )
    )

    value = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert value["status"] == "passed"
    wait_request = next(
        request
        for request in registry.transport.requests
        if request.operation == "runtime.job_status"
    )
    assert len(wait_request.purpose) == 240


def test_run_plan_preserves_nonterminal_run_when_wait_has_no_job_id():
    registry = FakeRegistry()
    registry.transport = NonDurableAcceptedPlanTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Preserve an accepted run without a durable job",
                    "connection_id": "ansys-one",
                    "steps": [
                        {
                            "step_id": "create",
                            "purpose": "Create the project asynchronously",
                            "operation": "project.create",
                            "payload": {},
                            "idempotency_key": "accepted-no-job",
                            "wait": {"timeout_ms": 1000},
                        },
                        {
                            "step_id": "inspect",
                            "purpose": "Inspect only after creation",
                            "operation": "project.inspect",
                            "payload": {},
                        },
                    ],
                },
            },
        )
    )

    value = response["result"]["structuredContent"]
    assert response["result"]["isError"] is True
    assert value["status"] == "interrupted"
    assert value["step_count"] == 1
    assert value["steps"][0]["run"]["state"] == "accepted"
    assert value["steps"][0]["run"]["run_id"]
    assert value["error"]["code"] == "durable_job_id_missing"


def test_run_plan_marks_submit_transport_interruption_as_mcp_error():
    registry = FakeRegistry()
    registry.transport = SubmitInterruptedPlanTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Expose a submit transport interruption",
                    "connection_id": "ansys-one",
                    "steps": [
                        {
                            "step_id": "create",
                            "purpose": "Create the disposable project",
                            "operation": "project.create",
                            "payload": {},
                            "idempotency_key": "interrupted-create",
                        },
                        {
                            "step_id": "inspect",
                            "purpose": "Inspect only after creation",
                            "operation": "project.inspect",
                            "payload": {},
                        },
                    ],
                },
            },
        )
    )

    value = response["result"]["structuredContent"]
    assert response["result"]["isError"] is True
    assert value["status"] == "interrupted"
    assert value["step_count"] == 0
    assert value["error"]["code"] == "ConnectionError"


def test_run_plan_stops_after_first_terminal_failure():
    registry = FakeRegistry()
    registry.transport = FailingPlanTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Stop a plan when verification fails",
                    "connection_id": "ansys-one",
                    "steps": [
                        {
                            "step_id": "inspect",
                            "purpose": "Inspect the selected project",
                            "operation": "project.inspect",
                            "payload": {},
                        },
                        {
                            "step_id": "export",
                            "purpose": "Export evidence only after inspection",
                            "operation": "image.export",
                            "payload": {},
                            "idempotency_key": "plan-export-evidence",
                        },
                    ],
                },
            },
        )
    )

    value = response["result"]["structuredContent"]
    assert value["status"] == "failed"
    assert value["step_count"] == 1
    assert value["planned_step_count"] == 2
    assert [request.operation for request in registry.transport.requests] == [
        "runtime.capabilities",
        "project.inspect",
    ]


def test_run_plan_audit_records_step_reasons_and_execution_links_without_payloads(tmp_path):
    database = tmp_path / "agent-audit.sqlite3"
    registry = FakeRegistry()
    registry.transport = PlanTransport()
    server = MCPRuntimeServer(registry, audit_database=database)
    server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Create and inspect a disposable project",
                    "connection_id": "ansys-one",
                    "steps": [
                        {
                            "step_id": "create",
                            "purpose": "Create a disposable project",
                            "operation": "project.create",
                            "payload": {"secret_like_detail": "not-in-clear-audit"},
                            "idempotency_key": "audit-plan-create",
                        },
                        {
                            "step_id": "inspect",
                            "purpose": "Inspect the disposable project",
                            "operation": "project.inspect",
                            "payload": {},
                        },
                    ],
                },
            },
        )
    )

    requested, completed = audit_events(database)
    assert requested["payload"]["plan_steps"] == [
        {
            "step_id": "create",
            "operation": "project.create",
            "purpose": "Create a disposable project",
        },
        {
            "step_id": "inspect",
            "operation": "project.inspect",
            "purpose": "Inspect the disposable project",
        },
    ]
    assert "not-in-clear-audit" not in json.dumps(requested["payload"])
    assert [step["state"] for step in completed["payload"]["execution"]["steps"]] == [
        "passed",
        "passed",
    ]
    server.close()


def test_run_plan_audit_preserves_nonterminal_overall_state(tmp_path):
    database = tmp_path / "agent-audit.sqlite3"
    registry = FakeRegistry()
    registry.transport = DurablePlanTransport()
    server = MCPRuntimeServer(registry, audit_database=database)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.run_plan",
                "arguments": {
                    "purpose": "Submit and expose one durable plan step",
                    "connection_id": "ansys-one",
                    "steps": [
                        {
                            "step_id": "create",
                            "purpose": "Create the project asynchronously",
                            "operation": "project.create",
                            "payload": {},
                            "idempotency_key": "nonterminal-create",
                        },
                        {
                            "step_id": "inspect",
                            "purpose": "Inspect only after creation",
                            "operation": "project.inspect",
                            "payload": {},
                        },
                    ],
                },
            },
        )
    )

    assert response["result"]["structuredContent"]["status"] == "waiting"
    completed = audit_events(database)[1]["payload"]["execution"]
    assert completed["state"] == "waiting"
    assert completed["terminal"] is False
    assert completed["steps"][0]["job_id"] == "plan-job"
    server.close()


def test_mcp_uses_cached_capability_mutability_for_submit_payload():
    registry = FakeRegistry()
    registry.transport = CapabilityAwareTransport()
    server = MCPRuntimeServer(registry)
    server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.capabilities",
                "arguments": {
                    "purpose": "Discover exact read operation metadata",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    response = server.handle(
        _rpc(
            2,
            "tools/call",
            {
                "name": "eda.submit",
                "arguments": {
                    "purpose": "Inspect one project without mutation",
                    "connection_id": "ansys-one",
                    "operation": "project.inspect",
                    "payload": {},
                },
            },
        )
    )
    assert response["result"]["isError"] is False
    assert registry.transport.requests[-1].payload["mutating"] is False


def test_mcp_read_discovers_missing_safety_metadata_without_an_agent_turn():
    registry = FakeRegistry()
    registry.transport = CapabilityAwareTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.read",
                "arguments": {
                    "purpose": "Inspect one project through the read-only lane",
                    "connection_id": "ansys-one",
                    "operation": "project.inspect",
                    "payload": {},
                },
            },
        )
    )
    rejected = server.handle(
        _rpc(
            2,
            "tools/call",
            {
                "name": "eda.read",
                "arguments": {
                    "purpose": "Reject a mutation through the read-only lane",
                    "connection_id": "ansys-one",
                    "operation": "project.create",
                    "payload": {},
                },
            },
        )
    )

    assert response["result"]["isError"] is False
    assert [request.operation for request in registry.transport.requests[:2]] == [
        "runtime.capabilities",
        "project.inspect",
    ]
    assert registry.transport.requests[1].payload["mutating"] is False
    assert rejected["result"]["isError"] is True
    assert rejected["result"]["structuredContent"]["error"]["code"] == "PermissionError"


def test_mcp_read_preflights_and_rejects_a_mutation_before_execution():
    registry = FakeRegistry()
    registry.transport = CapabilityAwareTransport()
    server = MCPRuntimeServer(registry)

    rejected = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.read",
                "arguments": {
                    "purpose": "Reject a mutation before it reaches EDA",
                    "connection_id": "ansys-one",
                    "operation": "project.create",
                    "payload": {},
                },
            },
        )
    )

    assert rejected["result"]["isError"] is True
    assert rejected["result"]["structuredContent"]["error"]["code"] == "PermissionError"
    assert [request.operation for request in registry.transport.requests] == [
        "runtime.capabilities"
    ]


def test_mcp_read_can_return_a_deterministic_bounded_result_view():
    registry = FakeRegistry()
    registry.transport = ResultViewTransport()
    server = MCPRuntimeServer(registry)
    server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.capabilities",
                "arguments": {
                    "purpose": "Discover exact read operation metadata",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    response = server.handle(
        _rpc(
            2,
            "tools/call",
            {
                "name": "eda.read",
                "arguments": {
                    "purpose": "Inspect only the required result facts",
                    "connection_id": "ansys-one",
                    "operation": "project.inspect",
                    "payload": {},
                    "result_view": {
                        "fields": [
                            {
                                "name": "session_count",
                                "pointer": "/data/sessions",
                                "mode": "count",
                            },
                            {"name": "active", "pointer": "/data/active"},
                            {
                                "name": "has_missing",
                                "pointer": "/data/missing",
                                "mode": "exists",
                            },
                        ]
                    },
                },
            },
        )
    )

    value = response["result"]["structuredContent"]
    assert value["response"]["result"] == {
        "session_count": 2,
        "active": "one",
        "has_missing": False,
    }
    assert value["response"]["result_view"] == {"projected": True, "field_count": 3}
    assert value["run"]["state"] == "passed"
    assert "sessions" not in json.dumps(value["response"])
    assert "result_view" not in registry.transport.requests[-1].payload


def test_mcp_read_result_view_rejects_a_missing_value_pointer():
    registry = FakeRegistry()
    registry.transport = ResultViewTransport()
    server = MCPRuntimeServer(registry)
    server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.capabilities",
                "arguments": {
                    "purpose": "Discover exact read operation metadata",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    response = server.handle(
        _rpc(
            2,
            "tools/call",
            {
                "name": "eda.read",
                "arguments": {
                    "purpose": "Reject an invalid result selector",
                    "connection_id": "ansys-one",
                    "operation": "project.inspect",
                    "payload": {},
                    "result_view": {"fields": [{"name": "missing", "pointer": "/data/missing"}]},
                },
            },
        )
    )

    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["error"]["code"] == "ValueError"


def test_mcp_read_result_view_does_not_mask_a_bridge_failure():
    registry = FakeRegistry()
    registry.transport = FailedResultViewTransport()
    server = MCPRuntimeServer(registry)
    server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.capabilities",
                "arguments": {
                    "purpose": "Discover exact read operation metadata",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    response = server.handle(
        _rpc(
            2,
            "tools/call",
            {
                "name": "eda.read",
                "arguments": {
                    "purpose": "Preserve a failed native read result",
                    "connection_id": "ansys-one",
                    "operation": "project.inspect",
                    "payload": {},
                    "result_view": {"fields": [{"name": "missing", "pointer": "/data/missing"}]},
                },
            },
        )
    )

    value = response["result"]["structuredContent"]
    assert value["run"]["state"] == "failed"
    assert value["response"]["error"] == {
        "code": "native_failure",
        "message": "Preserve this Bridge failure",
    }
    assert "result_view" not in value["response"]


def test_mcp_job_wait_polls_inside_runtime_until_terminal():
    registry = FakeRegistry()
    registry.transport = EventuallyTerminalTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.job.wait",
                "arguments": {
                    "purpose": "Wait for the existing durable job",
                    "connection_id": "ansys-one",
                    "job_id": "job-one",
                    "timeout_ms": 1000,
                    "poll_interval_ms": 100,
                },
            },
        )
    )
    value = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert value["run"]["state"] == "passed"
    assert value["run"]["terminal"] is True
    assert len(registry.transport.requests) == 3


@pytest.mark.parametrize("timeout", [True, MAX_WAIT_MS + 1])
def test_mcp_job_wait_rejects_unbounded_or_boolean_timeout(timeout):
    registry = FakeRegistry()
    registry.transport = EventuallyTerminalTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.job.wait",
                "arguments": {
                    "purpose": "Reject an invalid durable wait bound",
                    "connection_id": "ansys-one",
                    "job_id": "job-one",
                    "timeout_ms": timeout,
                },
            },
        )
    )

    assert response["result"]["isError"] is True
    assert (
        "timeout_ms is out of range" in response["result"]["structuredContent"]["error"]["message"]
    )
    assert registry.transport.requests == []


def test_mcp_job_wait_can_project_a_terminal_durable_result():
    registry = FakeRegistry()
    registry.transport = EventuallyTerminalTransport()
    server = MCPRuntimeServer(registry)
    response = server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.job.wait",
                "arguments": {
                    "purpose": "Wait for only the required durable result facts",
                    "connection_id": "ansys-one",
                    "job_id": "job-one",
                    "timeout_ms": 1000,
                    "poll_interval_ms": 100,
                    "result_view": {
                        "fields": [{"name": "job_field_count", "pointer": "/job", "mode": "count"}]
                    },
                },
            },
        )
    )

    value = response["result"]["structuredContent"]
    assert value["run"]["state"] == "passed"
    assert value["response"]["result"] == {"job_field_count": 4}
    assert "job_id" not in value["response"]["result"]


def test_mcp_read_can_wait_and_project_in_one_agent_call():
    registry = FakeRegistry()
    registry.transport = DurableReadTransport()
    server = MCPRuntimeServer(registry)
    server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.capabilities",
                "arguments": {
                    "purpose": "Discover durable read metadata",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    response = server.handle(
        _rpc(
            2,
            "tools/call",
            {
                "name": "eda.read",
                "arguments": {
                    "purpose": "Inspect and wait for required project facts",
                    "connection_id": "ansys-one",
                    "operation": "project.inspect",
                    "payload": {},
                    "wait": {"timeout_ms": 1000, "poll_interval_ms": 100},
                    "result_view": {
                        "fields": [
                            {"name": "bundle_complete", "pointer": "/data/bundle_complete"},
                            {"name": "object_count", "pointer": "/data/objects", "mode": "count"},
                        ]
                    },
                },
            },
        )
    )

    value = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert value["run"]["terminal"] is True
    assert value["response"]["result"] == {"bundle_complete": True, "object_count": 2}
    assert [request.operation for request in registry.transport.requests] == [
        "runtime.capabilities",
        "project.inspect",
        "runtime.job_status",
    ]
    assert "wait" not in registry.transport.requests[1].payload


def test_mcp_submit_can_wait_for_mutation_in_one_agent_call():
    registry = FakeRegistry()
    registry.transport = DurableReadTransport()
    server = MCPRuntimeServer(registry)
    server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.capabilities",
                "arguments": {
                    "purpose": "Discover durable mutation metadata",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    response = server.handle(
        _rpc(
            2,
            "tools/call",
            {
                "name": "eda.submit",
                "arguments": {
                    "purpose": "Create and wait for one disposable project",
                    "connection_id": "ansys-one",
                    "operation": "project.create",
                    "payload": {},
                    "idempotency_key": "create-one",
                    "wait": {"timeout_ms": 1000, "poll_interval_ms": 100},
                },
            },
        )
    )

    value = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert value["run"]["state"] == "passed"
    assert value["response"]["result"]["data"]["created"] is True
    assert [request.operation for request in registry.transport.requests] == [
        "runtime.capabilities",
        "project.create",
        "runtime.job_status",
    ]


def test_mcp_connection_reset_closes_only_runtime_owned_transport():
    registry = FakeRegistry()
    server = MCPRuntimeServer(registry)
    server.handle(
        _rpc(
            1,
            "tools/call",
            {
                "name": "eda.capabilities",
                "arguments": {
                    "purpose": "Open one disposable transport",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    assert server._transports
    response = server.handle(
        _rpc(
            2,
            "tools/call",
            {
                "name": "eda.connection.reset",
                "arguments": {
                    "purpose": "Reload an upgraded remote Runtime",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    assert response["result"]["structuredContent"]["status"] == "reset"
    assert registry.transport.closed is True
    assert server._transports == {}


def test_mcp_runtime_records_agent_fact_without_codex_hook(tmp_path):
    database = tmp_path / "agent-audit.sqlite3"
    registry = FakeRegistry()
    server = MCPRuntimeServer(registry, audit_database=database)
    server.handle(
        _rpc(
            1,
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "pi-agent", "version": "0.50"},
            },
        )
    )
    server.handle(
        _rpc(
            2,
            "tools/call",
            {
                "name": "eda.capabilities",
                "arguments": {
                    "purpose": "Inspect one selected EDA target",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    server.handle(
        _rpc(
            3,
            "tools/call",
            {
                "name": "eda.capabilities",
                "arguments": {
                    "purpose": "Inspect one selected EDA target",
                    "connection_id": "ansys-one",
                },
            },
        )
    )
    events = audit_events(database)
    assert [item["event_type"] for item in events] == [
        "agent.tool.requested",
        "agent.tool.completed",
        "agent.tool.requested",
        "agent.tool.completed",
    ]
    requested = events[0]["payload"]
    completed = events[1]["payload"]
    assert requested["purpose"] == "Inspect one selected EDA target"
    assert requested["actor"]["client"] == {"value": "pi-agent", "provenance": "observed"}
    assert requested["actor"]["client_version"] == {
        "value": "0.50",
        "provenance": "observed",
    }
    assert requested["actor"]["agent_family"] == {
        "value": "pi",
        "provenance": "inferred",
    }
    assert requested["actor"]["session_id"]["value"].startswith("mcp_")
    assert requested["actor"]["session_id"]["provenance"] == "inferred"
    assert completed["execution"]["linked"] is True
    assert completed["execution"]["state"] == "passed"
    assert completed["execution"]["connection_id"] == "ansys-one"
    assert completed["execution"]["eda"] == "ansys-electronics-desktop"
    assert completed["execution"]["operation"] == "runtime.capabilities"
    assert completed["timing"]["client_transport_ms"] is not None
    assert completed["timing"]["mcp_server_ms"] >= 0
    assert events[2]["payload"]["actor"]["session_id"] == requested["actor"]["session_id"]
    assert analyze_events(events)["findings"] == [
        {"code": "potential_redundant_discovery", "count": 1}
    ]
    server.close()


def test_mcp_accepts_bounded_declared_actor_metadata_but_observes_client(tmp_path):
    database = tmp_path / "agent-audit.sqlite3"
    registry = FakeRegistry()
    server = MCPRuntimeServer(registry, audit_database=database)
    server.handle(
        _rpc(
            1,
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "pi-agent", "version": "0.73.1"},
            },
        )
    )
    call = _rpc(
        2,
        "tools/call",
        {
            "name": "eda.capabilities",
            "arguments": {
                "purpose": "Inspect one selected EDA target",
                "connection_id": "ansys-one",
            },
            "_meta": {
                "io.modelcontextprotocol/clientInfo": {
                    "name": "pi-agent",
                    "version": "0.73.1",
                },
                "io.eda-runtime/actor": {
                    "agent_family": "pi-agent",
                    "agent_version": "0.73.1",
                    "provider": "openai",
                    "model": "gpt-test",
                    "reasoning": "medium",
                    "skill": "eda-runtime-control",
                    "session_id": "session-one",
                    "tool_call_id": "tool-one",
                    "client": "spoofed-client",
                    "unrecognized": "discard-me",
                },
            },
        },
    )
    server.handle(call)
    actor = audit_events(database)[0]["payload"]["actor"]
    assert actor["client"] == {"value": "pi-agent", "provenance": "observed"}
    assert actor["client_version"] == {"value": "0.73.1", "provenance": "observed"}
    assert actor["agent_family"] == {"value": "pi-agent", "provenance": "declared"}
    assert actor["provider"] == {"value": "openai", "provenance": "declared"}
    assert actor["model"] == {"value": "gpt-test", "provenance": "declared"}
    assert actor["reasoning"] == {"value": "medium", "provenance": "declared"}
    assert actor["session_id"] == {"value": "session-one", "provenance": "declared"}
    assert actor["tool_call_id"] == {"value": "tool-one", "provenance": "declared"}
    server.close()


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
