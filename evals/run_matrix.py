"""Run a bounded cross-Agent evaluation matrix and retain normalized facts only."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_cases(
    case_root: Path,
    *,
    max_level: int,
    approve_mutations: bool,
    approve_solves: bool,
    case_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for path in case_root.glob("*.json"):
        case = json.loads(path.read_text(encoding="utf-8"))
        case["_path"] = path
        if case_ids is not None and str(case["case_id"]) not in case_ids:
            continue
        if case_ids is None and int(case["level"]) > max_level:
            continue
        mutation = str((case.get("safety") or {}).get("mutation") or "forbidden")
        if mutation != "forbidden" and not approve_mutations:
            skipped.append({"case_id": case["case_id"], "reason": "mutation_not_approved"})
            continue
        solve = str((case.get("safety") or {}).get("solve") or "forbidden")
        if solve != "forbidden" and not approve_solves:
            skipped.append({"case_id": case["case_id"], "reason": "solve_not_approved"})
            continue
        selected.append(case)
    selected.sort(key=lambda item: (int(item["level"]), str(item["case_id"])))
    return selected, skipped


def load_summarizer(root: Path):
    path = root / "summarize_results.py"
    spec = importlib.util.spec_from_file_location("eda_eval_summary", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def result_path(
    output_dir: Path, *, case_id: str, agent: str, trial: int, repetitions: int
) -> Path:
    suffix = f"__trial_{trial:02d}" if repetitions > 1 else ""
    return output_dir / f"{case_id.replace('.', '_')}__{agent}{suffix}.json"


def supplied_variable_names(values: list[str]) -> set[str]:
    names: set[str] = set()
    for value in values:
        name, separator, selected = value.partition("=")
        if not separator or not name or not selected:
            raise ValueError("--var values must use NAME=value")
        names.add(name)
    return names


def missing_case_variables(cases: list[dict[str, Any]], supplied: set[str]) -> list[str]:
    required = {str(name) for case in cases for name in case.get("variables", []) if str(name)}
    return sorted(required - supplied)


def matrix_exit_code(results: list[dict[str, Any]]) -> int:
    if not results:
        return 2
    return 0 if all(result.get("passed") is True for result in results) else 1


def execution_schedule(
    cases: list[dict[str, Any]], agents: list[str], repetitions: int
) -> list[tuple[dict[str, Any], int, str]]:
    """Interleave clients without ever running two EDA evaluations concurrently."""
    schedule: list[tuple[dict[str, Any], int, str]] = []
    if not agents:
        return schedule
    for case_index, case in enumerate(cases):
        for trial in range(1, repetitions + 1):
            offset = (case_index + trial - 1) % len(agents)
            ordered_agents = agents[offset:] + agents[:offset]
            schedule.extend((case, trial, agent) for agent in ordered_agents)
    return schedule


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents", nargs="+", choices=("codex", "pi"), default=["codex", "pi"])
    parser.add_argument("--max-level", type=int, default=4)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--approve-mutations", action="store_true")
    parser.add_argument("--approve-solves", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--var", action="append", default=[])
    parser.add_argument("--codex-model", default="gpt-5.5")
    parser.add_argument("--pi-model", default="openai-codex/gpt-5.5")
    parser.add_argument("--thinking", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--codex-profile", default="eda-runtime")
    parser.add_argument("--pi-command", default="pi-eda.cmd")
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 10:
        parser.error("--repetitions must be between 1 and 10")

    eval_root = Path(__file__).resolve().parent
    requested_case_ids = set(args.case_id) if args.case_id else None
    cases, skipped = load_cases(
        eval_root / "cases",
        max_level=args.max_level,
        approve_mutations=args.approve_mutations,
        approve_solves=args.approve_solves,
        case_ids=requested_case_ids,
    )
    if requested_case_ids:
        found_case_ids = {str(case["case_id"]) for case in cases} | {
            str(item["case_id"]) for item in skipped
        }
        missing = sorted(requested_case_ids - found_case_ids)
        if missing:
            parser.error(f"unknown --case-id value(s): {', '.join(missing)}")
    try:
        supplied_names = supplied_variable_names(args.var)
    except ValueError as exc:
        parser.error(str(exc))
    missing_variables = missing_case_variables(cases, supplied_names)
    if missing_variables:
        parser.error(f"missing --var value(s): {', '.join(missing_variables)}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    unavailable_agents: set[str] = set()
    execution_order: list[dict[str, Any]] = []
    for sequence, (case, trial, agent) in enumerate(
        execution_schedule(cases, list(args.agents), args.repetitions), start=1
    ):
        if agent in unavailable_agents:
            skipped.append(
                {
                    "case_id": case["case_id"],
                    "agent": agent,
                    "trial": trial,
                    "reason": "agent_auth_unavailable",
                }
            )
            continue
        execution_order.append(
            {
                "sequence": sequence,
                "case_id": case["case_id"],
                "agent": agent,
                "trial": trial,
            }
        )
        output = result_path(
            args.output_dir,
            case_id=str(case["case_id"]),
            agent=agent,
            trial=trial,
            repetitions=args.repetitions,
        )
        model = args.codex_model if agent == "codex" else args.pi_model
        command = [
            sys.executable,
            str(eval_root / "run_case.py"),
            "--case",
            str(case["_path"]),
            "--agent",
            agent,
            "--model",
            model,
            "--thinking",
            args.thinking,
            "--cwd",
            str(args.cwd),
            "--output",
            str(output),
            "--codex-profile",
            args.codex_profile,
            "--pi-command",
            args.pi_command,
        ]
        for value in args.var:
            command.extend(["--var", value])
        mutation = str((case.get("safety") or {}).get("mutation") or "forbidden")
        if args.approve_mutations and mutation != "forbidden":
            command.append("--approve-mutations")
        solve = str((case.get("safety") or {}).get("solve") or "forbidden")
        if args.approve_solves and solve != "forbidden":
            command.append("--approve-solves")
        completed = subprocess.run(
            command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )  # noqa: S603
        if not output.is_file():
            results.append(
                {
                    "case_id": case["case_id"],
                    "agent": agent,
                    "model": model,
                    "reasoning": args.thinking,
                    "trial": trial,
                    "sequence": sequence,
                    "passed": False,
                    "failures": [
                        "runner_did_not_write_result",
                        f"runner_exit_code:{completed.returncode}",
                    ],
                    "metrics": {},
                }
            )
            continue
        result = json.loads(output.read_text(encoding="utf-8"))
        result["trial"] = trial
        result["sequence"] = sequence
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        results.append(result)
        if "agent_auth_unavailable" in result.get("failures", []):
            unavailable_agents.add(agent)

    summary = load_summarizer(eval_root).summarize(results)
    report = {
        "schema_version": "eda-runtime.eval-matrix/v1",
        "summary": summary,
        "execution_order": execution_order,
        "skipped": skipped,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (args.output_dir / "matrix-summary.json").write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return matrix_exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
