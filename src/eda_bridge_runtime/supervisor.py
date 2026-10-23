"""Detached durable-job worker primitives shared by long-running EDA adapters."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from .cancellation import cancellation_scope
from .errors import error_facts
from .jobs import JobStore
from .protocol import RequestEnvelope, ResponseEnvelope


def spawn_detached_worker(
    command: Sequence[str],
    *,
    job_id: str,
    log_path: str | Path,
    store: JobStore,
) -> int:
    """Start a worker that is not coupled to the submitting SSH/stdin session."""
    destination = Path(log_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stream = destination.open("ab", buffering=0)
    options: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": stream,
        "stderr": subprocess.STDOUT,
        "close_fds": True,
    }
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        options["start_new_session"] = True
    try:
        process = subprocess.Popen(list(command), **options)  # noqa: S603
    except Exception:
        stream.close()
        raise
    stream.close()
    store.record_event(
        job_id,
        {
            "event": "worker.spawned",
            "pid": process.pid,
            "log_path": str(destination),
        },
    )
    return process.pid


def run_job_worker(
    store: JobStore,
    job_id: str,
    handler: Callable[[RequestEnvelope], ResponseEnvelope],
) -> ResponseEnvelope:
    job = store.get(job_id)
    if job["state"] != "queued":
        raise ValueError(f"job is not runnable from state {job['state']}")
    store.transition(job_id, "running", {"event": "worker.started", "pid": os.getpid()})
    request = store.request(job_id)
    try:
        with cancellation_scope(lambda: store.cancellation_requested(job_id)):
            response = handler(request)
    except Exception as exc:
        facts = error_facts(exc)
        response = ResponseEnvelope(
            request_id=request.request_id,
            run_id=request.run_id,
            status="uncertain" if facts.get("execution_uncertain") else "failed",
            error=facts,
        )
    terminal = response.status if response.status in {"passed", "uncertain"} else "failed"
    store.transition(job_id, terminal, response.to_dict())
    return response
