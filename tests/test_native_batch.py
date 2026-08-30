import hashlib
import json
from pathlib import Path

import pytest

from eda_bridge_runtime.native_batch import (
    validate_native_batch,
    validate_operation_class,
    validate_python_program_policy,
)


def _program(entrypoint: str, body: str = "return {'status': 'passed'}") -> dict[str, str]:
    source = f"def {entrypoint}(api, context):\n    {body}\n"
    return {
        "language": "python",
        "source": source,
        "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
    }


def _observe() -> dict:
    return {
        "schema_version": "eda.native-batch/v1",
        "batch_id": "inspect_design",
        "runtime": "ansys.pyaedt",
        "effect": "observe",
        "program": _program("run"),
        "scope": {
            "resource_kind": "aedt-project",
            "selectors": {"design": "Layout1"},
            "read_paths": ["/projects/demo.aedt"],
            "write_paths": [],
            "artifacts": [],
        },
        "transaction": {
            "strategy": "none",
            "source_fingerprints": {},
            "fresh_reopen": False,
            "promotion": "none",
        },
        "validation": {"program": None, "required_artifacts": []},
        "limits": {"timeout_seconds": 60, "max_output_bytes": 65536},
    }


def test_observe_batch_accepts_official_program_without_write_scope():
    plan = validate_native_batch(_observe())
    assert plan["effect"] == "observe"
    assert plan["program"]["language"] == "python"


def test_staged_mutation_requires_independent_validation_and_promotion():
    plan = _observe()
    plan.update(effect="staged_mutation")
    plan["scope"]["write_paths"] = ["/projects/candidate/demo.aedt"]
    plan["scope"]["artifacts"] = ["evidence/result.json"]
    plan["transaction"] = {
        "strategy": "adapter_staging",
        "source_fingerprints": {"/projects/demo.aedt": "a" * 64},
        "fresh_reopen": True,
        "promotion": "on_validation",
    }
    plan["validation"] = {
        "program": _program("validate"),
        "required_artifacts": ["evidence/result.json"],
    }
    validated = validate_native_batch(plan)
    assert validated["transaction"]["promotion"] == "on_validation"


def test_program_hash_is_part_of_the_contract():
    plan = _observe()
    plan["program"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="does not match"):
        validate_native_batch(plan)


def test_observe_batch_rejects_declared_write_scope():
    plan = _observe()
    plan["scope"]["write_paths"] = ["/projects/output.aedt"]
    with pytest.raises(ValueError, match="observe batches cannot"):
        validate_native_batch(plan)


def test_artifacts_are_relative_and_bounded():
    plan = _observe()
    plan["scope"]["artifacts"] = ["../outside.txt"]
    with pytest.raises(ValueError, match="normalized relative"):
        validate_native_batch(plan)


def test_operation_classes_are_fixed_product_roles():
    assert validate_operation_class("generic-native-execution") == "generic-native-execution"
    with pytest.raises(ValueError, match="unsupported"):
        validate_operation_class("plot-wrapper")


def test_public_native_batch_schema_is_valid_json():
    root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (root / "docs" / "schemas" / "native-batch-v1.schema.json").read_text(encoding="utf-8")
    )
    assert schema["properties"]["schema_version"]["const"] == "eda.native-batch/v1"


def test_python_policy_allows_declared_vendor_import_and_rejects_shell_escape():
    validate_python_program_policy(
        "from ansys.aedt.core import Hfss3dLayout\ndef run(api, context):\n    return {}\n",
        allowed_import_prefixes=("ansys.aedt.core", "math"),
    )
    with pytest.raises(ValueError, match="undeclared module"):
        validate_python_program_policy(
            "import subprocess\ndef run(api, context):\n    return {}\n",
            allowed_import_prefixes=("ansys.aedt.core",),
        )
    with pytest.raises(ValueError, match="forbidden builtin"):
        validate_python_program_policy(
            "def run(api, context):\n    return open('outside.txt')\n",
            allowed_import_prefixes=(),
        )
