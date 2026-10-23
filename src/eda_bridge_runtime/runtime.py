"""Request orchestration and evidence capture."""

from __future__ import annotations

import time
from typing import Any

from ._version import __version__
from .adapter import Adapter, AdapterContext, AdapterResult
from .cancellation import check_cancellation
from .connections import runtime_home
from .errors import error_facts
from .execution_scope import execution_scope
from .lease import LeaseStore
from .ledger import ExecutionLedger
from .protocol import RequestEnvelope, ResponseEnvelope, RuntimeFacts
from .resources import resource_keys


class Runtime:
    def __init__(self, ledger: ExecutionLedger):
        self.ledger = ledger
        self._adapters: dict[str, Adapter] = {}
        self.facts = RuntimeFacts(runtime_version=__version__)
        self.resource_path = runtime_home() / "resources.sqlite3"
        self.resources = LeaseStore(self.resource_path)

    def register(self, eda: str, adapter: Adapter) -> None:
        if eda in self._adapters:
            raise ValueError(f"adapter already registered for {eda}")
        self._adapters[eda] = adapter

    def execute(self, request: RequestEnvelope) -> ResponseEnvelope:
        request.require_idempotency()
        started = time.monotonic()
        self.ledger.record_request(request, self.facts.to_dict())
        if request.is_mutating:
            claim = self.ledger.claim_idempotency(request)
            if claim["state"] != "claimed":
                response = self._idempotency_response(request, claim)
                self._record_completed(request, response, started)
                return response
        eda = str(request.target.get("eda", ""))
        if request.operation == "runtime.run_receipt":
            source_run_id = str(request.payload.get("run_id") or "").strip()
            if not 5 <= len(source_run_id) <= 160:
                response = ResponseEnvelope(
                    request_id=request.request_id,
                    run_id=request.run_id,
                    status="failed",
                    error={
                        "code": "invalid_run_id",
                        "message": "run_id must contain 5..160 non-whitespace characters",
                    },
                )
            elif (receipt := self.ledger.compact_receipt(source_run_id)) is None:
                response = ResponseEnvelope(
                    request_id=request.request_id,
                    run_id=request.run_id,
                    status="failed",
                    error={
                        "code": "run_not_found",
                        "message": "the requested run is not present in this Runtime ledger",
                    },
                )
            else:
                response = ResponseEnvelope(
                    request_id=request.request_id,
                    run_id=request.run_id,
                    status="passed",
                    result={"data": {"receipt": receipt}, "artifacts": []},
                )
            self._record_completed(request, response, started)
            return response
        adapter = self._adapters.get(eda)
        if adapter is None:
            response = ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="failed",
                error={"code": "adapter_not_found", "message": f"no adapter registered for {eda}"},
            )
            if request.is_mutating:
                self.ledger.complete_idempotency(request, response.to_dict())
            self._record_completed(request, response, started)
            return response

        def emit(event_type: str, payload: dict[str, Any]) -> None:
            self.ledger.append(
                run_id=request.run_id,
                request_id=request.request_id,
                event_type=event_type,
                source=f"adapter:{adapter.name}",
                payload={
                    "inherited_intent": {
                        "purpose": request.purpose,
                        "expected_effect": request.expected_effect,
                    },
                    "observed": payload,
                },
            )

        leases = []
        response = None
        try:
            needs_admission = getattr(
                adapter, "requires_admission", lambda value: value.is_mutating
            )
            if (
                request.operation != "runtime.capabilities"
                and not request.is_mutating
                and needs_admission(request)
            ):
                raise ValueError(
                    "This registered operation requires mutation admission and an idempotency key"
                )
            if request.is_mutating:
                resolver = getattr(adapter, "resource_keys", resource_keys)
                leases = self.resources.acquire_many(
                    resolver(request),
                    request.run_id,
                    wait_seconds=min(300, float(request.payload.get("queue_timeout_seconds", 30))),
                )

            def assert_current() -> None:
                check_cancellation()
                for lease in leases:
                    self.resources.assert_current(lease)

            emit("adapter.started", {"adapter": adapter.name, "version": adapter.version})
            if request.operation == "runtime.capabilities":
                capabilities = adapter.capabilities(request.target)
                emit(
                    "adapter.capabilities.observed",
                    {"adapter": adapter.name, "version": adapter.version},
                )
                result = AdapterResult(status="passed", result={"capabilities": capabilities})
            else:
                assert_current()
                adapter_context = AdapterContext(
                    emit=emit,
                    fencing_token=leases[0].fencing_token if leases else None,
                    assert_current=assert_current,
                    admission={
                        "store": str(self.resource_path),
                        "leases": [lease.__dict__ for lease in leases],
                    },
                )
                with execution_scope(adapter_context.admission, request.purpose):
                    result = adapter.execute(request, adapter_context)
            response = ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status=result.status,
                result={"data": result.result, "artifacts": list(result.artifacts)},
                error=result.error
                or (
                    {"code": "execution_failed", "message": "Adapter returned a failed result"}
                    if result.status == "failed"
                    else None
                ),
            )
        except Exception as exc:  # adapter boundary intentionally normalizes failures
            facts = error_facts(exc)
            response = ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="uncertain" if facts.get("execution_uncertain") else "failed",
                error=facts,
            )
        finally:
            for lease in reversed(leases):
                if response is None or response.status == "uncertain":
                    self.resources.mark_uncertain(lease)
                else:
                    self.resources.release(lease)
        if request.is_mutating:
            self.ledger.complete_idempotency(request, response.to_dict())
        self._record_completed(request, response, started)
        return response

    @staticmethod
    def _idempotency_response(request: RequestEnvelope, claim: dict[str, Any]) -> ResponseEnvelope:
        if claim["state"] == "completed":
            previous = claim["response"]
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status=previous["status"],
                result={
                    "deduplicated": True,
                    "original_request_id": previous["request_id"],
                    "original_run_id": previous["run_id"],
                    "original_result": previous.get("result", {}),
                },
                error=previous.get("error"),
            )
        if claim["state"] == "in_progress":
            return ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="accepted",
                result={
                    "deduplicated": True,
                    "state": "in_progress",
                    "first_request_id": claim["first_request_id"],
                },
            )
        return ResponseEnvelope(
            request_id=request.request_id,
            run_id=request.run_id,
            status="failed",
            error={
                "code": "idempotency_conflict",
                "message": "idempotency key was reused for a different operation",
            },
        )

    def _record_completed(
        self, request: RequestEnvelope, response: ResponseEnvelope, started: float
    ) -> None:
        self.ledger.append(
            run_id=request.run_id,
            request_id=request.request_id,
            event_type="request.completed",
            source="runtime",
            payload={
                "observed_result": response.to_dict(),
                "timing": {"runtime_total_ms": round((time.monotonic() - started) * 1000, 3)},
            },
        )
        self.ledger.finalize(request.run_id)
