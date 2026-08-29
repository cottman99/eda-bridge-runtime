import importlib.util
from pathlib import Path


def load_summary():
    path = Path(__file__).parents[1] / "evals" / "summarize_results.py"
    spec = importlib.util.spec_from_file_location("eval_summary", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def result(agent, *, passed=True, failures=None, trial=1, wall_ms=10, input_tokens=20):
    return {
        "case_id": "l2.ads-session-status",
        "agent": agent,
        "model": "test",
        "reasoning": "medium",
        "trial": trial,
        "passed": passed,
        "failures": failures or [],
        "metrics": {
            "wall_ms": wall_ms,
            "tool_attempts": 2,
            "tool_calls_succeeded": 2 if passed else 0,
            "input_tokens": input_tokens,
            "cached_input_tokens": 5,
            "output_tokens": 4,
            "reasoning_output_tokens": 3,
            "client_transport_ms_total": 2.5,
            "client_transport_ms_largest": 1.5,
            "non_transport_wall_ms": 7.5,
            "client_transport_share_pct": 25.0,
            "total_response_payload_chars": 200,
            "largest_response_payload_chars": 150,
        },
        "final": {"private_target": "must not enter summary"},
    }


def test_summary_is_comparable_and_omits_final_payloads():
    summary = load_summary().summarize([result("codex"), result("pi")])

    assert summary["cross_agent_comparable_cases"] == 1
    assert summary["outcomes"] == {"passed": 2}
    assert "final" not in summary["rows"][0]
    assert summary["rows"][0]["reasoning"] == "medium"
    assert summary["rows"][0]["client_transport_share_pct"] == 25.0
    assert summary["rows"][0]["largest_response_payload_chars"] == 150


def test_summary_separates_auth_from_system_failure():
    summary = load_summary().summarize(
        [result("pi", passed=False, failures=["agent_auth_unavailable"])]
    )

    assert summary["rows"][0]["outcome"] == "agent_auth_unavailable"


def test_summary_reports_repeated_trial_reliability_and_medians():
    summary = load_summary().summarize(
        [
            result("codex", trial=1, wall_ms=10, input_tokens=20),
            result("codex", trial=2, wall_ms=30, input_tokens=40),
            result("codex", trial=3, wall_ms=20, input_tokens=30, passed=False),
        ]
    )

    reliability = summary["reliability"][0]
    assert reliability["trials"] == 3
    assert reliability["passed"] == 2
    assert reliability["pass_rate"] == 0.6667
    assert reliability["semantic_passed"] == 2
    assert reliability["semantic_pass_rate"] == 0.6667
    assert reliability["wall_budget_pass_rate"] == 1.0
    assert reliability["median_wall_ms"] == 20.0
    assert reliability["median_input_tokens"] == 30.0


def test_summary_distinguishes_correct_but_slow_from_functional_failure():
    summary = load_summary().summarize(
        [result("codex", passed=False, failures=["wall_budget_exceeded"])]
    )

    assert summary["rows"][0]["outcome"] == "failed"
    assert summary["rows"][0]["semantic_passed"] is True
    assert summary["reliability"][0]["pass_rate"] == 0.0
    assert summary["reliability"][0]["semantic_pass_rate"] == 1.0
    assert summary["reliability"][0]["wall_budget_pass_rate"] == 0.0
