"""Versioned wire contracts shared by every transport and adapter."""

from __future__ import annotations

import os
import platform
import socket
import uuid
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import PurePath
from typing import Any

REQUEST_PROTOCOL = "eda-runtime.request/v1"
RESPONSE_PROTOCOL = "eda-runtime.response/v1"
EVENT_PROTOCOL = "eda-runtime.event/v1"
HANDSHAKE_PROTOCOL = "eda-runtime.handshake/v1"
RUN_VIEW_PROTOCOL = "eda-runtime.run-view/v1"
TERMINAL_RUN_STATES = frozenset({"passed", "failed", "cancelled"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass(frozen=True)
class SourcedValue:
    value: str
    provenance: str = "declared"


@dataclass(frozen=True)
class ActorIdentity:
    agent_family: SourcedValue = field(default_factory=lambda: SourcedValue("unknown", "unknown"))
    agent_version: SourcedValue = field(default_factory=lambda: SourcedValue("unknown", "unknown"))
    model: SourcedValue = field(default_factory=lambda: SourcedValue("unknown", "unknown"))
    provider: SourcedValue = field(default_factory=lambda: SourcedValue("unknown", "unknown"))
    reasoning: SourcedValue = field(default_factory=lambda: SourcedValue("unknown", "unknown"))
    harness: SourcedValue = field(default_factory=lambda: SourcedValue("none", "runtime_detected"))
    skill: SourcedValue = field(default_factory=lambda: SourcedValue("unknown", "unknown"))
    client: SourcedValue = field(default_factory=lambda: SourcedValue("unknown", "unknown"))

    @classmethod
    def detect(cls, declared: Mapping[str, str] | None = None) -> ActorIdentity:
        """Collect cheap metadata without delaying or blocking a request."""
        declared = declared or {}
        env_map = {
            "agent_family": ("CODEX_AGENT_FAMILY", "CODEX"),
            "agent_version": ("CODEX_VERSION",),
            "model": ("CODEX_MODEL", "OPENAI_MODEL"),
            "provider": ("CODEX_PROVIDER",),
            "reasoning": ("CODEX_REASONING_EFFORT",),
            "harness": ("EDA_HARNESS",),
            "skill": ("EDA_SKILL",),
            "client": ("EDA_CLIENT",),
        }

        def resolve(name: str) -> SourcedValue:
            if value := declared.get(name):
                return SourcedValue(str(value), "declared")
            for env_name in env_map[name]:
                if value := os.environ.get(env_name):
                    return SourcedValue(value, "runtime_detected")
            default = "none" if name == "harness" else "unknown"
            provenance = "runtime_detected" if name == "harness" else "unknown"
            return SourcedValue(default, provenance)

        return cls(**{name: resolve(name) for name in env_map})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RequestEnvelope:
    purpose: str
    target: dict[str, Any]
    operation: str
    payload: dict[str, Any] = field(default_factory=dict)
    expected_effect: str | None = None
    idempotency_key: str | None = None
    request_id: str = field(default_factory=lambda: new_id("req"))
    run_id: str = field(default_factory=lambda: new_id("run"))
    trace_id: str = field(default_factory=lambda: new_id("trace"))
    actor: ActorIdentity = field(default_factory=ActorIdentity.detect)
    protocol: str = REQUEST_PROTOCOL
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        purpose = self.purpose.strip()
        if len(purpose) < 3 or len(purpose) > 240:
            raise ValueError("purpose must contain 3..240 non-whitespace characters")
        if not self.operation.strip():
            raise ValueError("operation is required")
        if not isinstance(self.target, dict) or not self.target:
            raise ValueError("target must be a non-empty object")
        if self.protocol != REQUEST_PROTOCOL:
            raise ValueError(f"unsupported request protocol: {self.protocol}")

    @property
    def is_mutating(self) -> bool:
        return bool(self.payload.get("mutating", True))

    def require_idempotency(self) -> None:
        if self.is_mutating and not self.idempotency_key:
            raise ValueError("mutating requests require idempotency_key")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["actor"] = self.actor.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RequestEnvelope:
        raw = dict(data)
        actor_raw = raw.pop("actor", None)
        if actor_raw:
            fields = {
                key: SourcedValue(**value) if isinstance(value, dict) else SourcedValue(str(value))
                for key, value in actor_raw.items()
            }
            raw["actor"] = ActorIdentity(**fields)
        return cls(**raw)


@dataclass(frozen=True)
class ResponseEnvelope:
    request_id: str
    run_id: str
    status: str
    result: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    protocol: str = RESPONSE_PROTOCOL
    completed_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.status not in {"accepted", "running", "passed", "failed", "cancelled"}:
            raise ValueError(f"invalid response status: {self.status}")
        if self.status == "failed" and not self.error:
            raise ValueError("failed response requires error")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeFacts:
    runtime_version: str
    hostname: str = field(default_factory=socket.gethostname)
    os: str = field(default_factory=platform.platform)
    python: str = field(default_factory=platform.python_version)
    display: str | None = field(default_factory=lambda: os.environ.get("DISPLAY"))

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def project_run(response: Mapping[str, Any]) -> dict[str, Any]:
    """Project synchronous responses and durable jobs into one compact run view.

    The wire response remains unchanged. This additive projection gives clients a
    stable observation shape without forcing vendor bridges to share one execution
    model or returning raw artifact paths to the agent.
    """
    result = response.get("result")
    result = result if isinstance(result, Mapping) else {}
    job = result.get("job")
    job = job if isinstance(job, Mapping) else {}
    state = str(job.get("state") or response.get("status") or "unknown")
    run_id = str(
        job.get("run_id") or result.get("original_run_id") or response.get("run_id") or ""
    )
    request_id = str(
        job.get("request_id")
        or result.get("original_request_id")
        or response.get("request_id")
        or ""
    )
    job_id = str(job.get("job_id") or result.get("job_id") or "") or None
    updated_at = str(
        job.get("updated_at") or response.get("completed_at") or response.get("created_at") or ""
    ) or None
    return {
        "protocol": RUN_VIEW_PROTOCOL,
        "run_id": run_id,
        "request_id": request_id,
        "job_id": job_id,
        "state": state,
        "terminal": state in TERMINAL_RUN_STATES,
        "updated_at": updated_at,
        "evidence_refs": _evidence_refs(result),
    }


def _evidence_refs(value: Any, *, depth: int = 0) -> list[dict[str, Any]]:
    if depth > 6:
        return []
    references: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "artifacts" and isinstance(item, list):
                references.extend(
                    reference
                    for artifact in item
                    if isinstance(artifact, Mapping)
                    if (reference := _artifact_reference(artifact)) is not None
                )
            else:
                references.extend(_evidence_refs(item, depth=depth + 1))
    elif isinstance(value, list):
        for item in value:
            references.extend(_evidence_refs(item, depth=depth + 1))
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for reference in references:
        key = (
            reference.get("logical_name"),
            reference.get("sha256"),
            reference.get("size"),
        )
        unique[key] = reference
    return list(unique.values())


def _artifact_reference(artifact: Mapping[str, Any]) -> dict[str, Any] | None:
    digest = artifact.get("sha256") or artifact.get("bundle_sha256")
    path = artifact.get("path")
    logical_name = artifact.get("logical_name") or artifact.get("name")
    if not logical_name and path:
        logical_name = PurePath(str(path).replace("\\", "/")).name
    if not any((logical_name, digest, artifact.get("size"))):
        return None
    reference: dict[str, Any] = {"logical_name": str(logical_name or "artifact")}
    if digest:
        reference["sha256"] = str(digest)
    if artifact.get("size") is not None:
        reference["size"] = int(artifact["size"])
    if artifact.get("media_type"):
        reference["media_type"] = str(artifact["media_type"])
    if artifact.get("retention_days") is not None:
        reference["retention_days"] = int(artifact["retention_days"])
    return reference
