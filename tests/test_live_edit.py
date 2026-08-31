import pytest

from eda_bridge_runtime.live_edit import LIVE_EDIT_SCHEMA, validate_live_edit
from eda_bridge_runtime.native_batch import validate_operation_class


def _patch():
    return {
        "schema_version": LIVE_EDIT_SCHEMA,
        "patch_id": "patch-1",
        "expected_revision": "revision-1",
        "operations": [{"op": "set_parameter", "name": "R1"}],
    }


def test_live_edit_normalizes_common_safety_defaults():
    patch = validate_live_edit(_patch())
    assert patch["conflict_policy"] == "fail_on_change"
    assert patch["validation"] == "readback"
    assert validate_operation_class("typed-live-edit") == "typed-live-edit"


def test_live_edit_rejects_unknown_fields_and_empty_operations():
    patch = _patch()
    patch["unsafe"] = True
    with pytest.raises(ValueError, match="unsupported fields"):
        validate_live_edit(patch)

    patch = _patch()
    patch["operations"] = []
    with pytest.raises(ValueError, match="1..32"):
        validate_live_edit(patch)


def test_live_edit_rejects_non_failing_conflict_policy():
    patch = _patch()
    patch["conflict_policy"] = "last_write_wins"
    with pytest.raises(ValueError, match="fail_on_change"):
        validate_live_edit(patch)
