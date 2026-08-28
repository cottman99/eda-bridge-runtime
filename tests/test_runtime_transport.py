import io
import json

from eda_bridge_runtime.adapter import Adapter, AdapterResult
from eda_bridge_runtime.ledger import ExecutionLedger
from eda_bridge_runtime.protocol import RequestEnvelope
from eda_bridge_runtime.runtime import Runtime
from eda_bridge_runtime.transport import LocalTransport, serve_json_lines


class FakeAdapter(Adapter):
    name = "fake"
    version = "1"

    def capabilities(self):
        return {"operations": ["inspect"], "escape_lanes": []}

    def execute(self, request, context):
        context.emit("adapter.observation", {"operation": request.operation})
        return AdapterResult(status="passed", result={"value": 42})


class CountingAdapter(FakeAdapter):
    def __init__(self):
        self.calls = 0

    def execute(self, request, context):
        self.calls += 1
        return super().execute(request, context)


def make_runtime(tmp_path):
    runtime = Runtime(ExecutionLedger(tmp_path / "ledger.sqlite3"))
    runtime.register("fake", FakeAdapter())
    return runtime


def read_request():
    return RequestEnvelope(
        purpose="Inspect sanitized design",
        target={"eda": "fake"},
        operation="inspect",
        payload={"mutating": False},
    )


def test_local_transport_and_intent_inheritance(tmp_path):
    runtime = make_runtime(tmp_path)
    response = LocalTransport(runtime.execute).request(read_request())
    assert response.status == "passed"
    events = runtime.ledger.events(run_id=response.run_id)
    observation = next(event for event in events if event["event_type"] == "adapter.observation")
    assert observation["payload"]["inherited_intent"]["purpose"] == "Inspect sanitized design"
    assert runtime.ledger.verify(response.run_id)


def test_missing_adapter_is_audited_failure(tmp_path):
    runtime = make_runtime(tmp_path)
    request = RequestEnvelope(
        purpose="Inspect unavailable EDA",
        target={"eda": "missing"},
        operation="inspect",
        payload={"mutating": False},
    )
    response = runtime.execute(request)
    assert response.status == "failed"
    assert response.error["code"] == "adapter_not_found"
    assert runtime.ledger.verify(request.run_id)


def test_json_lines_server_uses_same_envelope(tmp_path):
    runtime = make_runtime(tmp_path)
    request = read_request()
    source = io.StringIO(
        json.dumps({"protocol": "eda-runtime.handshake/v1", "versions": [1]})
        + "\n"
        + json.dumps(request.to_dict())
        + "\n"
    )
    destination = io.StringIO()
    serve_json_lines(source, destination, runtime.execute)
    responses = [json.loads(line) for line in destination.getvalue().splitlines()]
    assert responses[0]["selected"] == 1
    assert responses[1]["status"] == "passed"


def test_mutation_is_not_executed_twice_for_same_key(tmp_path):
    runtime = Runtime(ExecutionLedger(tmp_path / "ledger.sqlite3"))
    adapter = CountingAdapter()
    runtime.register("fake", adapter)
    first = RequestEnvelope(
        purpose="Change sanitized design",
        target={"eda": "fake"},
        operation="set",
        payload={"mutating": True, "value": 1},
        idempotency_key="stable-key",
    )
    assert runtime.execute(first).status == "passed"
    retry = RequestEnvelope(
        purpose=first.purpose,
        target=first.target,
        operation=first.operation,
        payload=first.payload,
        idempotency_key=first.idempotency_key,
    )
    response = runtime.execute(retry)
    assert response.status == "passed"
    assert response.result["deduplicated"] is True
    assert adapter.calls == 1


def test_mutation_key_conflict_is_rejected(tmp_path):
    runtime = Runtime(ExecutionLedger(tmp_path / "ledger.sqlite3"))
    runtime.register("fake", CountingAdapter())
    first = RequestEnvelope(
        purpose="Change sanitized design",
        target={"eda": "fake"},
        operation="set",
        payload={"mutating": True, "value": 1},
        idempotency_key="stable-key",
    )
    runtime.execute(first)
    conflict = RequestEnvelope(
        purpose="Change sanitized design again",
        target={"eda": "fake"},
        operation="set",
        payload={"mutating": True, "value": 2},
        idempotency_key="stable-key",
    )
    response = runtime.execute(conflict)
    assert response.status == "failed"
    assert response.error["code"] == "idempotency_conflict"


def test_ssh_transport_uses_one_remote_command_string():
    from eda_bridge_runtime.transport import SSHStdioTransport

    transport = SSHStdioTransport(
        "eda.example", ["ads-agent", "runtime", "serve", "--ledger", "/tmp/a b.sqlite3"]
    )
    assert transport.command == [
        "ssh",
        "eda.example",
        "ads-agent runtime serve --ledger '/tmp/a b.sqlite3'",
    ]
