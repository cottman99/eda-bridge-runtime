import json
import os
import subprocess
import sys

from eda_bridge_runtime.agent_audit import audit_events


def _cp936_environment() -> dict[str, str]:
    return {**os.environ, "PYTHONIOENCODING": "cp936"}


def test_mcp_cli_uses_utf8_when_windows_pipe_defaults_to_cp936(tmp_path):
    request_id = "中文请求"
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "编码测试", "version": "1"},
        },
    }

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "eda_bridge_runtime.cli",
            "mcp",
            "serve",
            "--registry",
            str(tmp_path / "connections.json"),
        ],
        input=(json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"),
        capture_output=True,
        env=_cp936_environment(),
        check=False,
    )

    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    response = json.loads(completed.stdout.decode("utf-8"))
    assert response["id"] == request_id


def test_codex_hook_cli_preserves_utf8_purpose_under_cp936(tmp_path):
    database = tmp_path / "agent-audit.sqlite3"
    purpose = "检查中文动机是否完整记录"
    event = {
        "session_id": "session-utf8",
        "turn_id": "turn-utf8",
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__eda_bridge_runtime__eda_connections_list",
        "tool_use_id": "tool-utf8",
        "tool_input": {"purpose": purpose},
    }

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "eda_bridge_runtime.cli",
            "hook",
            "codex-pre-tool-use",
            "--database",
            str(database),
        ],
        input=json.dumps(event, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        env=_cp936_environment(),
        check=False,
    )

    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    events = audit_events(database)
    assert events[0]["payload"]["purpose"] == purpose
