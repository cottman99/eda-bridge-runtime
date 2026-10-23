import sys
import threading
import time

import pytest

from eda_bridge_runtime import AdapterResult, ExecutionLedger, RequestEnvelope, Runtime
from eda_bridge_runtime.admission import assert_admission
from eda_bridge_runtime.errors import ExecutionError
from eda_bridge_runtime.jobs import JobStore, _pid_is_alive
from eda_bridge_runtime.process_execution import run_owned_process


def request(project, *, key="one", **payload):
    return RequestEnvelope(
        purpose="Verify worker coordination",
        target={"eda": "test", "project": str(project)},
        operation="native.execute",
        idempotency_key=key,
        payload=payload,
    )


def test_two_connections_share_host_coordination_and_run_sequentially(tmp_path, monkeypatch):
    monkeypatch.setenv("EDA_RUNTIME_HOME", str(tmp_path / "host"))
    entered, release = threading.Event(), threading.Event()
    observed = []

    class Vendor:
        name, version = "test", "1"

        def execute(self, value, context):
            assert_admission(context.admission)
            observed.append(value.idempotency_key)
            if value.idempotency_key == "first":
                entered.set()
                assert release.wait(5)
            return AdapterResult(status="passed", result={"observed": value.idempotency_key})

    def run(name):
        runtime = Runtime(ExecutionLedger(tmp_path / name / "ledger.sqlite3"))
        runtime.register("test", Vendor())
        response = runtime.execute(request(tmp_path / "same-project", key=name))
        assert response.status == "passed"

    first = threading.Thread(target=run, args=("first",))
    second = threading.Thread(target=run, args=("second",))
    first.start()
    assert entered.wait(5)
    second.start()
    time.sleep(0.2)
    assert observed == ["first"]
    release.set()
    first.join(5)
    second.join(5)
    assert observed == ["first", "second"]
    assert not first.is_alive() and not second.is_alive()


def test_uncertain_execution_blocks_new_work_and_duplicate_never_replays(tmp_path, monkeypatch):
    monkeypatch.setenv("EDA_RUNTIME_HOME", str(tmp_path / "host"))
    calls, tickets = [], []

    class Vendor:
        name, version = "test", "1"

        def execute(self, value, context):
            calls.append(value.request_id)
            tickets.append(context.admission)
            raise ExecutionError("execution_uncertain", "Lost vendor completion", uncertain=True)

    runtime = Runtime(ExecutionLedger(tmp_path / "ledger.sqlite3"))
    runtime.register("test", Vendor())
    initial = request(tmp_path / "project")
    assert runtime.execute(initial).status == "uncertain"
    assert runtime.execute(request(tmp_path / "project")).status == "uncertain"
    rejected = runtime.execute(
        request(tmp_path / "project", key="different", queue_timeout_seconds=0)
    )
    assert rejected.error["code"] == "execution_uncertain"
    assert len(calls) == 1
    with pytest.raises(ExecutionError):
        assert_admission(tickets[0])


def test_job_identity_includes_operational_secrets_before_redaction(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.submit(request(tmp_path / "project", release_handle="handle-A"))
    with pytest.raises(ExecutionError) as error:
        store.submit(request(tmp_path / "project", release_handle="handle-B"))
    assert error.value.code == "idempotency_conflict"


def test_owned_worker_deadline_is_portable_and_stops_its_process(tmp_path):
    pid_path = tmp_path / "pid.txt"
    script = tmp_path / "worker.py"
    script.write_text(
        "import os, pathlib, time\npathlib.Path("
        + repr(str(pid_path))
        + ").write_text(str(os.getpid()))\nprint('worker started', flush=True)\ntime.sleep(30)\n"
    )
    with pytest.raises(ExecutionError) as error:
        run_owned_process(
            [sys.executable, str(script)], timeout=0.5, log_path=str(tmp_path / "worker.log")
        )
    assert error.value.uncertain
    assert not _pid_is_alive(int(pid_path.read_text()))
    assert "worker started" in (tmp_path / "worker.log").read_text()


def test_missing_sdk_is_an_environment_fact(tmp_path, monkeypatch):
    from eda_bridge_runtime.errors import error_facts

    facts = error_facts(ModuleNotFoundError("No module named 'vendor_sdk'"))
    assert facts["code"] == "dependency_missing"
    assert facts["phase"] == "environment"


def test_standard_library_program_can_call_unwrapped_object_method(tmp_path):
    from eda_bridge_runtime.python_execution import execute_python

    class Official:
        def newly_added_method(self, value):
            return value + 1

    program = {
        "source": "import statistics\ndef run(api, context):\n"
        "    return {'value': api.newly_added_method(statistics.mean([1, 3]))}\n"
    }
    assert execute_python(program, Official(), {}) == {"value": 3}
