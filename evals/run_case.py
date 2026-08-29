"""Run and deterministically score one public EDA Runtime evaluation case."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


def canonical_tool(name: str) -> str:
    value = name.removeprefix("mcp__eda_bridge_runtime__")
    if value.startswith("eda_"):
        return value.replace("_", ".", 1).replace("_", ".")
    return value


def json_lines(output: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            values.append(value)
    return values


def tool_fact(tool: str, result: Any) -> dict[str, Any]:
    """Reduce one tool result to non-sensitive execution facts for scoring."""
    result = result if isinstance(result, dict) else {}
    structured = result.get("structured_content") or result.get("structuredContent")
    structured = structured if isinstance(structured, dict) else {}
    run = structured.get("run") if isinstance(structured.get("run"), dict) else {}
    response = structured.get("response") if isinstance(structured.get("response"), dict) else {}
    response_result = response.get("result") if isinstance(response.get("result"), dict) else {}
    response_chars = len(
        json.dumps(response_result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    return {
        "tool": tool,
        "run_id": str(run.get("run_id") or "") or None,
        "job_id": str(run.get("job_id") or "") or None,
        "state": str(run.get("state") or "") or None,
        "deduplicated": response_result.get("deduplicated") is True,
        "response_payload_chars": response_chars,
    }


def runtime_metrics(facts: list[dict[str, Any]]) -> dict[str, int]:
    runs = {fact["run_id"] for fact in facts if fact["run_id"]}
    jobs = {fact["job_id"] for fact in facts if fact["job_id"]}
    seen: set[tuple[str, str]] = set()
    reused_run_calls = 0
    for fact in facts:
        identity = (str(fact["tool"]), str(fact["run_id"] or ""))
        if not identity[1]:
            continue
        if identity in seen:
            reused_run_calls += 1
        seen.add(identity)
    return {
        "deduplicated_calls": sum(fact["deduplicated"] is True for fact in facts),
        "reused_run_calls": reused_run_calls,
        "distinct_projected_runs": len(runs),
        "distinct_jobs": len(jobs),
        "total_response_payload_chars": sum(fact["response_payload_chars"] for fact in facts),
        "largest_response_payload_chars": max(
            (fact["response_payload_chars"] for fact in facts), default=0
        ),
    }


def parse_codex(events: list[dict[str, Any]]) -> dict[str, Any]:
    tools: list[str] = []
    attempts: list[str] = []
    facts: list[dict[str, Any]] = []
    messages = 0
    final_text = ""
    usage = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
    }
    for event in events:
        if event.get("type") == "turn.completed":
            for key in usage:
                usage[key] += int((event.get("usage") or {}).get(key, 0))
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        if event.get("type") == "item.completed" and item.get("type") == "mcp_tool_call":
            tool = canonical_tool(str(item.get("tool") or ""))
            attempts.append(tool)
            if item.get("status") == "completed" and not item.get("error"):
                tools.append(tool)
                facts.append(tool_fact(tool, item.get("result")))
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            messages += 1
            final_text = str(item.get("text") or "")
    return {
        "tools": tools,
        "attempts": attempts,
        "facts": facts,
        "messages": messages,
        "usage": usage,
        "final_text": final_text,
    }


def parse_pi(events: list[dict[str, Any]]) -> dict[str, Any]:
    tools: list[str] = []
    attempts: list[str] = []
    facts: list[dict[str, Any]] = []
    messages = 0
    final_text = ""
    usage = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
    }
    for event in events:
        if event.get("type") == "tool_execution_end":
            tool = canonical_tool(str(event.get("toolName") or ""))
            attempts.append(tool)
            if not event.get("isError", False):
                tools.append(tool)
                facts.append(tool_fact(tool, event.get("result")))
        if event.get("type") != "message_end":
            continue
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        if message.get("role") != "assistant":
            continue
        messages += 1
        raw_usage = message.get("usage") if isinstance(message.get("usage"), dict) else {}
        usage["input_tokens"] += int(raw_usage.get("input", 0))
        usage["cached_input_tokens"] += int(raw_usage.get("cacheRead", 0))
        usage["output_tokens"] += int(raw_usage.get("output", 0))
        content = message.get("content") if isinstance(message.get("content"), list) else []
        text_parts = [str(item.get("text")) for item in content if item.get("type") == "text"]
        if text_parts:
            final_text = "".join(text_parts)
    return {
        "tools": tools,
        "attempts": attempts,
        "facts": facts,
        "messages": messages,
        "usage": usage,
        "final_text": final_text,
    }


def final_object(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def nested_value(value: dict[str, Any], path: str) -> Any:
    selected: Any = value
    for part in path.split("."):
        if not isinstance(selected, dict) or part not in selected:
            return None
        selected = selected[part]
    return selected


def score(case: dict[str, Any], observation: dict[str, Any], exit_code: int) -> dict[str, Any]:
    failures: list[str] = []
    tools = observation["tools"]
    if exit_code != 0:
        failures.append(f"agent_exit_code:{exit_code}")
    allowed = set(case["allowed_tools"])
    unexpected = [tool for tool in observation["attempts"] if tool not in allowed]
    if unexpected:
        failures.append("unexpected_tools:" + ",".join(unexpected))
    for tool, count in case["required_tools"].items():
        actual = tools.count(tool)
        if actual != count:
            failures.append(f"tool_count:{tool}:expected={count}:actual={actual}")
    budgets = case["budgets"]
    if len(tools) > int(budgets["max_tool_calls"]):
        failures.append("tool_budget_exceeded")
    observed_runtime = runtime_metrics(observation["facts"])
    for path, value in case.get("expected_runtime", {}).get("equals", {}).items():
        if nested_value(observed_runtime, path) != value:
            failures.append(f"runtime_mismatch:{path}")
    for path, value in case.get("expected_runtime", {}).get("minimum", {}).items():
        actual = nested_value(observed_runtime, path)
        if not isinstance(actual, int | float) or actual < value:
            failures.append(f"runtime_below_minimum:{path}")
    final = final_object(observation["final_text"])
    if final is None:
        failures.append("final_not_json_object")
    else:
        expected = case["expected_final"]
        for path, value in expected.get("equals", {}).items():
            if nested_value(final, path) != value:
                failures.append(f"final_mismatch:{path}")
        for path, value in expected.get("minimum", {}).items():
            actual = nested_value(final, path)
            if not isinstance(actual, int | float) or actual < value:
                failures.append(f"final_below_minimum:{path}")
    return {"passed": not failures, "failures": failures, "final": final}


def codex_command(args: argparse.Namespace, case: dict[str, Any]) -> list[str]:
    return [
        args.codex_command,
        "exec",
        "--profile",
        args.codex_profile,
        "--ephemeral",
        "--json",
        "--model",
        args.model,
        "--config",
        f'model_reasoning_effort="{args.thinking}"',
        "-C",
        str(args.cwd),
        case["prompt"],
    ]


def pi_command(args: argparse.Namespace, case: dict[str, Any]) -> list[str]:
    command = [
        args.pi_command,
        "--offline",
        "--mode",
        "json",
        "--print",
        "--no-session",
        "--model",
        args.model,
        "--thinking",
        args.thinking,
        "--no-extensions",
        "--extension",
        str(args.pi_extension),
        "--no-skills",
        "--skill",
        str(args.pi_skill),
        "--no-builtin-tools",
        "--tools",
        "eda_connections_list",
        case["prompt"],
    ]
    return native_command(command)


def native_command(command: list[str]) -> list[str]:
    if os.name != "nt":
        return command
    executable = command[0]
    suffix = Path(executable).suffix.casefold()
    if not suffix:
        executable = shutil.which(executable) or executable
        suffix = Path(executable).suffix.casefold()
    if suffix in {".cmd", ".bat"}:
        return ["cmd.exe", "/d", "/s", "/c", "call", executable, *command[1:]]
    return [executable, *command[1:]]


def validate_case(case: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "case_id",
        "level",
        "prompt",
        "required_tools",
        "allowed_tools",
        "expected_final",
        "budgets",
        "safety",
    }
    missing = sorted(required - case.keys())
    if missing or case.get("schema_version") != "eda-runtime.eval-case/v1":
        raise ValueError(f"invalid evaluation case; missing={missing}")


def variables(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        name, separator, selected = value.partition("=")
        if not separator or not name or not selected:
            raise ValueError("--var values must use NAME=value")
        result[name] = selected
    return result


def render_prompt(case: dict[str, Any], supplied: dict[str, str]) -> str:
    prompt = str(case["prompt"])
    for name in case.get("variables", []):
        if name not in supplied:
            raise ValueError(f"missing evaluation variable: {name}")
        prompt = prompt.replace("{{" + name + "}}", supplied[name])
    return prompt


def launch_failure(output: str) -> str | None:
    lowered = output.casefold()
    patterns = (
        (
            (
                "no api key found",
                "credentials_not_configured",
                "no matching provider is authenticated",
            ),
            "agent_auth_unavailable",
        ),
        (("mcp tool is not exposed", "transport closed"), "runtime_mcp_unavailable"),
        (("timed out", "timeoutexpired"), "agent_timeout"),
    )
    for messages, classification in patterns:
        if any(message in lowered for message in messages):
            return classification
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--agent", choices=("codex", "pi"), required=True)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--thinking", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument("--var", action="append", default=[])
    parser.add_argument("--codex-command", default="codex")
    parser.add_argument("--codex-profile", default="eda-runtime")
    parser.add_argument("--pi-command", default="pi-eda.cmd")
    parser.add_argument("--pi-extension", type=Path, default=Path("integrations/pi-eda-runtime"))
    parser.add_argument(
        "--pi-skill",
        type=Path,
        default=Path("integrations/pi-eda-runtime/skills/eda-runtime-control/SKILL.md"),
    )
    args = parser.parse_args()
    case = json.loads(args.case.read_text(encoding="utf-8"))
    validate_case(case)
    case["prompt"] = render_prompt(case, variables(args.var))
    command = (
        native_command(codex_command(args, case))
        if args.agent == "codex"
        else pi_command(args, case)
    )
    timeout = int(case["budgets"]["max_wall_seconds"]) + 15
    started = time.monotonic()
    try:
        completed = subprocess.run(  # noqa: S603
            command,
            cwd=args.cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output = completed.stdout
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        output = str(exc.stdout or "")
        exit_code = 124
    wall_ms = round((time.monotonic() - started) * 1000, 3)
    events = json_lines(output)
    observation = parse_codex(events) if args.agent == "codex" else parse_pi(events)
    scored = score(case, observation, exit_code)
    classified_failure = launch_failure(output)
    if classified_failure and classified_failure not in scored["failures"]:
        scored["failures"].append(classified_failure)
        scored["passed"] = False
    if wall_ms > int(case["budgets"]["max_wall_seconds"]) * 1000:
        scored["failures"].append("wall_budget_exceeded")
        scored["passed"] = False
    result = {
        "schema_version": "eda-runtime.eval-result/v1",
        "case_id": case["case_id"],
        "agent": args.agent,
        "model": args.model,
        "reasoning": args.thinking,
        "passed": scored["passed"],
        "failures": scored["failures"],
        "metrics": {
            "wall_ms": wall_ms,
            "observed_agent_messages": observation["messages"],
            "tool_attempts": len(observation["attempts"]),
            "tool_calls_succeeded": len(observation["tools"]),
            "tool_sequence": observation["tools"],
            **runtime_metrics(observation["facts"]),
            **observation["usage"],
        },
        "final": scored["final"],
        "raw_trace_sha256": hashlib.sha256(output.encode()).hexdigest(),
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if args.raw_output:
        args.raw_output.parent.mkdir(parents=True, exist_ok=True)
        args.raw_output.write_text(output, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
