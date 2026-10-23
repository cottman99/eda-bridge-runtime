"""Bounded source-only SDK inspection: never import modules or evaluate getters."""

from __future__ import annotations

import ast
import hashlib
import time
from pathlib import Path


def describe_symbols(roots, query: str, *, version=None, limit: int = 6):
    if not query.strip() or not 1 <= limit <= 20:
        raise ValueError("A symbol query and a limit between 1 and 20 are required")
    needle = query.strip().casefold()
    results, seen = [], set()
    scanned = 0
    deadline = time.monotonic() + 5
    truncated = False
    for root in (Path(value).resolve() for value in roots):
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".pyi"} or path in seen:
                continue
            seen.add(path)
            scanned += 1
            if scanned > 2000 or time.monotonic() >= deadline:
                truncated = True
                break
            try:
                if path.stat().st_size > 1_048_576:
                    continue
                raw = path.read_text(encoding="utf-8", errors="replace")
                if needle not in raw.casefold():
                    continue
                tree = ast.parse(raw)
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if needle not in node.name.casefold():
                    continue
                signature = (
                    f"class {node.name}"
                    if isinstance(node, ast.ClassDef)
                    else f"def {node.name}({ast.unparse(node.args)})"
                )
                results.append(
                    {
                        "name": node.name,
                        "signature": signature,
                        "docstring": (ast.get_docstring(node) or "")[:4000],
                        "source_ref": str(path),
                        "line": node.lineno,
                        "source_kind": "sdk_source",
                        "version": version,
                        "source_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                        "runtime_verified": False,
                    }
                )
                if len(results) >= limit:
                    truncated = True
                    break
            if truncated:
                break
        if truncated:
            break
    return {
        "status": "partial" if truncated else "ready" if seen else "source_missing",
        "results": results,
        "scanned_files": min(scanned, 2000),
        "execution_available": True,
    }
