"""Publish a validated set of new paths, rolling back partial moves on error."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from .errors import ExecutionError


def promote_paths(moves: Sequence[tuple[Path, Path]]) -> None:
    completed = []
    destinations = [target.resolve() for _, target in moves]
    if len(set(destinations)) != len(destinations):
        raise ValueError("Promotion destinations must be distinct")
    for source, target in moves:
        if not source.exists():
            raise FileNotFoundError(source)
        if target.exists():
            raise FileExistsError(target)
        target.parent.mkdir(parents=True, exist_ok=True)
    try:
        for source, target in moves:
            if target.exists():
                raise FileExistsError(target)
            os.rename(source, target)
            completed.append((source, target))
    except BaseException as exc:
        rollback_errors = []
        for source, target in reversed(completed):
            try:
                os.rename(target, source)
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        if rollback_errors:
            raise ExecutionError(
                "execution_uncertain",
                "Partial promotion requires reconciliation",
                uncertain=True,
                evidence={
                    "moves": [(str(a), str(b)) for a, b in completed],
                    "rollback_errors": rollback_errors,
                },
            ) from exc
        raise
