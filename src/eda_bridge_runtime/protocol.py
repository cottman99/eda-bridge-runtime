"""Versioned wire contracts shared by every transport and adapter."""

from __future__ import annotations

import os
import platform
import socket
import uuid
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

REQUEST_PROTOCOL = "eda-runtime.request/v1"
RESPONSE_PROTOCOL = "eda-runtime.response/v1"
EVENT_PROTOCOL = "eda-runtime.event/v1"
HANDSHAKE_PROTOCOL = "eda-runtime.handshake/v1"


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
