"""One durable submission service for local and SSH vendor bridges."""

from pathlib import Path

from .jobs import JobStore
from .protocol import ResponseEnvelope
from .supervisor import spawn_detached_worker


class DurableService:
    def __init__(self, jobs_path, ledger_path, *, runtime_factory, worker_command):
        self.jobs_path = Path(jobs_path).resolve()
        self.ledger_path = Path(ledger_path).resolve()
        self.store = JobStore(self.jobs_path)
        self.runtime_factory = runtime_factory
        self.worker_command = worker_command
        self.spawn = spawn_detached_worker

    def prepare_request(self, request):
        return request

    def should_detach(self, request):
        return request.is_mutating

    def handle(self, request):
        if request.operation == "runtime.job_cancel":
            request.require_idempotency()
            job = self.store.cancel(str(request.payload["job_id"]), request.purpose)
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="passed",
                result={"job": self._public_job(job), "cancellation_requested": True},
            )
        if request.operation in {"runtime.job_status", "runtime.job_events"}:
            self.store.recover_orphans()
            job_id = str(request.payload["job_id"])
            result = {"job": self._public_job(self.store.get(job_id))}
            if request.operation == "runtime.job_events":
                result.update(
                    job_id=job_id,
                    events=self.store.events(job_id, int(request.payload.get("after_cursor", 0))),
                )
            return ResponseEnvelope(
                request_id=request.request_id, run_id=request.run_id, status="passed", result=result
            )
        request = self.prepare_request(request)
        if not self.should_detach(request):
            return self.runtime_factory(self.ledger_path).execute(request)
        job = self.store.submit(request)
        spawned = any(
            event["detail"].get("event") == "worker.spawned"
            for event in self.store.events(job["job_id"])
        )
        if job["state"] == "queued" and not spawned:
            # Competing submitters may start two tiny workers. The SQLite state
            # transition claims execution atomically before either opens an SDK.
            self.spawn(
                self.worker_command(request, job["job_id"]),
                job_id=job["job_id"],
                log_path=self.jobs_path.parent / "job-logs" / (job["job_id"] + ".log"),
                store=self.store,
            )
            job = self.store.get(job["job_id"])
        status = "accepted" if job["state"] in {"queued", "running"} else job["state"]
        error = None
        if status == "orphaned":
            status = "uncertain"
            error = {
                "code": "execution_uncertain",
                "message": "Worker ended without a terminal result; reconcile before another write",
                "execution_uncertain": True,
            }
        elif job.get("result"):
            error = job["result"].get("error")
        return ResponseEnvelope(
            request_id=request.request_id,
            run_id=request.run_id,
            status=status,
            result={"job": self._public_job(job)},
            error=error,
        )

    @staticmethod
    def _public_job(job):
        return {
            key: job[key]
            for key in (
                "job_id",
                "request_id",
                "run_id",
                "state",
                "result",
                "created_at",
                "updated_at",
            )
        }
