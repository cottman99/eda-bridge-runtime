import pytest

from eda_bridge_runtime.protocol import ActorIdentity, RequestEnvelope, ResponseEnvelope


def test_purpose_is_required():
    with pytest.raises(ValueError, match="purpose"):
        RequestEnvelope(purpose=" ", target={"eda": "fake"}, operation="inspect")


def test_mutation_requires_idempotency():
    request = RequestEnvelope(
        purpose="Update one property", target={"eda": "fake"}, operation="set"
    )
    with pytest.raises(ValueError, match="idempotency"):
        request.require_idempotency()


def test_read_only_request_does_not_require_idempotency():
    request = RequestEnvelope(
        purpose="Inspect active design",
        target={"eda": "fake"},
        operation="inspect",
        payload={"mutating": False},
    )
    request.require_idempotency()


def test_actor_unknown_does_not_block(monkeypatch):
    for name in ["CODEX_MODEL", "OPENAI_MODEL", "CODEX_PROVIDER"]:
        monkeypatch.delenv(name, raising=False)
    actor = ActorIdentity.detect()
    assert actor.model.value == "unknown"
    assert actor.model.provenance == "unknown"


def test_response_failed_requires_error():
    with pytest.raises(ValueError, match="requires error"):
        ResponseEnvelope(request_id="r", run_id="x", status="failed")


def test_round_trip_request():
    original = RequestEnvelope(
        purpose="Inspect active design",
        target={"eda": "fake", "design": "demo"},
        operation="inspect",
        payload={"mutating": False},
    )
    restored = RequestEnvelope.from_dict(original.to_dict())
    assert restored == original
