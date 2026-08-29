import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


def load_runner():
    path = Path(__file__).parents[1] / "evals" / "run_case.py"
    spec = importlib.util.spec_from_file_location("eval_runner", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_codex_trace_is_normalized_and_scored():
    runner = load_runner()
    events = [
        {"type": "turn.started"},
        {
            "type": "item.completed",
            "item": {
                "type": "mcp_tool_call",
                "tool": "eda.connections.list",
                "status": "completed",
                "result": {
                    "structured_content": {
                        "client_transport_ms": 4.5,
                        "run": {"run_id": "run-one", "state": "passed"},
                        "response": {"result": {"deduplicated": True}},
                    }
                },
            },
        },
        {
            "type": "item.completed",
            "item": {
                "type": "agent_message",
                "text": '{"status":"ready","connection_count":2}',
            },
        },
        {
            "type": "turn.completed",
            "usage": {"input_tokens": 10, "output_tokens": 2},
        },
    ]
    observation = runner.parse_codex(events)
    case = {
        "allowed_tools": ["eda.connections.list"],
        "required_tools": {"eda.connections.list": 1},
        "expected_final": {
            "equals": {"status": "ready"},
            "minimum": {"connection_count": 1},
        },
        "budgets": {"max_tool_calls": 1},
        "expected_runtime": {"equals": {"deduplicated_calls": 1}},
    }

    assert runner.score(case, observation, 0)["passed"] is True
    assert observation["usage"]["input_tokens"] == 10
    assert observation["facts"][0]["response_payload_chars"] > 0
    assert runner.runtime_metrics(observation["facts"]) == {
        "deduplicated_calls": 1,
        "reused_run_calls": 0,
        "distinct_projected_runs": 1,
        "distinct_jobs": 0,
        "total_response_payload_chars": 21,
        "largest_response_payload_chars": 21,
        "client_transport_ms_total": 4.5,
        "client_transport_ms_largest": 4.5,
    }
    assert runner.wall_partition(10.0, runner.runtime_metrics(observation["facts"])) == {
        "non_transport_wall_ms": 5.5,
        "client_transport_share_pct": 45.0,
    }


def test_pi_tool_alias_and_unexpected_tool_are_detected():
    runner = load_runner()
    events = [
        {
            "type": "tool_execution_end",
            "toolName": "eda_connections_list",
            "isError": False,
        },
        {"type": "tool_execution_end", "toolName": "bash", "isError": False},
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": '{"status":"ready","connection_count":2}'}],
                "usage": {"input": 8, "output": 2, "cacheRead": 3},
            },
        },
    ]
    observation = runner.parse_pi(events)
    case = {
        "allowed_tools": ["eda.connections.list"],
        "required_tools": {"eda.connections.list": 1},
        "expected_final": {
            "equals": {"status": "ready"},
            "minimum": {"connection_count": 1},
        },
        "budgets": {"max_tool_calls": 2},
    }
    scored = runner.score(case, observation, 0)

    assert observation["tools"][0] == "eda.connections.list"
    assert observation["attempts"] == ["eda.connections.list", "bash"]
    assert scored["passed"] is False
    assert "unexpected_tools:bash" in scored["failures"]


def test_pi_runtime_details_contribute_the_same_execution_facts():
    runner = load_runner()
    events = [
        {
            "type": "tool_execution_end",
            "toolName": "eda_read",
            "isError": False,
            "result": {
                "details": {
                    "runtime": {
                        "client_transport_ms": 3.5,
                        "run": {"run_id": "pi-run", "state": "passed"},
                        "response": {"result": {"observed": True}},
                    }
                }
            },
        }
    ]

    observation = runner.parse_pi(events)

    assert observation["tools"] == ["eda.read"]
    assert observation["facts"][0]["run_id"] == "pi-run"
    assert observation["facts"][0]["client_transport_ms"] == 3.5


