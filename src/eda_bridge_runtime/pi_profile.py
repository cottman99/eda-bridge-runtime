"""Install a narrow Pi EDA launcher without modifying or exposing credentials."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

EDA_TOOLS = (
    "eda_context_resolve",
    "eda_connections_list",
    "eda_connection_reset",
    "eda_capabilities",
    "eda_read",
    "eda_submit",
    "eda_run_plan",
    "eda_job_status",
    "eda_job_wait",
    "eda_job_events",
)


def runtime_extension_root() -> Path:
    """Locate the packaged Pi adapter, with an editable-tree fallback for development."""

    packaged = Path(__file__).resolve().parent / "pi_eda_runtime"
    if packaged.is_dir():
        return packaged
    editable = Path(__file__).resolve().parents[2] / "integrations" / "pi-eda-runtime"
    if editable.is_dir():
        return editable
    raise ValueError("The installed Runtime package does not contain the Pi EDA adapter.")


def file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def credential_entry_count(path: Path) -> int:
    if not path.is_file():
        return 0
    return len(load_object(path))


def install_profile(
    *,
    profile_dir: Path,
    session_dir: Path,
    launcher: Path,
    login_launcher: Path | None = None,
    status_launcher: Path | None = None,
    node: Path,
    pi_cli: Path,
    auth_provider: str = "openai-codex",
    vendor_skills: tuple[Path, ...] = (),
) -> dict[str, Any]:
    profile_dir = profile_dir.expanduser().resolve()
    session_dir = session_dir.expanduser().resolve()
    launcher = launcher.expanduser().resolve()
    login_launcher = (
        login_launcher.expanduser().resolve()
        if login_launcher is not None
        else launcher.with_name(f"{launcher.stem}-login{launcher.suffix}")
    )
    status_launcher = (
        status_launcher.expanduser().resolve()
        if status_launcher is not None
        else launcher.with_name(f"{launcher.stem}-status{launcher.suffix}")
    )
    node = node.expanduser().resolve()
    pi_cli = pi_cli.expanduser().resolve()
    if not node.is_file() or not pi_cli.is_file():
        raise ValueError("The selected Node executable and Pi CLI bundle must already exist.")
    if not auth_provider or any(character.isspace() for character in auth_provider):
        raise ValueError("Pi authentication provider must be one non-empty token.")
    package_root = runtime_extension_root()
    runtime_skill = package_root / "skills/eda-runtime-control/SKILL.md"
    selected_skills = (runtime_skill, *(path.expanduser().resolve() for path in vendor_skills))
    if not all(path.is_file() for path in selected_skills):
        raise ValueError("Every selected Pi EDA Skill must be an existing SKILL.md file.")

    auth_path = profile_dir / "auth.json"
    auth_before = file_hash(auth_path)
    auth_entries = credential_entry_count(auth_path)
    settings_path = profile_dir / "settings.json"
    settings = load_object(settings_path)
    settings.update(
        {
            "defaultThinkingLevel": "medium",
            "defaultProjectTrust": "never",
            "enableAnalytics": False,
            "enableInstallTelemetry": False,
            "quietStartup": True,
            "sessionDir": session_dir.as_posix(),
            "compaction": {
                "enabled": True,
                "reserveTokens": 16384,
                "keepRecentTokens": 16000,
            },
            "retry": {
                "enabled": True,
                "maxRetries": 1,
                "baseDelayMs": 1000,
                "provider": {"maxRetries": 0, "maxRetryDelayMs": 15000},
            },
        }
    )
    atomic_text(settings_path, json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
    session_dir.mkdir(parents=True, exist_ok=True)

    launch_arguments = [
        str(node),
        str(pi_cli),
        "--no-extensions",
        "--extension",
        str(package_root),
        "--no-skills",
    ]
    for skill in selected_skills:
        launch_arguments.extend(["--skill", str(skill)])
    enabled_tools = ("read", *EDA_TOOLS)
    launch_arguments.extend(["--no-builtin-tools", "--tools", ",".join(enabled_tools)])
    if any("%" in value or "\n" in value or "\r" in value for value in launch_arguments):
        raise ValueError("Pi launcher paths must not contain batch expansion characters.")
    command = "\n".join(
        [
            "@echo off",
            "setlocal",
            f'set "PI_CODING_AGENT_DIR={profile_dir}"',
            f'set "PI_CODING_AGENT_SESSION_DIR={session_dir}"',
            'set "PI_TELEMETRY=0"',
            'set "PI_SKIP_VERSION_CHECK=1"',
            subprocess.list2cmdline(launch_arguments) + " %*",
            "",
        ]
    )
    atomic_text(launcher, command)
    login_arguments = [
        str(node),
        str(pi_cli),
        "--no-extensions",
        "--no-skills",
        "--no-tools",
        "--no-context-files",
    ]
    login_command = "\n".join(
        [
            "@echo off",
            "setlocal",
            f'set "PI_CODING_AGENT_DIR={profile_dir}"',
            f'set "PI_CODING_AGENT_SESSION_DIR={session_dir}"',
            'set "PI_TELEMETRY=0"',
            'set "PI_SKIP_VERSION_CHECK=1"',
            subprocess.list2cmdline(login_arguments) + " %*",
            "",
        ]
    )
    atomic_text(login_launcher, login_command)
    status_arguments = [
        str(node),
        str(pi_cli),
        "auth",
        "check",
        "--provider",
        auth_provider,
        "--json",
    ]
    status_command = "\n".join(
        [
            "@echo off",
            "setlocal",
            f'set "PI_CODING_AGENT_DIR={profile_dir}"',
            f'set "PI_CODING_AGENT_SESSION_DIR={session_dir}"',
            'set "PI_TELEMETRY=0"',
            'set "PI_SKIP_VERSION_CHECK=1"',
            subprocess.list2cmdline(status_arguments),
            "",
        ]
    )
    atomic_text(status_launcher, status_command)
    auth_after = file_hash(auth_path)
    if auth_before != auth_after:
        raise RuntimeError("Pi credential file changed during profile installation.")
    return {
        "status": "installed",
        "agent": "pi",
        "profile_dir": str(profile_dir),
        "session_dir": str(session_dir),
        "launcher": str(launcher),
        "login_launcher": str(login_launcher),
        "status_launcher": str(status_launcher),
        "auth_provider": auth_provider,
        "auth_state": "configured" if auth_entries else "login_required",
        "auth_unchanged": True,
        "runtime_extension": str(package_root),
        "loaded_skills": len(selected_skills),
        "builtin_tools": ["read"],
        "runtime_tools": len(EDA_TOOLS),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-dir", type=Path, required=True)
    parser.add_argument("--session-dir", type=Path, required=True)
    parser.add_argument("--launcher", type=Path, required=True)
    parser.add_argument("--login-launcher", type=Path)
    parser.add_argument("--status-launcher", type=Path)
    parser.add_argument("--auth-provider", default="openai-codex")
    parser.add_argument("--node", type=Path, required=True)
    parser.add_argument("--pi-cli", type=Path, required=True)
    parser.add_argument(
        "--vendor-skill",
        type=Path,
        action="append",
        default=[],
        help="Additional vendor SKILL.md to load into the one-command EDA profile.",
    )
    args = parser.parse_args()
    result = install_profile(
        profile_dir=args.profile_dir,
        session_dir=args.session_dir,
        launcher=args.launcher,
        login_launcher=args.login_launcher,
        status_launcher=args.status_launcher,
        node=args.node,
        pi_cli=args.pi_cli,
        auth_provider=args.auth_provider,
        vendor_skills=tuple(args.vendor_skill),
    )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
