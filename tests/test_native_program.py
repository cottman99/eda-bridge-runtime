import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from eda_bridge_runtime.native_program import (
    native_program_capability_contract,
    validate_native_program,
    validate_operation_class,
    validate_python_program,
)


def test_capability_contract_exposes_complete_first_submission_shape():
    contract = native_program_capability_contract()
    assert contract["schema_version"] == "eda.native-program/v1"
    assert set(contract["required"]) == {
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
    assert contract["program"]["source_must_define"] == "def run(api, context)"
    assert contract["program"]["allowed_fields"] == ["language", "source", "sha256"]
    assert contract["program"]["do_not_submit_fields"] == ["entrypoint"]
    assert contract["validation"]["mutate_program"]["source_must_define"] == (
        "def validate(api, context)"
    )
    assert contract["transaction"]["mutate"] == {
        "strategy": "adapter_staging",
        "source_fingerprints": "one SHA-256 per declared source read path",
        "fresh_reopen": True,
        "promotion": "on_validation",
    }


def _program(entrypoint: str, body: str = "return {'status': 'passed'}") -> dict[str, str]:
    source = f"def {entrypoint}(api, context):\n    {body}\n"
    return {
        "language": "python",
        "source": source,
        "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
    }


def _observe() -> dict:
    return {
        "schema_version": "eda.native-program/v1",
        "mode": "background",
        "program_id": "inspect_design",
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
    plan = validate_native_program(_observe())
    assert plan["effect"] == "observe"
    assert plan["program"]["language"] == "python"


def test_mutate_requires_independent_validation_and_promotion():
    plan = _observe()
    plan.update(effect="mutate")
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
    validated = validate_native_program(plan)
    assert validated["transaction"]["promotion"] == "on_validation"


def test_program_hash_is_part_of_the_contract():
    plan = _observe()
    plan["program"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="does not match"):
        validate_native_program(plan)


def test_runtime_materializes_missing_program_hashes():
    plan = _observe()
    expected = plan["program"].pop("sha256")
    validated = validate_native_program(plan)
    assert validated["program"]["sha256"] == expected

    plan.update(effect="mutate")
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
    validation_expected = plan["validation"]["program"].pop("sha256")
    validated = validate_native_program(plan)
    assert validated["validation"]["program"]["sha256"] == validation_expected


def test_explicit_validation_program_hash_mismatch_fails_closed():
    plan = _observe()
    plan.update(effect="mutate")
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
    plan["validation"]["program"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="validation.program.sha256 does not match source"):
        validate_native_program(plan)


def test_runtime_materializes_stable_program_id_without_logging_source_or_paths(caplog):
    plan = _observe()
    plan["scope"]["selectors"] = {"project": "demo", "design": "Layout1"}
    explicit_hash = plan["program"]["sha256"]
    plan.pop("program_id")
    without_hash = deepcopy(plan)
    without_hash["program"].pop("sha256")
    reordered_material = deepcopy(without_hash)
    reordered_material["scope"] = dict(reversed(list(reordered_material["scope"].items())))
    reordered_material["scope"]["selectors"] = dict(
        reversed(list(reordered_material["scope"]["selectors"].items()))
    )

    first = validate_native_program(plan)
    second = validate_native_program(without_hash)
    reordered = validate_native_program(dict(reversed(list(reordered_material.items()))))

    assert first["program_id"] == second["program_id"] == reordered["program_id"]
    assert first["program_id"].startswith("program-")
    assert len(first["program_id"]) == len("program-") + 64
    assert first["program"]["sha256"] == second["program"]["sha256"] == explicit_hash
    assert "/projects/demo.aedt" not in caplog.text
    assert without_hash["program"]["source"] not in caplog.text


def test_source_line_endings_remain_exact_material_for_hash_and_program_id():
    lf = _observe()
    lf.pop("program_id")
    lf["program"].pop("sha256")
    crlf = deepcopy(lf)
    crlf["program"]["source"] = crlf["program"]["source"].replace("\n", "\r\n")

    lf_validated = validate_native_program(lf)
    crlf_validated = validate_native_program(crlf)
    assert lf_validated["program"]["sha256"] != crlf_validated["program"]["sha256"]
    assert lf_validated["program_id"] != crlf_validated["program_id"]


def test_explicit_program_id_is_preserved_and_still_validated():
    plan = _observe()
    assert validate_native_program(plan)["program_id"] == "inspect_design"
    plan["program_id"] = "invalid id"
    with pytest.raises(ValueError, match="bounded identifier"):
        validate_native_program(plan)


def test_observe_batch_rejects_declared_write_scope():
    plan = _observe()
    plan["scope"]["write_paths"] = ["/projects/output.aedt"]
    with pytest.raises(ValueError, match="observe programs cannot"):
        validate_native_program(plan)


def test_artifacts_are_relative_and_bounded():
    plan = _observe()
    plan["scope"]["artifacts"] = ["../outside.txt"]
    with pytest.raises(ValueError, match="normalized relative"):
        validate_native_program(plan)


def test_observe_cannot_claim_unpublished_artifacts():
    plan = _observe()
    plan["scope"]["artifacts"] = ["result.json"]
    with pytest.raises(ValueError, match="Publishing artifacts requires mutate"):
        validate_native_program(plan)


def test_operation_classes_are_fixed_product_roles():
    assert validate_operation_class("generic-native-execution") == "generic-native-execution"
    with pytest.raises(ValueError, match="unsupported"):
        validate_operation_class("plot-wrapper")


def test_public_native_program_schema_is_valid_json():
    root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (root / "docs" / "schemas" / "native-program-v1.schema.json").read_text(encoding="utf-8")
    )
    assert schema["properties"]["schema_version"]["const"] == "eda.native-program/v1"
    assert "program_id" not in schema["required"]
    assert "sha256" not in schema["$defs"]["program"]["required"]


def test_native_python_uses_normal_imports_and_builtins(tmp_path):
    from eda_bridge_runtime.python_execution import execute_python

    source = (
        "import pathlib, subprocess\ndef run(api, context):\n"
        "    with open(context['path'], 'w') as f:\n        f.write('native')\n"
        "    return {'class': pathlib.Path.__name__, 'module': subprocess.__name__}\n"
    )
    validate_python_program(source)
    target = tmp_path / "result.txt"
    assert execute_python({"source": source}, None, {"path": str(target)}) == {
        "class": "Path",
        "module": "subprocess",
    }
    assert target.read_text() == "native"
    with pytest.raises(ValueError):
        validate_python_program("def run(")
