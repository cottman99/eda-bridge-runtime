"""Canonical project resource keys independent of connection aliases."""

from __future__ import annotations

import os
from pathlib import Path

from .protocol import RequestEnvelope


def resource_keys(request: RequestEnvelope) -> tuple[str, ...]:
    eda = str(request.target.get("eda", "unknown"))
    plan = request.payload.get("plan")
    plan = plan if isinstance(plan, dict) else {}
    scope = plan.get("scope") or {}
    paths = set()
    sources = [request.target, request.payload, plan, request.target.get("identity") or {}]
    if request.target.get("context"):
        from .context import EDAContext

        decoded = EDAContext.decode(request.target["context"])
        sources.extend((decoded.target, decoded.target.get("identity") or {}))
    for source in sources:
        for field in (
            "workspace",
            "workspace_path",
            "project",
            "source",
            "output",
            "source_project",
            "output_project",
            "source_workspace",
            "output_workspace",
        ):
            value = source.get(field)
            if isinstance(value, str) and value.strip():
                paths.add(value)
    for field in ("read_paths", "write_paths"):
        paths.update(item for item in scope.get(field, []) if isinstance(item, str))
    if paths:

        def canonical(value: str) -> str:
            path = Path(value).expanduser().resolve()
            if eda == "ansys-electronics-desktop" and path.suffix.lower() == ".aedb":
                path = path.with_suffix(".aedt")
            return os.path.normcase(str(path))

        expanded = set(paths)
        for value in paths:
            for parent in Path(value).expanduser().resolve().parents:
                if (parent / "workspace.json").is_file() or (parent / "workspace.ads").is_file():
                    expanded.add(str(parent))
                    break
        return tuple(sorted({f"{eda}:path:{canonical(p)}" for p in expanded}))
    # Adapters resolve opaque contexts first. Otherwise serialize conservatively.
    return (f"{eda}:unresolved-target",)
