"""Deterministic local and SSH adapter connection registry."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from .protocol import RequestEnvelope
from .transport import PersistentStdioTransport, SSHStdioTransport, Transport

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def runtime_home() -> Path:
    return Path(os.environ.get("EDA_RUNTIME_HOME", Path.home() / ".eda-bridge-runtime"))


def default_connections_path() -> Path:
    return runtime_home() / "connections.json"


@dataclass(frozen=True)
class ConnectionSpec:
    connection_id: str
    eda: str
    kind: str
    command: tuple[str, ...]
    host: str | None = None
    ssh_options: tuple[str, ...] = ()
    timeout_seconds: float = 30
    origin_id: str | None = None

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.connection_id):
            raise ValueError("connection_id must be 1..64 safe identifier characters")
        if not self.eda.strip() or not self.command:
            raise ValueError("eda and command are required")
        if self.kind not in {"local", "ssh"}:
            raise ValueError("connection kind must be local or ssh")
        if self.kind == "ssh" and not self.host:
            raise ValueError("SSH connections require host")
        if self.kind == "local" and self.host:
            raise ValueError("local connections must not define host")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.origin_id and not _ID.fullmatch(self.origin_id):
            raise ValueError("origin_id must be 1..64 safe identifier characters")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["command"] = list(self.command)
        value["ssh_options"] = list(self.ssh_options)
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ConnectionSpec:
        data = dict(value)
        data["command"] = tuple(data.get("command", ()))
        data["ssh_options"] = tuple(data.get("ssh_options", ()))
        return cls(**data)

    def open(self) -> Transport:
        if self.kind == "local":
            return PersistentStdioTransport(self.command, timeout_seconds=self.timeout_seconds)
        return SSHStdioTransport(
            str(self.host),
            self.command,
            ssh_options=self.ssh_options,
            timeout_seconds=self.timeout_seconds,
        )


def discover_connection_origin(
    spec: ConnectionSpec, *, transport: Transport | None = None
) -> ConnectionSpec:
    """Read one adapter identity during connection setup and bind its stable origin."""

    owned = transport is None
    selected = transport or spec.open()
    try:
        response = selected.request(
            RequestEnvelope(
                purpose="Bind one registered EDA connection to its stable origin",
                target={"eda": spec.eda, "connection_id": spec.connection_id},
                operation="runtime.capabilities",
                payload={"mutating": False},
            )
        )
    finally:
        if owned:
            selected.close()
    data = response.result.get("data") if isinstance(response.result, dict) else None
    capabilities = data.get("capabilities") if isinstance(data, dict) else None
    origin_id = str((capabilities or {}).get("origin_id") or "")
    if response.status != "passed" or not _ID.fullmatch(origin_id):
        raise ValueError("EDA adapter did not return a valid stable origin_id")
    return replace(spec, origin_id=origin_id)


class ConnectionRegistry:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_connections_path()

    def list(self) -> list[ConnectionSpec]:
        if not self.path.is_file():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("connections"), list):
            raise ValueError(f"unsupported connection registry: {self.path}")
        return sorted(
            (ConnectionSpec.from_dict(item) for item in data["connections"]),
            key=lambda item: item.connection_id,
        )

    def upsert(self, spec: ConnectionSpec) -> ConnectionSpec:
        values = {item.connection_id: item for item in self.list()}
        values[spec.connection_id] = spec
        self._write(list(values.values()))
        return spec

    def remove(self, connection_id: str) -> bool:
        values = {item.connection_id: item for item in self.list()}
        removed = values.pop(connection_id, None) is not None
        if removed:
            self._write(list(values.values()))
        return removed

    def resolve(
        self,
        *,
        connection_id: str | None = None,
        eda: str | None = None,
        origin_id: str | None = None,
    ) -> ConnectionSpec:
        values = self.list()
        if connection_id:
            match = next((item for item in values if item.connection_id == connection_id), None)
            if not match:
                raise ValueError(f"unknown EDA connection: {connection_id}")
            if eda and match.eda != eda:
                raise ValueError(f"connection {connection_id} does not target {eda}")
            if origin_id and match.origin_id not in {None, origin_id}:
                raise ValueError(f"connection {connection_id} does not target origin {origin_id}")
            return match
        if origin_id:
            matches = [
                item
                for item in values
                if item.origin_id == origin_id and (not eda or item.eda == eda)
            ]
            if len(matches) == 1:
                return matches[0]
            legacy = [item for item in values if not eda or item.eda == eda]
            if len(matches) == 0 and len(legacy) == 1 and legacy[0].origin_id is None:
                return legacy[0]
            raise ValueError(
                f"origin {origin_id} resolves to {len(matches)} connections; "
                "register one exact origin binding"
            )
        matches = [item for item in values if not eda or item.eda == eda]
        if len(matches) != 1:
            target = eda or "requested EDA"
            raise ValueError(
                f"{target} resolves to {len(matches)} connections; provide a captured context "
                "with connection_id or select one connection"
            )
        return matches[0]

    def _write(self, values: list[ConnectionSpec]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "connections": [
                item.to_dict() for item in sorted(values, key=lambda x: x.connection_id)
            ],
        }
        handle, temporary = tempfile.mkstemp(
            prefix="connections-", suffix=".json", dir=self.path.parent
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2, sort_keys=True)
                stream.write("\n")
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
