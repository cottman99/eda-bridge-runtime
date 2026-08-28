"""Request orchestration and evidence capture."""

from __future__ import annotations

import time
from typing import Any

from ._version import __version__
from .adapter import Adapter, AdapterContext
from .ledger import ExecutionLedger
from .protocol import RequestEnvelope, ResponseEnvelope, RuntimeFacts


class Runtime:
    def __init__(self, ledger: ExecutionLedger):
        self.ledger = ledger
        self._adapters: dict[str, Adapter] = {}
        self.facts = RuntimeFacts(runtime_version=__version__)

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

        try:
            emit("adapter.started", {"adapter": adapter.name, "version": adapter.version})
            result = adapter.execute(request, AdapterContext(emit=emit))
            response = ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status=result.status,
                result={"data": result.result, "artifacts": list(result.artifacts)},
            )
        except Exception as exc:  # adapter boundary intentionally normalizes failures
            response = ResponseEnvelope(
                request_id=request.request_id,
                run_id=request.run_id,
                status="failed",
                error={"code": type(exc).__name__, "message": str(exc)},
            )
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
