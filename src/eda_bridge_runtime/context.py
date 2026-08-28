"""Secret-free context handoff copied from an EDA UI to an agent."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .protocol import utc_now

CONTEXT_PREFIX_V1 = "EDA_CONTEXT:v1:"
CONTEXT_PREFIX_V2 = "EDA_CONTEXT:v2:"
CONTEXT_PREFIX = CONTEXT_PREFIX_V2
MAX_CONTEXT_BYTES = 16_384
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_FORBIDDEN_KEYS = {"token", "password", "secret", "private_key", "credential"}


def _runtime_home() -> Path:
    return Path(os.environ.get("EDA_RUNTIME_HOME", Path.home() / ".eda-bridge-runtime"))


def stable_origin_id(eda: str, *, root: str | Path | None = None) -> str:
    """Return one persisted, secret-free origin identity for an EDA adapter."""

    normalized = eda.strip()
    if not normalized:
        raise ValueError("eda is required")
    home = Path(root) if root is not None else _runtime_home()
    name = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16] + ".json"
    path = home / "origins" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        value = json.loads(path.read_text(encoding="utf-8"))
        origin_id = str(value.get("origin_id") or "")
        if value.get("eda") != normalized or not _SAFE_ID.fullmatch(origin_id):
            raise ValueError(f"invalid EDA origin record: {path}")
        return origin_id
    origin_id = "origin-" + uuid.uuid4().hex[:20]
    payload = {"schema_version": 1, "eda": normalized, "origin_id": origin_id}
    descriptor, temporary = tempfile.mkstemp(prefix="origin-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.write("\n")
        try:
            os.link(temporary, path)
        except FileExistsError:
            return stable_origin_id(normalized, root=home)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return origin_id


def capability_digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "cap-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _reject_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        keys = {str(key).lower() for key in value}
        if keys & _FORBIDDEN_KEYS:
            raise ValueError("context payloads must not contain credentials")
        for nested in value.values():
            _reject_forbidden_keys(nested)
    elif isinstance(value, list | tuple):
        for nested in value:
            _reject_forbidden_keys(nested)


@dataclass(frozen=True)
class EDAContext:
    eda: str
    target_kind: str
    locator: dict[str, Any]
    display_name: str | None = None
    generation: int = 1
    capabilities_hint: tuple[str, ...] = ()
    created_at: str = field(default_factory=utc_now)
    origin: dict[str, Any] = field(default_factory=dict)
    session: dict[str, Any] = field(default_factory=dict)
    target: dict[str, Any] = field(default_factory=dict)
    selection: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    freshness: dict[str, Any] = field(default_factory=dict)
    protocol: str = "eda-context/v2"

    def __post_init__(self) -> None:
        if not self.eda.strip() or not self.target_kind.strip() or not self.locator:
            raise ValueError("eda, target_kind, and locator are required")
        if self.protocol not in {"eda-context/v1", "eda-context/v2"}:
            raise ValueError("unsupported EDA context protocol")
        _reject_forbidden_keys(asdict(self))
        origin_id = str(self.origin.get("origin_id") or "")
        if origin_id and not _SAFE_ID.fullmatch(origin_id):
            raise ValueError("origin_id must be a safe identifier")

    def encode(self) -> str:
        payload = asdict(self)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        wrapper = {
            "payload": payload,
            "checksum": hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24],
        }
        data = json.dumps(wrapper, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if len(data.encode("utf-8")) > MAX_CONTEXT_BYTES:
            raise ValueError("EDA context exceeds the bounded payload limit")
        encoded = base64.urlsafe_b64encode(data.encode("utf-8")).decode("ascii").rstrip("=")
        prefix = CONTEXT_PREFIX_V1 if self.protocol == "eda-context/v1" else CONTEXT_PREFIX_V2
        return prefix + encoded

    @classmethod
    def decode(cls, token: str) -> EDAContext:
        if token.startswith(CONTEXT_PREFIX_V2):
            prefix = CONTEXT_PREFIX_V2
            expected_protocol = "eda-context/v2"
        elif token.startswith(CONTEXT_PREFIX_V1):
            prefix = CONTEXT_PREFIX_V1
            expected_protocol = "eda-context/v1"
        else:
            raise ValueError("not a supported EDA_CONTEXT token")
        encoded = token[len(prefix) :]
        padded = encoded + "=" * (-len(encoded) % 4)
        try:
            wrapper = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            payload = wrapper["payload"]
            claimed = wrapper["checksum"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("invalid EDA_CONTEXT token") from exc
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
        if actual != claimed:
            raise ValueError("EDA_CONTEXT checksum mismatch")
        if payload.get("protocol", expected_protocol) != expected_protocol:
            raise ValueError("EDA_CONTEXT prefix and payload protocol disagree")
        payload.setdefault("protocol", expected_protocol)
        if "capabilities_hint" in payload:
            payload["capabilities_hint"] = tuple(payload["capabilities_hint"])
        for name in ("origin", "session", "target", "selection", "capabilities", "freshness"):
            payload.setdefault(name, {})
        return cls(**payload)
