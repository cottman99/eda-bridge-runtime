import sys

import pytest

from eda_bridge_runtime import JobStore, RequestEnvelope
from eda_bridge_runtime.cancellation import cancellation_scope
from eda_bridge_runtime.errors import ExecutionError
from eda_bridge_runtime.process_execution import run_owned_process
from eda_bridge_runtime.retention import retain_stage


def test_queued_cancellation_is_durable_and_not_replayable(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    request = RequestEnvelope(
        purpose="Test cancellation",
        target={"eda": "test"},
        operation="native.execute",
        payload={},
        idempotency_key="cancel-test",
    )
    job = store.submit(request)
    assert store.cancel(job["job_id"], "User cancelled")["state"] == "cancelled"
    assert store.submit(request)["state"] == "cancelled"
    with pytest.raises(ValueError, match="transition"):
        store.transition(job["job_id"], "running")


def test_owned_process_observes_cancellation(tmp_path):
    with cancellation_scope(lambda: True), pytest.raises(ExecutionError) as error:
        run_owned_process([sys.executable, "-c", "import time; time.sleep(20)"], timeout=30)
    assert error.value.code == "cancellation_requested"
    assert error.value.uncertain is True


def test_retention_preserves_unknown_and_uncertain_directories(tmp_path):
    user = tmp_path / "user-data"
    user.mkdir()
    (user / "source").write_text("preserve")
    uncertain = tmp_path / "uncertain"
    uncertain.mkdir()
    retain_stage(uncertain, uncertain=True, keep=1)
    failed = tmp_path / "failed"
    failed.mkdir()
    retain_stage(failed, uncertain=False, keep=1)
    latest = tmp_path / "latest"
    latest.mkdir()
    retain_stage(latest, uncertain=False, keep=1)
    assert not failed.exists()
    assert user.exists() and uncertain.exists() and latest.exists()
