"""Bounded retention of completed, Bridge-owned failure staging directories."""

import json
import shutil
import time
from pathlib import Path

_MARKER = ".eda-retained-stage.json"


def retain_stage(path: Path | None, *, uncertain: bool, keep: int = 8, days: int = 7) -> None:
    if path is None or not path.is_dir():
        return
    root = path.resolve()
    (root / _MARKER).write_text(
        json.dumps(
            {
                "schema": "eda.retained-stage/v1",
                "path": str(root),
                "finished_at": time.time(),
                "uncertain": uncertain,
            }
        ),
        encoding="utf-8",
    )
    candidates = []
    for marker in root.parent.glob("*/" + _MARKER):
        directory = marker.parent
        if directory.is_symlink() or directory.resolve().parent != root.parent:
            continue
        try:
            record = json.loads(marker.read_text(encoding="utf-8"))
            if (
                record.get("schema") == "eda.retained-stage/v1"
                and record.get("path") == str(directory.resolve())
                and record.get("uncertain") is False
            ):
                candidates.append((float(record["finished_at"]), directory))
        except (OSError, ValueError, KeyError):
            continue
    for index, (finished, directory) in enumerate(sorted(candidates, reverse=True)):
        if directory == root:
            continue
        if index >= keep or time.time() - finished > days * 86400:
            shutil.rmtree(directory)
