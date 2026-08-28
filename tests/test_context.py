from dataclasses import replace

import pytest

from eda_bridge_runtime.context import EDAContext


def test_context_round_trip_without_secret():
    context = EDAContext(
        eda="example",
        target_kind="design",
        locator={"workspace_id": "safe-id", "design_id": "demo"},
        capabilities_hint=("inspect", "simulate"),
    )
    assert EDAContext.decode(context.encode()) == context


def test_context_rejects_credentials():
    with pytest.raises(ValueError, match="credentials"):
        EDAContext(eda="example", target_kind="design", locator={"token": "secret"})


def test_context_detects_tampering():
    token = EDAContext(eda="example", target_kind="design", locator={"id": "1"}).encode()
    altered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(ValueError):
        EDAContext.decode(altered)


def test_generation_can_invalidate_cached_binding():
    initial = EDAContext(eda="example", target_kind="design", locator={"id": "1"})
    refreshed = replace(initial, generation=2)
    assert EDAContext.decode(refreshed.encode()).generation > initial.generation
