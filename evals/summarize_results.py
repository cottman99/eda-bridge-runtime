"""Aggregate normalized EDA evaluation results without loading raw Agent traces."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_LEVEL = re.compile(r"^l(?P<level>\d+)\.(?P<domain>[^.]+)")


def outcome(result: dict[str, Any]) -> str:
    if result.get("passed") is True:
        return "passed"
    failures = set(result.get("failures") or [])
    if "agent_auth_unavailable" in failures:
        return "agent_auth_unavailable"
    if "runtime_mcp_unavailable" in failures:
        return "runtime_unavailable"
    return "failed"


def row(result: dict[str, Any]) -> dict[str, Any]:
    case_id = str(result.get("case_id") or "unknown")
    match = _LEVEL.match(case_id)
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    return {
        "case_id": case_id,
        "level": int(match.group("level")) if match else None,
        "domain": match.group("domain") if match else "unknown",
        "agent": str(result.get("agent") or "unknown"),
        "model": str(result.get("model") or "unknown"),
        "reasoning": str(result.get("reasoning") or "unknown"),
        "outcome": outcome(result),
        "wall_ms": metrics.get("wall_ms"),
        "tool_attempts": metrics.get("tool_attempts"),
        "tool_calls_succeeded": metrics.get("tool_calls_succeeded"),
        "input_tokens": metrics.get("input_tokens"),
        "cached_input_tokens": metrics.get("cached_input_tokens"),
        "output_tokens": metrics.get("output_tokens"),
        "reasoning_output_tokens": metrics.get("reasoning_output_tokens"),
        "client_transport_ms_total": metrics.get("client_transport_ms_total"),
        "client_transport_ms_largest": metrics.get("client_transport_ms_largest"),
        "non_transport_wall_ms": metrics.get("non_transport_wall_ms"),
        "client_transport_share_pct": metrics.get("client_transport_share_pct"),
        "total_response_payload_chars": metrics.get("total_response_payload_chars"),
        "largest_response_payload_chars": metrics.get("largest_response_payload_chars"),
        "failures": list(result.get("failures") or []),
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    rows = sorted(
        (row(result) for result in results),
        key=lambda item: (
            item["level"] if isinstance(item["level"], int) else 99,
            item["case_id"],
            item["agent"],
        ),
    )
    outcomes: dict[str, int] = {}
    for item in rows:
        outcomes[item["outcome"]] = outcomes.get(item["outcome"], 0) + 1
    comparable_cases = 0
    grouped: dict[str, set[str]] = {}
    for item in rows:
        if item["outcome"] == "passed":
            grouped.setdefault(item["case_id"], set()).add(item["agent"])
    comparable_cases = sum(len(agents) > 1 for agents in grouped.values())
    return {
        "schema_version": "eda-runtime.eval-summary/v1",
        "result_count": len(rows),
        "outcomes": outcomes,
        "cross_agent_comparable_cases": comparable_cases,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    values = [json.loads(path.read_text(encoding="utf-8")) for path in args.results]
    summary = summarize(values)
    rendered = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
