"""Transport-independent failure facts. Error messages are not capability policy."""

from __future__ import annotations

from typing import Any


class ExecutionError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        phase: str = "execution",
        evidence: dict[str, Any] | None = None,
        uncertain: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.phase = phase
        self.evidence = evidence or {}
        self.uncertain = uncertain

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "phase": self.phase,
            "evidence": self.evidence,
            "execution_uncertain": self.uncertain,
        }


def error_facts(exc: Exception, *, phase: str = "execution") -> dict[str, Any]:
    if isinstance(exc, ExecutionError):
        return exc.to_dict()
    if isinstance(exc, ModuleNotFoundError):
        code = "dependency_missing"
        phase = "environment"
    elif isinstance(exc, PermissionError):
        code = "access_denied"
    elif isinstance(exc, (ValueError, TypeError)):
        code = "invalid_request"
    elif isinstance(exc, FileNotFoundError):
        code = "source_missing"
    elif isinstance(exc, TimeoutError):
        code = "execution_uncertain"
    else:
        code = "execution_failed"
    return {
        "code": code,
        "message": str(exc),
        "phase": phase,
        "exception_type": type(exc).__name__,
        "execution_uncertain": isinstance(exc, TimeoutError),
    }
