import io
import json
import os
import sys
import time

from eda_bridge_runtime.adapter import Adapter, AdapterResult
from eda_bridge_runtime.ledger import ExecutionLedger
from eda_bridge_runtime.protocol import RequestEnvelope, project_run
from eda_bridge_runtime.runtime import Runtime
from eda_bridge_runtime.transport import LocalTransport, serve_json_lines


class FakeAdapter(Adapter):
    name = "fake"
    version = "1"

    def capabilities(self, target=None):
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


def test_runtime_exposes_adapter_capabilities_without_adapter_execute(tmp_path):
    runtime = Runtime(ExecutionLedger(tmp_path / "ledger.sqlite3"))
    adapter = CountingAdapter()
    runtime.register("fake", adapter)
    request = RequestEnvelope(
        purpose="Discover available operations",
        target={"eda": "fake", "profile": "test"},
        operation="runtime.capabilities",
        payload={"mutating": False},
    )
    response = runtime.execute(request)
    assert response.status == "passed"
    assert response.result["data"]["capabilities"]["operations"] == ["inspect"]
    assert adapter.calls == 0
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


def test_runtime_returns_compact_receipt_without_mirroring_raw_result(tmp_path):
    runtime = make_runtime(tmp_path)
    source = read_request()
    source_response = runtime.execute(source)
    lookup = RequestEnvelope(
        purpose="Recover prior execution receipt",
        target={"eda": "fake"},
        operation="runtime.run_receipt",
        payload={"mutating": False, "run_id": source_response.run_id},
    )

    response = runtime.execute(lookup)
    receipt = response.result["data"]["receipt"]

    assert response.status == "passed"
    assert receipt["protocol"] == "eda-runtime.run-receipt/v1"
    assert receipt["run"]["run_id"] == source_response.run_id
    assert receipt["purpose"] == source.purpose
    assert receipt["operation"] == "inspect"
    assert receipt["ledger"]["finalized"] is True
    assert receipt["ledger"]["verified"] is True
    assert len(receipt["response_sha256"]) == 64
    assert "value" not in json.dumps(receipt)


def test_runtime_receipt_lookup_fails_closed_for_unknown_run(tmp_path):
    runtime = make_runtime(tmp_path)
    response = runtime.execute(
        RequestEnvelope(
            purpose="Recover missing execution receipt",
            target={"eda": "fake"},
            operation="runtime.run_receipt",
            payload={"mutating": False, "run_id": "run_missing"},
        )
    )
    assert response.status == "failed"
    assert response.error["code"] == "run_not_found"


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


def test_json_lines_server_isolates_bad_frame_and_continues(tmp_path):
    runtime = make_runtime(tmp_path)
    request = read_request()
    source = io.StringIO("not-json\n" + json.dumps(request.to_dict()) + "\n")
    destination = io.StringIO()
    serve_json_lines(source, destination, runtime.execute)
    responses = [json.loads(line) for line in destination.getvalue().splitlines()]
    assert responses[0]["status"] == "failed"
    assert responses[0]["error"]["code"] == "JSONDecodeError"
    assert responses[1]["status"] == "passed"


def test_json_lines_handshake_rejects_unsupported_version(tmp_path):
    destination = io.StringIO()
    serve_json_lines(
        io.StringIO(json.dumps({"protocol": "eda-runtime.handshake/v1", "versions": [9]}) + "\n"),
        destination,
        make_runtime(tmp_path).execute,
    )
    assert json.loads(destination.getvalue())["selected"] is None


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
    assert project_run(response.to_dict())["run_id"] == first.run_id
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
    assert transport.timeout_seconds == 30


def test_transport_close_is_bounded_and_stops_descendant_process(tmp_path):
    from eda_bridge_runtime.transport import PersistentStdioTransport

    heartbeat = tmp_path / "descendant-heartbeat.txt"
    child_code = (
        "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
        "[(p.open('a').write('x'), time.sleep(0.05)) for _ in range(1200)]"
    )
    parent_code = (
        "import json,pathlib,subprocess,sys,time; "
        "child=subprocess.Popen([sys.executable,'-u','-c',sys.argv[2],sys.argv[1]]); "
        "p=pathlib.Path(sys.argv[1]); "
        "deadline=time.monotonic()+5; "
        "\nwhile not p.exists() and time.monotonic()<deadline: time.sleep(0.01); "
        "\nprint(json.dumps({'protocol':'eda-runtime.handshake/v1','selected':1}),flush=True); "
        "time.sleep(60)"
    )
    transport = PersistentStdioTransport(
        [sys.executable, "-u", "-c", parent_code, str(heartbeat), child_code],
        timeout_seconds=5,
    )
    transport._start()
    assert heartbeat.is_file()

    started = time.monotonic()
    transport.close()
    elapsed = time.monotonic() - started
    size_after_close = os.path.getsize(heartbeat)
    time.sleep(0.25)

    assert elapsed < 4
    assert os.path.getsize(heartbeat) == size_after_close
