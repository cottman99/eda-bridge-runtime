"""Content-addressed artifact evidence."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Artifact:
    logical_name: str
    path: str
    sha256: str
    size: int
    media_type: str = "application/octet-stream"
    retention_days: int | None = None

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        logical_name: str | None = None,
        media_type: str = "application/octet-stream",
        retention_days: int | None = None,
    ) -> Artifact:
        source = Path(path)
        digest = hashlib.sha256()
        with source.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return cls(
            logical_name or source.name,
            str(source),
            digest.hexdigest(),
            source.stat().st_size,
            media_type,
            retention_days,
        )

    def to_dict(self) -> dict[str, str | int | None]:
        return asdict(self)
