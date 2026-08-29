import importlib.util
from pathlib import Path


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
        "budgets": {"max_tool_calls": 1, "max_turns": 2},
    }

    assert runner.score(case, observation, 0)["passed"] is True
    assert observation["usage"]["input_tokens"] == 10


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
        "budgets": {"max_tool_calls": 2, "max_turns": 2},
    }
    scored = runner.score(case, observation, 0)

    assert observation["tools"][0] == "eda.connections.list"
    assert scored["passed"] is False
    assert "unexpected_tools:bash" in scored["failures"]


def test_windows_command_wrapping_is_shared_by_agent_clients(monkeypatch):
    runner = load_runner()
    monkeypatch.setattr(runner.os, "name", "nt")
    monkeypatch.setattr(
        runner.shutil,
        "which",
        lambda value: f"C:/tools/{value}.cmd",
    )

    command = runner.native_command(["codex", "exec", "one prompt"])

    assert command[:5] == ["cmd.exe", "/d", "/s", "/c", "call"]
    assert command[5].endswith("codex.cmd")


def test_case_variables_are_required_and_not_stored_in_case_definition():
    runner = load_runner()
    case = {"prompt": "Inspect {{CONNECTION}}", "variables": ["CONNECTION"]}

    assert runner.render_prompt(case, {"CONNECTION": "one"}) == "Inspect one"
