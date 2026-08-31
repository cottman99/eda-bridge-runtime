"""Vendor-neutral envelope for bounded edits in an existing graphical EDA session."""

from __future__ import annotations

import re
from typing import Any

LIVE_EDIT_SCHEMA = "eda.live-edit/v1"

_PATCH_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,79}")
_MAX_OPERATIONS = 32


def validate_live_edit(value: Any) -> dict[str, Any]:
    """Validate common live-edit mechanics without encoding vendor operations.

    Exact Context/session authorization remains in the vendor Bridge. Each
    vendor also validates the operation objects and performs the real readback.
    """

    if not isinstance(value, dict):
        raise TypeError("live edit must be an object")
    unknown = sorted(
        set(value)
        - {
            "schema_version",
            "patch_id",
            "expected_revision",
            "operations",
            "conflict_policy",
            "validation",
        }
    )
    if unknown:
        raise ValueError("live edit contains unsupported fields: " + ", ".join(unknown))
    if value.get("schema_version") != LIVE_EDIT_SCHEMA:
        raise ValueError(f"unsupported live edit schema: {value.get('schema_version')}")

    patch_id = str(value.get("patch_id") or "")
    if not _PATCH_ID.fullmatch(patch_id):
        raise ValueError("patch_id must be a bounded identifier")

    revision = value.get("expected_revision")
    if revision is not None and (
        not isinstance(revision, str) or not revision or len(revision) > 256
    ):
        raise ValueError("expected_revision must be null or a bounded string")

    conflict_policy = str(value.get("conflict_policy") or "fail_on_change")
    if conflict_policy != "fail_on_change":
        raise ValueError("live edits support only fail_on_change conflict policy")
    validation = str(value.get("validation") or "readback")
    if validation != "readback":
        raise ValueError("live edits require readback validation")

    operations = value.get("operations")
    if not isinstance(operations, list) or not operations or len(operations) > _MAX_OPERATIONS:
        raise ValueError(f"live edit requires 1..{_MAX_OPERATIONS} operations")
    normalized_operations: list[dict[str, Any]] = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise TypeError(f"operations[{index}] must be an object")
        op = str(operation.get("op") or "")
        if not op or len(op) > 128:
            raise ValueError(f"operations[{index}].op must be a bounded identifier")
        normalized_operations.append(dict(operation))

    return {
        "schema_version": LIVE_EDIT_SCHEMA,
        "patch_id": patch_id,
        "expected_revision": revision,
        "operations": normalized_operations,
        "conflict_policy": conflict_policy,
        "validation": validation,
    }
