import json
from pathlib import Path

import pytest

from eda_bridge_runtime.experience_library import (
    get_experience_asset,
    list_experience_assets,
    sha256_file,
    validate_experience_library,
)


def _asset() -> str:
    fields = {
        "schema_version": "eda.experience-asset/v1",
        "asset_version": "1.0.0",
        "id": "example.inspect",
        "kind": "action_pattern",
        "status": "validated",
        "summary": "Inspect one exact target through its official API.",
        "intents": ["inspect target"],
        "tags": ["official-api"],
        "applies_to": {"eda": "example", "versions": ["1"]},
        "prerequisites": ["exact context"],
        "recommendation": "Read first and keep the scope bounded.",
        "steps": ["resolve context", "read official state"],
        "failure_signals": ["target identity mismatch"],
        "validation": {"method": "readback", "status": "passed"},
        "official_refs": ["https://example.invalid/official"],
        "evidence_refs": ["docs/acceptance.md"],
        "confidence": 0.9,
        "last_verified": "2026-08-31",
        "supersedes": [],
    }
    lines = ["---", *(f"{key}: {json.dumps(value)}" for key, value in fields.items()), "---"]
    return "\n".join(lines) + "\n\n# Evidence boundary\n\nExample only.\n"


def test_validates_hashed_independent_experience_library(tmp_path: Path):
    asset_path = tmp_path / "action_patterns" / "inspect.md"
    asset_path.parent.mkdir()
    content = _asset()
    asset_path.write_text(content, encoding="utf-8")
    digest = sha256_file(asset_path)
    manifest = {
        "schema_version": "eda.experience-library/v1",
        "provider": "example",
        "assets": [
            {
                "id": "example.inspect",
                "path": "action_patterns/inspect.md",
                "sha256": digest,
                "kind": "action_pattern",
                "status": "validated",
                "summary": "Inspect one exact target through its official API.",
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    assert validate_experience_library(tmp_path)["provider"] == "example"


def test_rejects_drifted_experience_asset(tmp_path: Path):
    asset_path = tmp_path / "action_patterns" / "inspect.md"
    asset_path.parent.mkdir()
    asset_path.write_text(_asset(), encoding="utf-8")
    manifest = {
        "schema_version": "eda.experience-library/v1",
        "provider": "example",
        "assets": [
            {
                "id": "example.inspect",
                "path": "action_patterns/inspect.md",
                "sha256": "0" * 64,
                "kind": "action_pattern",
                "status": "validated",
                "summary": "Inspect one exact target through its official API.",
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="hash"):
        validate_experience_library(tmp_path)


def test_compiled_shortcut_must_match_eligible_asset(tmp_path: Path):
    from eda_bridge_runtime.experience_library import validate_compiled_shortcut_binding

    asset_path = tmp_path / "action_patterns" / "inspect.md"
    asset_path.parent.mkdir()
    content = _asset()
    asset_path.write_text(content, encoding="utf-8")
    digest = sha256_file(asset_path)
    manifest = {
        "schema_version": "eda.experience-library/v1",
        "provider": "example",
        "assets": [
            {
                "id": "example.inspect",
                "path": "action_patterns/inspect.md",
                "sha256": digest,
                "kind": "action_pattern",
                "status": "validated",
                "summary": "Inspect one exact target through its official API.",
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    binding = {
        "implements_asset_id": "example.inspect",
        "asset_version": "1.0.0",
        "asset_schema_version": "eda.experience-asset/v1",
        "asset_content_hash": digest,
        "implementation_version": "example-1",
        "applies_to": {"eda": "example", "versions": ["1"]},
        "effect_class": "observe",
        "parameter_schema": {"type": "object"},
        "validation": {"method": "readback"},
        "fallback": "governed_native_execution",
    }

    assert (
        validate_compiled_shortcut_binding(
            binding, library_root=tmp_path, eda="example", version="1", profile="de"
        )["id"]
        == "example.inspect"
    )

    listed = list_experience_assets(tmp_path, tags=["official-api"])
    assert [item["id"] for item in listed["assets"]] == ["example.inspect"]
    assert get_experience_asset(tmp_path, "example.inspect")["sha256"] == digest


def test_missing_library_degrades_advice_without_raising(tmp_path: Path):
    assert list_experience_assets(tmp_path)["status"] == "degraded"
