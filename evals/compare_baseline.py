"""Compare normalized repeated evaluations without treating small samples as hard gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def identity(item: dict[str, Any]) -> tuple[str, str, str, str]:
    return tuple(
        str(item.get(name) or "unknown") for name in ("case_id", "agent", "model", "reasoning")
    )


def delta(current: dict[str, Any], baseline: dict[str, Any], name: str) -> float | None:
    left = current.get(name)
    right = baseline.get(name)
    if not isinstance(left, int | float) or not isinstance(right, int | float):
        return None
    return round(float(left) - float(right), 3)


def compare(
    baseline: dict[str, Any], current: dict[str, Any], *, minimum_trials: int = 3
) -> dict[str, Any]:
    if minimum_trials < 1:
        raise ValueError("minimum_trials must be positive")
    current_summary = (
        current.get("summary") if isinstance(current.get("summary"), dict) else current
    )
    baseline_rows = {
        identity(item): item for item in baseline.get("cases", []) if isinstance(item, dict)
    }
    current_rows = {
        identity(item): item
        for item in current_summary.get("reliability", [])
        if isinstance(item, dict)
    }
    comparisons = []
    for key in sorted(baseline_rows.keys() & current_rows.keys()):
        reference = baseline_rows[key]
        observed = current_rows[key]
        reference_trials = int(reference.get("trials") or 0)
        observed_trials = int(observed.get("trials") or 0)
        if reference_trials < minimum_trials:
            status = "insufficient_reference"
        elif observed_trials < minimum_trials:
            status = "insufficient_current"
        else:
            status = "comparable"
        comparisons.append(
            {
                "case_id": key[0],
                "agent": key[1],
                "model": key[2],
                "reasoning": key[3],
                "status": status,
                "reference_trials": reference_trials,
                "current_trials": observed_trials,
                "pass_rate_delta": delta(observed, reference, "pass_rate"),
                "semantic_pass_rate_delta": delta(observed, reference, "semantic_pass_rate"),
                "wall_budget_pass_rate_delta": delta(observed, reference, "wall_budget_pass_rate"),
                "median_wall_ms_delta": delta(observed, reference, "median_wall_ms"),
                "median_input_tokens_delta": delta(observed, reference, "median_input_tokens"),
            }
        )
    return {
        "schema_version": "eda-runtime.eval-baseline-comparison/v1",
        "minimum_trials": minimum_trials,
        "comparisons": comparisons,
        "missing_current": ["|".join(key) for key in sorted(baseline_rows.keys() - current_rows)],
        "new_current": ["|".join(key) for key in sorted(current_rows.keys() - baseline_rows)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--minimum-trials", type=int, default=3)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    current = json.loads(args.current.read_text(encoding="utf-8"))
    result = compare(baseline, current, minimum_trials=args.minimum_trials)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
