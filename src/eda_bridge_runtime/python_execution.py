"""Standard-library-only native Python execution, also shipped to embedded runners.

This module has no vendor imports and no reduced builtins. It is not a sandbox.
The caller owns target admission, environment selection and lifecycle.
"""

from __future__ import annotations

import hashlib
import io
import json
from typing import Any

from .errors import ExecutionError


class BoundedTextIO(io.StringIO):
    """Bound diagnostic capture inside a live GUI without replacing its process."""

    def __init__(self, limit: int):
        super().__init__()
        self.limit = limit
        self.used = 0

    def write(self, value: str) -> int:
        size = len(value.encode("utf-8"))
        if self.used + size > self.limit:
            raise ExecutionError("output_limit", "Program diagnostic output exceeded its bound")
        self.used += size
        return super().write(value)


def execute_python(
    program: dict[str, str],
    api: Any,
    context: dict[str, Any],
    *,
    entrypoint: str = "run",
    max_output_bytes: int = 65536,
) -> dict[str, Any]:
    source = program["source"]
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if program.get("sha256") is not None and program["sha256"] != digest:
        raise ValueError("program.sha256 does not match source")
    namespace: dict[str, Any] = {"__name__": "__eda_program__"}
    exec(compile(source, "<eda-native-program>", "exec"), namespace, namespace)
    function = namespace.get(entrypoint)
    if not callable(function):
        raise ValueError(f"Program must define callable {entrypoint}(api, context)")
    result = function(api, dict(context))
    if not isinstance(result, dict):
        raise TypeError(f"{entrypoint} must return a JSON object")
    encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False).encode(
        "utf-8"
    )
    if len(encoded) > max_output_bytes:
        raise ValueError("Program result exceeds max_output_bytes")
    return result
