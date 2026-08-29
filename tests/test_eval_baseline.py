import importlib.util
from pathlib import Path


def load_comparator():
    path = Path(__file__).parents[1] / "evals" / "compare_baseline.py"
    spec = importlib.util.spec_from_file_location("eval_baseline", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def item(*, trials, pass_rate, wall=10):
    return {
        "case_id": "l1.ads-capabilities",
        "agent": "codex",
        "model": "gpt-5.5",
        "reasoning": "low",
        "trials": trials,
        "pass_rate": pass_rate,
        "semantic_pass_rate": pass_rate,
        "wall_budget_pass_rate": 1.0,
        "median_wall_ms": wall,
        "median_input_tokens": 20,
    }


def test_baseline_comparison_requires_enough_trials_and_reports_deltas():
    comparator = load_comparator()
    baseline = {"cases": [item(trials=3, pass_rate=1.0)]}
    current = {"reliability": [item(trials=3, pass_rate=0.6667, wall=15)]}

    result = comparator.compare(baseline, current)

    comparison = result["comparisons"][0]
    assert comparison["status"] == "comparable"
    assert comparison["pass_rate_delta"] == -0.333
    assert comparison["median_wall_ms_delta"] == 5.0


def test_baseline_comparison_labels_small_samples_instead_of_gating_them():
    comparator = load_comparator()
    baseline = {"cases": [item(trials=1, pass_rate=1.0)]}
    current = {"summary": {"reliability": [item(trials=3, pass_rate=1.0)]}}

    result = comparator.compare(baseline, current)

    assert result["comparisons"][0]["status"] == "insufficient_reference"
