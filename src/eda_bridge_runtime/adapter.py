"""Minimal adapter SDK. Vendor semantics stay outside the runtime core."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .protocol import RequestEnvelope


@dataclass(frozen=True)
class AdapterResult:
    status: str
    result: dict[str, Any] = field(default_factory=dict)
    artifacts: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class AdapterContext:
    emit: Callable[[str, dict[str, Any]], None]
    fencing_token: int | None = None


class Adapter(ABC):
    name: str
    version: str

    @abstractmethod
    def capabilities(self) -> dict[str, Any]:
        """Return typed operations and explicit escape lanes."""

    @abstractmethod
    def execute(self, request: RequestEnvelope, context: AdapterContext) -> AdapterResult:
        """Execute one idempotent request and return normalized evidence."""