def test_pi_plan_alias_preserves_public_runtime_tool_name():
    runner = load_runner()
    events = [
        {
            "type": "tool_execution_end",
            "toolName": "eda_run_plan",
            "isError": False,
            "result": {"details": {"runtime": {"status": "passed", "steps": []}}},
        }
    ]

    observation = runner.parse_pi(events)

    assert observation["attempts"] == ["eda.run_plan"]
    assert observation["tools"] == ["eda.run_plan"]


def test_codex_mutation_approval_uses_review_not_unrestricted_bypass():
    runner = load_runner()
    args = SimpleNamespace(
        codex_command="codex",
        model="gpt-5.5",
        thinking="medium",
        codex_profile="eda-runtime",
        approve_mutations=True,
        cwd=Path.cwd(),
    )
    command = runner.codex_command(args, {"prompt": "bounded mutation"}, Path("schema.json"))

    assert "--approve-for-me" in command
    assert "--dangerously-bypass-approvals-and-sandbox" not in command


def test_top_level_diagnostic_result_contributes_only_a_size_fact():
    runner = load_runner()
    events = [
        {
            "type": "item.completed",
            "item": {
                "type": "mcp_tool_call",
                "tool": "eda.connections.list",
                "status": "completed",
                "result": {
                    "structured_content": {
                        "status": "ready",
                        "connections": [{"connection_id": "private"}],
                    }
                },
            },
        }
    ]

    observation = runner.parse_codex(events)

    assert observation["facts"][0]["response_payload_chars"] > 2
    assert "private" not in str(observation["facts"])


def test_completed_client_call_with_failed_runtime_run_is_not_counted_as_succeeded():
    runner = load_runner()
    events = [
        {
            "type": "item.completed",
            "item": {
                "type": "mcp_tool_call",
                "tool": "eda.read",
                "status": "completed",
                "result": {
                    "structured_content": {
                        "run": {"run_id": "run-failed", "state": "failed"},
                        "response": {"status": "failed", "error": {"code": "bad_query"}},
                    }
                },
            },
        }
    ]

    observation = runner.parse_codex(events)

    assert observation["attempts"] == ["eda.read"]
    assert observation["tools"] == []
    assert observation["facts"][0]["state"] == "failed"


def test_plan_call_counts_nested_runs_without_double_counting_transport():
    runner = load_runner()
    events = [
        {
            "type": "item.completed",
            "item": {
                "type": "mcp_tool_call",
                "tool": "eda.run_plan",
                "status": "completed",
                "result": {
                    "structured_content": {
                        "status": "passed",
                        "client_transport_ms": 12.5,
                        "planned_step_count": 2,
                        "steps": [
                            {
                                "step_id": "one",
                                "run": {
                                    "run_id": "run-one",
                                    "job_id": "job-one",
                                    "state": "passed",
                                },
                                "response": {"result": {"observed": 1}},
                            },
                            {
                                "step_id": "two",
                                "run": {
                                    "run_id": "run-two",
                                    "job_id": "job-two",
                                    "state": "passed",
                                },
                                "response": {"result": {"observed": 2}},
                            },
                        ],
                    }
                },
            },
        }
    ]

    observation = runner.parse_codex(events)
    metrics = runner.runtime_metrics(observation["facts"])
    assert observation["tools"] == ["eda.run_plan"]
    assert metrics["distinct_projected_runs"] == 2
    assert metrics["distinct_jobs"] == 2
    assert metrics["client_transport_ms_total"] == 12.5


def test_windows_command_wrapping_is_shared_by_agent_clients(monkeypatch):
    runner = load_runner()
    # Replace only the loaded runner's platform view. Mutating os.name changes the
    # process-global module and makes pathlib try to instantiate WindowsPath on Linux.
    monkeypatch.setattr(runner, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        runner.shutil,
        "which",
        lambda value: f"C:/tools/{value}.cmd",
    )

    command = runner.native_command(["codex", "exec", "one prompt"])

    assert command[:5] == ["cmd.exe", "/d", "/s", "/c", "call"]
    assert command[5].endswith("codex.cmd")


