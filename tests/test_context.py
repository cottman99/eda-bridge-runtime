import base64
import json
from dataclasses import replace

import pytest

from eda_bridge_runtime.context import EDAContext, capability_digest, stable_origin_id


def test_context_round_trip_without_secret():
    context = EDAContext(
        eda="example",
        target_kind="design",
        locator={"workspace_id": "safe-id", "design_id": "demo"},
        capabilities_hint=("inspect", "simulate"),
    )
    assert EDAContext.decode(context.encode()) == context
    assert context.encode().startswith("EDA_CONTEXT:v2:")


def test_context_v2_carries_bounded_execution_snapshot():
    capabilities = {"names": ["inspect", "edit"], "digest": "cap-demo"}
    context = EDAContext(
        eda="example",
        target_kind="design",
        locator={"context_id": "ctx-demo"},
        display_name="Demo:Layout1",
        origin={"origin_id": "origin-demo"},
        session={"session_id": "session-demo", "display": ":4.0"},
        target={"project": "Demo", "design": "Layout1"},
        selection={"count": 1, "items": ["Trace1"]},
        capabilities=capabilities,
        freshness={"scope": "live", "generation": 2},
        generation=2,
    )
    decoded = EDAContext.decode(context.encode())
    assert decoded.origin["origin_id"] == "origin-demo"
    assert decoded.session["display"] == ":4.0"
    assert decoded.target["design"] == "Layout1"
    assert decoded.selection["items"] == ["Trace1"]


def test_context_v1_remains_decodable():
    legacy = EDAContext(
        eda="example",
        target_kind="design",
        locator={"id": "1"},
        protocol="eda-context/v1",
    )
    token = legacy.encode()
    assert token.startswith("EDA_CONTEXT:v1:")
    assert EDAContext.decode(token).protocol == "eda-context/v1"


def test_context_v2_is_readable_unicode_json_and_legacy_encoding_still_works():
    context = EDAContext(
        eda="example",
        target_kind="design",
        locator={"context_id": "ctx-demo"},
        display_name="演示工程:Layout1",
        target={"project_name": "演示工程", "design": "Layout1"},
    )
    text = context.encode()
    assert '"project_name": "演示工程"' in text
    assert '"design": "Layout1"' in text
    wrapper = text.removeprefix("EDA_CONTEXT:v2:").strip()
    assert json.loads(wrapper)["payload"]["target"] == context.target
    old_token = "EDA_CONTEXT:v2:" + base64.urlsafe_b64encode(wrapper.encode()).decode().rstrip("=")
    assert EDAContext.decode(old_token) == context
    assert EDAContext.decode("\n" + text + "\n") == context


def test_plain_context_checks_integrity_and_size():
    context = EDAContext(eda="example", target_kind="design", locator={"id": "one"})
    with pytest.raises(ValueError, match="checksum"):
        EDAContext.decode(context.encode().replace('"one"', '"two"'))
    with pytest.raises(ValueError, match="bounded"):
        EDAContext.decode("EDA_CONTEXT:v2:" + " " * 40000 + "{}")


def test_origin_id_is_stable_per_eda(tmp_path):
    first = stable_origin_id("example", root=tmp_path)
    assert stable_origin_id("example", root=tmp_path) == first
    assert stable_origin_id("other", root=tmp_path) != first


def test_capability_digest_is_order_stable():
    assert capability_digest({"b": 2, "a": 1}) == capability_digest({"a": 1, "b": 2})


def test_context_rejects_credentials():
    with pytest.raises(ValueError, match="credentials"):
        EDAContext(eda="example", target_kind="design", locator={"token": "secret"})

    with pytest.raises(ValueError, match="credentials"):
        EDAContext(
            eda="example",
            target_kind="design",
            locator={"id": "1"},
            target={"nested": {"password": "secret"}},
        )


def test_context_detects_tampering():
    token = EDAContext(eda="example", target_kind="design", locator={"id": "1"}).encode()
    altered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(ValueError):
        EDAContext.decode(altered)


def test_generation_can_invalidate_cached_binding():
    initial = EDAContext(eda="example", target_kind="design", locator={"id": "1"})
    refreshed = replace(initial, generation=2)
    assert EDAContext.decode(refreshed.encode()).generation > initial.generation
