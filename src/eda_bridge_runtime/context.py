"""Secret-free context handoff copied from an EDA UI to an agent."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .protocol import utc_now

CONTEXT_PREFIX = "EDA_CONTEXT:v1:"


@dataclass(frozen=True)
class EDAContext:
    eda: str
    target_kind: str
    locator: dict[str, Any]
    display_name: str | None = None
    generation: int = 1
    capabilities_hint: tuple[str, ...] = ()
    created_at: str = field(default_factory=utc_now)
    protocol: str = "eda-context/v1"

    def __post_init__(self) -> None:
        if not self.eda.strip() or not self.target_kind.strip() or not self.locator:
            raise ValueError("eda, target_kind, and locator are required")
        forbidden = {"token", "password", "secret", "private_key", "credential"}
        keys = {str(key).lower() for key in self.locator}
        if keys & forbidden:
            raise ValueError("context locators must not contain credentials")

    def encode(self) -> str:
        payload = asdict(self)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        wrapper = {
            "payload": payload,
            "checksum": hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24],
        }
        data = json.dumps(wrapper, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        encoded = base64.urlsafe_b64encode(data.encode("utf-8")).decode("ascii").rstrip("=")
        return CONTEXT_PREFIX + encoded

    @classmethod
    def decode(cls, token: str) -> EDAContext:
        if not token.startswith(CONTEXT_PREFIX):
            raise ValueError("not an EDA_CONTEXT/v1 token")
        encoded = token[len(CONTEXT_PREFIX) :]
        padded = encoded + "=" * (-len(encoded) % 4)
        try:
            wrapper = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            payload = wrapper["payload"]
            claimed = wrapper["checksum"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("invalid EDA_CONTEXT/v1 token") from exc
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
        if actual != claimed:
            raise ValueError("EDA_CONTEXT/v1 checksum mismatch")
        if "capabilities_hint" in payload:
            payload["capabilities_hint"] = tuple(payload["capabilities_hint"])
        return cls(**payload)