def test_codex_command_applies_shared_thinking_budget():
    runner = load_runner()
    args = SimpleNamespace(
        codex_command="codex",
        codex_profile="eda-runtime",
        model="gpt-5.5",
        thinking="low",
        cwd=Path("workspace"),
    )

    command = runner.codex_command(
        args,
        {"prompt": "inspect", "allowed_tools": ["eda.read"]},
        Path("schema.json"),
    )

    assert 'model_reasoning_effort="low"' in command
    assert command[command.index("--output-schema") + 1] == "schema.json"
    assert any(
        value == 'mcp_servers.eda-bridge-runtime.enabled_tools=["eda.read"]' for value in command
    )


def test_pi_command_exposes_only_case_allowed_runtime_tools():
    runner = load_runner()
    args = SimpleNamespace(
        pi_command="pi-eda.cmd",
        pi_extension=Path("extension"),
        pi_skill=Path("skill.md"),
        model="openai-codex/gpt-test",
        thinking="medium",
    )
    command = runner.pi_command(
        args,
        {
            "prompt": "run plan",
            "allowed_tools": ["eda.run_plan", "eda.connections.list"],
        },
    )

    assert command[command.index("--tools") + 1] == "eda_connections_list,eda_run_plan"


def test_codex_command_can_measure_the_unscoped_global_profile():
    runner = load_runner()
    args = SimpleNamespace(
        codex_command="codex",
        codex_profile=None,
        model="gpt-5.5",
        thinking="medium",
        cwd=Path("workspace"),
    )

    command = runner.codex_command(args, {"prompt": "inspect"}, Path("schema.json"))

    assert "--profile" not in command


def test_final_output_schema_constrains_shape_without_forcing_expected_values():
    runner = load_runner()
    schema = runner.final_output_schema(
        {
            "expected_final": {
                "equals": {"status": "passed", "complete": True},
                "minimum": {"count": 1},
            }
        }
    )

    assert schema["required"] == ["complete", "count", "status"]
    assert schema["properties"] == {
        "count": {"type": "integer"},
        "status": {"type": "string"},
        "complete": {"type": "boolean"},
    }
    assert schema["additionalProperties"] is False


def test_all_public_eval_cases_have_a_valid_contract():
    runner = load_runner()
    case_root = Path(__file__).parents[1] / "evals" / "cases"

    for case_path in case_root.glob("*.json"):
        runner.validate_case(json.loads(case_path.read_text(encoding="utf-8")))


def test_case_variables_are_required_and_not_stored_in_case_definition():
    runner = load_runner()
    case = {"prompt": "Inspect {{CONNECTION}}", "variables": ["CONNECTION"]}

    assert runner.render_prompt(case, {"CONNECTION": "one"}) == "Inspect one"


def test_auth_failure_is_reduced_to_non_secret_classification():
    runner = load_runner()

    assert runner.launch_failure("No API key found for one provider") == "agent_auth_unavailable"
    assert (
        runner.launch_failure("No matching provider is authenticated. Use --provider.")
        == "agent_auth_unavailable"
    )


def test_agent_reported_tool_unavailable_is_classified_without_raw_trace():
    runner = load_runner()

    assert (
        runner.agent_reported_failure(
            {"status": "failed", "eda": "tool_unavailable"}, tool_attempts=0
        )
        == "agent_reported_tool_unavailable"
    )
    assert (
        runner.agent_reported_failure(
            {"status": "failed", "eda": "tool_unavailable"}, tool_attempts=1
        )
        is None
    )


def test_zero_call_claimed_success_is_classified_as_unverified():
    runner = load_runner()

    assert (
        runner.agent_reported_failure(
            {"status": "passed", "frequency_count": 1},
            tool_attempts=0,
            required_tool_calls=1,
        )
        == "agent_reported_unverified_success"
    )
    assert (
        runner.agent_reported_failure({"status": "passed"}, tool_attempts=0, required_tool_calls=0)
        is None
    )
