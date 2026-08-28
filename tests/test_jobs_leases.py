import time

import pytest

from eda_bridge_runtime.jobs import JobStore
from eda_bridge_runtime.lease import LeaseStore
from eda_bridge_runtime.protocol import RequestEnvelope, ResponseEnvelope
from eda_bridge_runtime.supervisor import run_job_worker


def request(key="same-key"):
    return RequestEnvelope(
        purpose="Build sanitized model",
        target={"eda": "example"},
        operation="build",
        idempotency_key=key,
    )


def test_job_submission_is_idempotent(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    first = store.submit(request())
    second = store.submit(request())
    assert second["job_id"] == first["job_id"]


def test_job_transitions_and_cursor(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    job = store.submit(request())
    store.transition(job["job_id"], "running")
    store.transition(job["job_id"], "passed", {"count": 2})
    events = store.events(job["job_id"], after_cursor=1)
    assert [event["state"] for event in events] == ["running", "passed"]
    with pytest.raises(ValueError):
        store.transition(job["job_id"], "running")


def test_lease_fencing_rejects_stale_owner(tmp_path):
    store = LeaseStore(tmp_path / "leases.sqlite3")
    stale = store.acquire("eda:slot-1", "worker-a", ttl_seconds=0.001)
    time.sleep(0.01)
    current = store.acquire("eda:slot-1", "worker-b")
    assert current.fencing_token > stale.fencing_token
    assert not store.release(stale)


def test_lease_blocks_other_live_owner(tmp_path):
    store = LeaseStore(tmp_path / "leases.sqlite3")
    store.acquire("eda:slot-1", "worker-a")
    with pytest.raises(RuntimeError, match="leased"):
        store.acquire("eda:slot-1", "worker-b")


def test_durable_worker_reloads_request_and_persists_result(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    submitted = store.submit(request())

    def handler(envelope):
        return ResponseEnvelope(
            request_id=envelope.request_id,
            run_id=envelope.run_id,
            status="passed",
            result={"observed": 7},
        )

    response = run_job_worker(store, submitted["job_id"], handler)
    assert response.status == "passed"
    completed = store.get(submitted["job_id"])
    assert completed["state"] == "passed"
    assert completed["result"]["result"] == {"observed": 7}


def test_durable_worker_normalizes_exception(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    submitted = store.submit(request())

    def handler(_envelope):
        raise RuntimeError("synthetic failure")

    response = run_job_worker(store, submitted["job_id"], handler)
    assert response.status == "failed"
    assert store.get(submitted["job_id"])["state"] == "failed"
