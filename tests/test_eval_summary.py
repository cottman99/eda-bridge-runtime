import importlib.util
from pathlib import Path


def load_summary():
    path = Path(__file__).parents[1] / "evals" / "summarize_results.py"
    spec = importlib.util.spec_from_file_location("eval_summary", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def result(agent, *, passed=True, failures=None):
    return {
        "case_id": "l2.ads-session-status",
        "agent": agent,
        "model": "test",
        "passed": passed,
        "failures": failures or [],
        "metrics": {
            "wall_ms": 10,
            "tool_attempts": 2,
            "tool_calls_succeeded": 2 if passed else 0,
            "input_tokens": 20,
            "cached_input_tokens": 5,
        },
        "final": {"private_target": "must not enter summary"},
    }


def test_summary_is_comparable_and_omits_final_payloads():
    summary = load_summary().summarize([result("codex"), result("pi")])

    assert summary["cross_agent_comparable_cases"] == 1
    assert summary["outcomes"] == {"passed": 2}
    assert "final" not in summary["rows"][0]


def test_summary_separates_auth_from_system_failure():
    summary = load_summary().summarize(
        [result("pi", passed=False, failures=["agent_auth_unavailable"])]
    )

    assert summary["rows"][0]["outcome"] == "agent_auth_unavailable"
