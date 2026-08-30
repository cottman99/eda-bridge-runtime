"""Independent validation helpers for packaged bootstrap experience libraries.

Vendor adapters do not import this module during execution.  It exists so a
release, Skill, or future memory manager can verify the advisory asset bundle
without coupling Bridge availability to experience quality.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPERIENCE_ASSET_SCHEMA = "eda.experience-asset/v1"
EXPERIENCE_LIBRARY_SCHEMA = "eda.experience-library/v1"
EXPERIENCE_KINDS = {"intuition", "action_pattern", "workflow", "anti_pattern"}
EXPERIENCE_STATUSES = {"candidate", "validated", "preferred", "deprecated"}

_REQUIRED_FIELDS = {
    "schema_version",
    "asset_version",
    "id",
    "kind",
    "status",
    "summary",
    "intents",
    "tags",
    "applies_to",
    "prerequisites",
    "recommendation",
    "steps",
    "failure_signals",
    "validation",
    "official_refs",
    "evidence_refs",
    "confidence",
    "last_verified",
    "supersedes",
}

_SHORTCUT_FIELDS = {
    "implements_asset_id",
    "asset_version",
    "asset_schema_version",
    "asset_content_hash",
    "implementation_version",
    "applies_to",
    "effect_class",
    "parameter_schema",
    "validation",
    "fallback",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_experience_asset(path: Path) -> tuple[dict[str, Any], str]:
    """Parse the deliberately small, JSON-compatible YAML frontmatter subset."""

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError(f"experience asset lacks YAML frontmatter: {path}")
    frontmatter, body = text[4:].split("\n---\n", 1)
    metadata: dict[str, Any] = {}
    for line_number, line in enumerate(frontmatter.splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, raw = line.partition(":")
        if not separator or not key.strip() or not raw.strip():
            raise ValueError(f"invalid frontmatter line {line_number}: {path}")
        key = key.strip()
        if key in metadata:
            raise ValueError(f"duplicate frontmatter field {key}: {path}")
        try:
            metadata[key] = json.loads(raw.strip())
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"frontmatter values must use the JSON-compatible YAML subset: {path}:{line_number}"
            ) from exc
    return metadata, body


def validate_experience_asset(metadata: dict[str, Any], *, body: str) -> None:
    missing = sorted(_REQUIRED_FIELDS - set(metadata))
    unknown = sorted(set(metadata) - _REQUIRED_FIELDS)
    if missing or unknown:
        raise ValueError(f"experience asset fields missing={missing} unknown={unknown}")
    if metadata["kind"] not in EXPERIENCE_KINDS:
        raise ValueError("unsupported experience asset kind")
    if metadata["status"] not in EXPERIENCE_STATUSES:
        raise ValueError("unsupported experience asset status")
    if metadata["schema_version"] != EXPERIENCE_ASSET_SCHEMA:
        raise ValueError("unsupported experience asset schema")
    if not isinstance(metadata["asset_version"], str) or not metadata["asset_version"]:
        raise ValueError("experience asset version must be non-empty")
    if not isinstance(metadata["id"], str) or not metadata["id"]:
        raise ValueError("experience asset id must be non-empty")
    for name in (
        "intents",
        "tags",
        "prerequisites",
        "steps",
        "failure_signals",
        "official_refs",
        "evidence_refs",
        "supersedes",
    ):
        if not isinstance(metadata[name], list) or not all(
            isinstance(item, str) for item in metadata[name]
        ):
            raise ValueError(f"experience asset {name} must be a string list")
    if not isinstance(metadata["applies_to"], dict):
        raise ValueError("experience asset applies_to must be an object")
    if not isinstance(metadata["validation"], dict):
        raise ValueError("experience asset validation must be an object")
    if not isinstance(metadata["confidence"], (int, float)) or not 0 <= metadata["confidence"] <= 1:
        raise ValueError("experience asset confidence must be between zero and one")
    if not isinstance(metadata["last_verified"], str) or len(metadata["last_verified"]) != 10:
        raise ValueError("experience asset last_verified must be an ISO date")
    if not isinstance(metadata["summary"], str) or not isinstance(metadata["recommendation"], str):
        raise ValueError("experience asset summary and recommendation must be strings")
    if not body.strip():
        raise ValueError("experience asset body must explain its evidence boundary")


def validate_experience_library(root: Path) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != EXPERIENCE_LIBRARY_SCHEMA:
        raise ValueError("unsupported experience library schema")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("experience library must list at least one asset")
    seen: set[str] = set()
    for entry in assets:
        if set(entry) != {"id", "path", "sha256", "kind", "status", "summary"}:
            raise ValueError("experience manifest entry has an invalid shape")
        asset_path = (root / entry["path"]).resolve()
        if root.resolve() not in asset_path.parents:
            raise ValueError("experience asset escapes its library root")
        metadata, body = parse_experience_asset(asset_path)
        validate_experience_asset(metadata, body=body)
        if metadata["id"] in seen or entry["id"] != metadata["id"]:
            raise ValueError("experience manifest contains a duplicate or mismatched id")
        seen.add(metadata["id"])
        for field in ("kind", "status", "summary"):
            if entry[field] != metadata[field]:
                raise ValueError(f"experience manifest {field} does not match asset")
        if entry["sha256"] != sha256_file(asset_path):
            raise ValueError("experience asset hash does not match manifest")
    return manifest


def validate_compiled_shortcut_binding(
    binding: dict[str, Any],
    *,
    library_root: Path,
    eda: str,
    version: str,
    profile: str,
) -> dict[str, Any]:
    """Verify that a shortcut is a current compiled form of one packaged asset."""

    if set(binding) != _SHORTCUT_FIELDS:
        raise ValueError("compiled shortcut binding has an invalid shape")
    manifest = validate_experience_library(library_root)
    entry = next(
        (item for item in manifest["assets"] if item["id"] == binding["implements_asset_id"]),
        None,
    )
    if entry is None:
        raise ValueError("compiled shortcut asset is missing")
    metadata, body = parse_experience_asset(library_root / entry["path"])
    validate_experience_asset(metadata, body=body)
    if metadata["status"] not in {"validated", "preferred"}:
        raise ValueError("compiled shortcut asset is not eligible")
    expected = {
        "asset_version": metadata["asset_version"],
        "asset_schema_version": metadata["schema_version"],
        "asset_content_hash": entry["sha256"],
    }
    for field, value in expected.items():
        if binding[field] != value:
            raise ValueError(f"compiled shortcut {field} does not match its asset")
    if binding["applies_to"] != metadata["applies_to"]:
        raise ValueError("compiled shortcut applicability does not match its asset")
    applies_to = metadata["applies_to"]
    if applies_to.get("eda") not in {eda, "*"}:
        raise ValueError("compiled shortcut does not apply to this EDA")
    for field, selected in (("versions", version), ("profiles", profile)):
        allowed = applies_to.get(field, ["*"])
        if not isinstance(allowed, list) or selected not in allowed and "*" not in allowed:
            raise ValueError(f"compiled shortcut does not apply to selected {field}")
    if binding["effect_class"] not in {"observe", "mutation", "job"}:
        raise ValueError("compiled shortcut effect class is invalid")
    if not isinstance(binding["parameter_schema"], dict) or not isinstance(
        binding["validation"], dict
    ):
        raise ValueError("compiled shortcut schemas must be objects")
    if binding["fallback"] != "governed_native_execution":
        raise ValueError("compiled shortcut must preserve governed native execution fallback")
    if (
        not isinstance(binding["implementation_version"], str)
        or not binding["implementation_version"]
    ):
        raise ValueError("compiled shortcut implementation version must be non-empty")
    return metadata


def list_experience_assets(
    root: Path,
    *,
    intents: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Return a compact advisory index; failure never affects EDA execution."""

    try:
        manifest = validate_experience_library(root)
        requested = {item.casefold() for item in (intents or []) + (tags or [])}
        matches = []
        for entry in manifest["assets"]:
            metadata, _body = parse_experience_asset(root / entry["path"])
            terms = {str(item).casefold() for item in metadata["intents"] + metadata["tags"]}
            if requested and not requested.intersection(terms):
                continue
            matches.append(
                {
                    "id": entry["id"],
                    "kind": entry["kind"],
                    "status": entry["status"],
                    "summary": entry["summary"],
                    "asset_version": metadata["asset_version"],
                    "sha256": entry["sha256"],
                    "applies_to": metadata["applies_to"],
                    "confidence": metadata["confidence"],
                    "last_verified": metadata["last_verified"],
                }
            )
        return {
            "status": "ready",
            "schema_version": manifest["schema_version"],
            "provider": manifest.get("provider"),
            "assets": matches,
        }
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "degraded",
            "schema_version": EXPERIENCE_LIBRARY_SCHEMA,
            "assets": [],
            "reason": str(exc),
        }


def get_experience_asset(root: Path, asset_id: str, *, max_chars: int = 8000) -> dict[str, Any]:
    if max_chars < 1 or max_chars > 20000:
        raise ValueError("experience max_chars must be between 1 and 20000")
    manifest = validate_experience_library(root)
    entry = next((item for item in manifest["assets"] if item["id"] == asset_id), None)
    if entry is None:
        raise ValueError("unknown experience asset")
    metadata, body = parse_experience_asset(root / entry["path"])
    return {
        "status": "ready",
        "schema_version": manifest["schema_version"],
        "asset": metadata,
        "sha256": entry["sha256"],
        "body": body[:max_chars],
        "truncated": len(body) > max_chars,
    }
