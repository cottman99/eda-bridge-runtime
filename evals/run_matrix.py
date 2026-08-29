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
    case_root: Path, *, max_level: int, approve_mutations: bool
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for path in case_root.glob("*.json"):
        case = json.loads(path.read_text(encoding="utf-8"))
        case["_path"] = path
        if int(case["level"]) > max_level:
            continue
        mutation = str((case.get("safety") or {}).get("mutation") or "forbidden")
        if mutation != "forbidden" and not approve_mutations:
            skipped.append({"case_id": case["case_id"], "reason": "mutation_not_approved"})
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents", nargs="+", choices=("codex", "pi"), default=["codex", "pi"])
    parser.add_argument("--max-level", type=int, default=4)
    parser.add_argument("--approve-mutations", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--var", action="append", default=[])
    parser.add_argument("--codex-model", default="gpt-5.5")
    parser.add_argument("--pi-model", default="openai-codex/gpt-5.5")
    parser.add_argument("--thinking", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--codex-profile", default="eda-runtime")
    parser.add_argument("--pi-command", default="pi-eda.cmd")
    args = parser.parse_args()

    eval_root = Path(__file__).resolve().parent
    cases, skipped = load_cases(
        eval_root / "cases",
        max_level=args.max_level,
        approve_mutations=args.approve_mutations,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    unavailable_agents: set[str] = set()
    for agent in args.agents:
        for case in cases:
            if agent in unavailable_agents:
                skipped.append(
                    {
                        "case_id": case["case_id"],
                        "agent": agent,
                        "reason": "agent_auth_unavailable",
                    }
                )
                continue
            output = args.output_dir / f"{str(case['case_id']).replace('.', '_')}__{agent}.json"
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
            subprocess.run(
                command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )  # noqa: S603
            if not output.is_file():
                results.append(
                    {
                        "case_id": case["case_id"],
                        "agent": agent,
                        "model": model,
                        "reasoning": args.thinking,
                        "passed": False,
                        "failures": ["runner_did_not_write_result"],
                        "metrics": {},
                    }
                )
                continue
            result = json.loads(output.read_text(encoding="utf-8"))
            results.append(result)
            if "agent_auth_unavailable" in result.get("failures", []):
                unavailable_agents.add(agent)

    summary = load_summarizer(eval_root).summarize(results)
    report = {
        "schema_version": "eda-runtime.eval-matrix/v1",
        "summary": summary,
        "skipped": skipped,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (args.output_dir / "matrix-summary.json").write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if all(result.get("passed") is True for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
