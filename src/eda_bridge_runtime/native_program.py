"""Vendor-neutral contract for governed official EDA programs."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from typing import Any

NATIVE_PROGRAM_SCHEMA = "eda.native-program/v1"
OPERATION_CLASSES = frozenset(
    {
        "bridge-infrastructure",
        "generic-native-execution",
        "certified-workflow",
        "acceptance-probe",
        "typed-live-edit",
    }
)

_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,127}")
_SHA256 = re.compile(r"[a-f0-9]{64}")
_MAX_PROGRAM_BYTES = 131_072
_MAX_PATHS = 64
_MAX_ARTIFACTS = 64


def native_program_capability_contract() -> dict[str, Any]:
    """Return the exact public shape an Agent needs before its first submission.

    This is deliberately compact rather than a second validation path.  The
    validator below remains authoritative; adapters embed this description in
    their existing ``native.execute`` capability so an Agent does not have to
    discover required fields by submitting invalid mutations.
    """

    program = {
        "required": ["language", "source"],
        "optional": ["sha256"],
        "allowed_fields": ["language", "source", "sha256"],
        "source_must_define": "def run(api, context)",
        "do_not_submit_fields": ["entrypoint"],
    }
    return {
        "schema_version": NATIVE_PROGRAM_SCHEMA,
        "required": [
            "schema_version",
            "runtime",
            "mode",
            "effect",
            "program",
            "scope",
            "transaction",
            "validation",
            "limits",
        ],
        "optional": ["program_id"],
        "effect": ["observe", "mutate"],
        "mode": ["live", "background", "offline"],
        "program": program,
        "scope": {
            "required": [
                "resource_kind",
                "selectors",
                "read_paths",
                "write_paths",
                "artifacts",
            ]
        },
        "transaction": {
            "required": [
                "strategy",
                "source_fingerprints",
                "fresh_reopen",
                "promotion",
            ],
            "observe": {
                "strategy": "none",
                "source_fingerprints": {},
                "fresh_reopen": False,
                "promotion": "none",
            },
            "mutate": {
                "strategy": "adapter_staging",
                "source_fingerprints": "one SHA-256 per declared source read path",
                "fresh_reopen": True,
                "promotion": "on_validation",
            },
            "live_mutate": {
                "strategy": "none or vendor_transaction when implemented by the backend",
                "source_fingerprints": {},
                "fresh_reopen": False,
                "promotion": "none",
            },
        },
        "validation": {
            "required": ["program", "required_artifacts"],
            "observe_program": None,
            "mutate_program": {
                **program,
                "source_must_define": "def validate(api, context)",
            },
        },
        "limits": {
            "required": ["timeout_seconds", "max_output_bytes"],
            "timeout_seconds": [1, 86_400],
            "max_output_bytes": [1_024, 16_777_216],
        },
    }


def validate_operation_class(value: Any) -> str:
    operation_class = str(value or "")
    if operation_class not in OPERATION_CLASSES:
        raise ValueError("unsupported operation_class")
    return operation_class


def validate_python_program(source: str) -> None:
    """Validate syntax only. SDK availability and host policy are separate facts."""
    try:
        ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"official Python program has invalid syntax: {exc.msg}") from exc


def _exact_object(value: Any, *, name: str, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be an object")
    unknown = sorted(set(value) - fields)
    if unknown:
        raise ValueError(f"{name} contains unsupported fields: " + ", ".join(unknown))
    return dict(value)


def _program(value: Any, *, name: str, entrypoint: str) -> dict[str, str]:
    program = _exact_object(value, name=name, fields={"language", "source", "sha256"})
    language = str(program.get("language") or "")
    source = program.get("source")
    if not _IDENTIFIER.fullmatch(language):
        raise ValueError(f"{name}.language must be a bounded identifier")
    if not isinstance(source, str) or not source.strip():
        raise ValueError(f"{name}.source must contain official-language code")
    encoded = source.encode("utf-8")
    if len(encoded) > _MAX_PROGRAM_BYTES:
        raise ValueError(f"{name}.source exceeds {_MAX_PROGRAM_BYTES} UTF-8 bytes")
    if "\x00" in source:
        raise ValueError(f"{name}.source contains a null byte")
    actual = hashlib.sha256(encoded).hexdigest()
    if "sha256" in program and (
        not isinstance(program["sha256"], str)
        or not _SHA256.fullmatch(program["sha256"])
        or program["sha256"] != actual
    ):
        raise ValueError(f"{name}.sha256 does not match source")
    if language == "python" and not re.search(rf"^def {entrypoint}\s*\(", source, re.MULTILINE):
        raise ValueError(f"{name}.source must define {entrypoint}(...)")
    if language == "python":
        validate_python_program(source)
    return {"language": language, "source": source, "sha256": actual}


def _derive_program_id(plan: dict[str, Any]) -> str:
    material = {key: value for key, value in plan.items() if key != "program_id"}
    material["program"] = {key: value for key, value in plan["program"].items() if key != "sha256"}
    validation = dict(plan["validation"])
    if validation["program"] is not None:
        validation["program"] = {
            key: value for key, value in validation["program"].items() if key != "sha256"
        }
    material["validation"] = validation
    canonical = json.dumps(
        material,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "program-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _paths(value: Any, *, name: str) -> list[str]:
    if not isinstance(value, list) or len(value) > _MAX_PATHS:
        raise ValueError(f"{name} must be a list with at most {_MAX_PATHS} entries")
    normalized = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 4096 or "\x00" in item:
            raise ValueError(f"{name} contains an invalid path")
        normalized.append(item)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{name} contains duplicates")
    return normalized


def _artifacts(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) > _MAX_ARTIFACTS:
        raise ValueError(f"scope.artifacts must contain at most {_MAX_ARTIFACTS} entries")
    normalized = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 512 or "\x00" in item:
            raise ValueError("scope.artifacts contains an invalid entry")
        candidate = item.replace("\\", "/")
        parts = candidate.split("/")
        if (
            candidate.startswith("/")
            or ":" in parts[0]
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise ValueError("scope.artifacts entries must be normalized relative paths")
        normalized.append(candidate)
    if len(set(normalized)) != len(normalized):
        raise ValueError("scope.artifacts contains duplicates")
    return normalized


def validate_native_program(value: Any) -> dict[str, Any]:
    """Validate and normalize one generic official-runtime program envelope."""

    plan = _exact_object(
        value,
        name="native program",
        fields={
            "schema_version",
            "program_id",
            "runtime",
            "mode",
            "effect",
            "program",
            "scope",
            "transaction",
            "validation",
            "limits",
        },
    )
    required = {
        "schema_version",
        "runtime",
        "mode",
        "effect",
        "program",
        "scope",
        "transaction",
        "validation",
        "limits",
    }
    missing = sorted(name for name in required if name not in plan)
    if missing:
        raise ValueError("native program is missing: " + ", ".join(missing))
    if plan["schema_version"] != NATIVE_PROGRAM_SCHEMA:
        raise ValueError(f"unsupported native program schema: {plan['schema_version']}")
    if "program_id" in plan and not _IDENTIFIER.fullmatch(str(plan["program_id"])):
        raise ValueError("program_id must be a bounded identifier")
    if not _IDENTIFIER.fullmatch(str(plan["runtime"])):
        raise ValueError("runtime must be a bounded identifier")
    effect = str(plan["effect"])
    mode = str(plan["mode"])
    if mode not in {"live", "background", "offline"}:
        raise ValueError("mode must be live, background, or offline")
    if effect not in {"observe", "mutate"}:
        raise ValueError("effect must be observe or mutate")
    program = _program(plan["program"], name="program", entrypoint="run")

    scope = _exact_object(
        plan["scope"],
        name="scope",
        fields={"resource_kind", "selectors", "read_paths", "write_paths", "artifacts"},
    )
    if set(scope) != {"resource_kind", "selectors", "read_paths", "write_paths", "artifacts"}:
        raise ValueError(
            "scope requires resource_kind, selectors, read_paths, write_paths, and artifacts"
        )
    if not _IDENTIFIER.fullmatch(str(scope["resource_kind"])):
        raise ValueError("scope.resource_kind must be a bounded identifier")
    selectors = scope["selectors"]
    if not isinstance(selectors, dict) or len(selectors) > 32:
        raise ValueError("scope.selectors must be an object with at most 32 fields")
    for key, item in selectors.items():
        if not _IDENTIFIER.fullmatch(str(key)) or not isinstance(item, (str, int, float, bool)):
            raise ValueError("scope.selectors must contain bounded scalar fields")
    read_paths = _paths(scope["read_paths"], name="scope.read_paths")
    write_paths = _paths(scope["write_paths"], name="scope.write_paths")
    artifacts = _artifacts(scope["artifacts"])

    transaction = _exact_object(
        plan["transaction"],
        name="transaction",
        fields={"strategy", "source_fingerprints", "fresh_reopen", "promotion"},
    )
    if set(transaction) != {"strategy", "source_fingerprints", "fresh_reopen", "promotion"}:
        raise ValueError(
            "transaction requires strategy, source_fingerprints, fresh_reopen, and promotion"
        )
    strategy = str(transaction["strategy"])
    promotion = str(transaction["promotion"])
    fingerprints = transaction["source_fingerprints"]
    if not isinstance(fingerprints, dict) or len(fingerprints) > _MAX_PATHS:
        raise ValueError("transaction.source_fingerprints must be a bounded object")
    for path, digest in fingerprints.items():
        if path not in read_paths or not _SHA256.fullmatch(str(digest)):
            raise ValueError(
                "source fingerprints must match declared read paths and SHA-256 values"
            )
    fresh_reopen = transaction["fresh_reopen"]
    if not isinstance(fresh_reopen, bool):
        raise ValueError("transaction.fresh_reopen must be boolean")

    validation = _exact_object(
        plan["validation"], name="validation", fields={"program", "required_artifacts"}
    )
    if set(validation) != {"program", "required_artifacts"}:
        raise ValueError("validation requires program and required_artifacts")
    validation_program = validation["program"]
    normalized_validation = (
        None
        if validation_program is None
        else _program(validation_program, name="validation.program", entrypoint="validate")
    )
    required_artifacts = _artifacts(validation["required_artifacts"])
    if any(item not in artifacts for item in required_artifacts):
        raise ValueError("validation.required_artifacts must be declared in scope.artifacts")

    limits = _exact_object(
        plan["limits"], name="limits", fields={"timeout_seconds", "max_output_bytes"}
    )
    if set(limits) != {"timeout_seconds", "max_output_bytes"}:
        raise ValueError("limits requires timeout_seconds and max_output_bytes")
    timeout = limits["timeout_seconds"]
    max_output = limits["max_output_bytes"]
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 86_400:
        raise ValueError("limits.timeout_seconds must be between 1 and 86400")
    if (
        not isinstance(max_output, int)
        or isinstance(max_output, bool)
        or not 1024 <= max_output <= 16_777_216
    ):
        raise ValueError("limits.max_output_bytes must be between 1024 and 16777216")

    if effect == "observe":
        if artifacts:
            raise ValueError("Publishing artifacts requires mutate with declared output paths")
        if write_paths or strategy != "none" or promotion != "none" or fingerprints:
            raise ValueError(
                "observe programs cannot declare writes, staging, promotion, or fingerprints"
            )
    elif mode in {"background", "offline"}:
        if not read_paths or not write_paths:
            raise ValueError("staged mutations require declared read and write paths")
        if strategy != "adapter_staging" or promotion != "on_validation":
            raise ValueError("staged mutations require adapter_staging and on_validation")
        if (
            set(fingerprints) != set(read_paths)
            or not fresh_reopen
            or normalized_validation is None
        ):
            raise ValueError(
                "staged mutations require source fingerprints, fresh reopen, and validation code"
            )
    else:
        if strategy not in {"none", "vendor_transaction"} or promotion != "none":
            raise ValueError(
                "live mutations require an in-session recovery strategy, not promotion"
            )
        if not read_paths or not write_paths or normalized_validation is None:
            raise ValueError("live mutations require declared targets and independent validation")
        if fresh_reopen:
            raise ValueError("live execution cannot promise a fresh reopen of the active session")

    normalized = {
        **plan,
        "effect": effect,
        "mode": mode,
        "program": program,
        "scope": {
            "resource_kind": str(scope["resource_kind"]),
            "selectors": dict(selectors),
            "read_paths": read_paths,
            "write_paths": write_paths,
            "artifacts": artifacts,
        },
        "transaction": {
            "strategy": strategy,
            "source_fingerprints": dict(fingerprints),
            "fresh_reopen": fresh_reopen,
            "promotion": promotion,
        },
        "validation": {
            "program": normalized_validation,
            "required_artifacts": required_artifacts,
        },
        "limits": {"timeout_seconds": timeout, "max_output_bytes": max_output},
    }
    normalized["program_id"] = (
        str(plan["program_id"]) if "program_id" in plan else _derive_program_id(normalized)
    )
    return normalized
