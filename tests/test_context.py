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
