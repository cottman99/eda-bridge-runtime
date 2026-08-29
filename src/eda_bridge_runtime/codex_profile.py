"""Generate a narrow Codex profile for EDA Runtime work."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DEFAULT_KEEP_NAMES = frozenset(
    {
        "eda-runtime-control",
        "ads-agent-bridge",
        "ads-kb-docs",
        "ansysem-agent-bridge",
        "ansysem-kb-docs",
    }
)
_NAME = re.compile(r"^name:\s*[\"']?([^\"'\r\n]+)", re.MULTILINE)
_MCP_TABLE = re.compile(
    r"^\s*\[\s*mcp_servers\s*\.\s*"
    r'(?:(?P<double>"(?:\\.|[^"\\])*")|(?P<single>\'[^\']*\')|(?P<bare>[A-Za-z0-9_-]+))'
    r"(?:\s*\.|\s*\])"
)
_PLUGIN_VERSION = re.compile(
    r"^(?P<release>\d+(?:\.\d+)*)"
    r"(?:[-.]?(?P<label>dev|alpha|a|beta|b|rc|pre|preview)[.-]?(?P<number>\d+)?)?$",
    re.IGNORECASE,
)
_PRERELEASE_RANK = {
    "dev": 0,
    "alpha": 1,
    "a": 1,
    "beta": 2,
    "b": 2,
    "rc": 3,
    "pre": 3,
    "preview": 3,
}


def discover_skills(codex_home: Path) -> list[tuple[Path, str]]:
    roots = [
        (codex_home / "skills", frozenset({".system"})),
        (codex_home / "plugins" / "cache", frozenset()),
    ]
    found: list[tuple[Path, str]] = []
    for root, allowed_hidden_roots in roots:
        if not root.is_dir():
            continue
        for skill_file in root.rglob("SKILL.md"):
            relative = skill_file.relative_to(root)
            if any(
                part.startswith(".") and not (index == 0 and part in allowed_hidden_roots)
                for index, part in enumerate(relative.parts)
            ):
                continue
            try:
                header = skill_file.read_text(encoding="utf-8")[:4096]
            except (OSError, UnicodeError):
                continue
            match = _NAME.search(header)
            if match:
                found.append((skill_file.resolve(), match.group(1).strip()))
    return sorted(set(found), key=lambda item: str(item[0]).casefold())


def _is_plugin_cache_skill(path: Path) -> bool:
    parts = tuple(part.casefold() for part in path.parts)
    return any(parts[index : index + 2] == ("plugins", "cache") for index in range(len(parts) - 1))


def _plugin_version_key(path: Path) -> tuple[tuple[int, ...], int, int]:
    if not _is_plugin_cache_skill(path) or len(path.parents) < 3:
        return ((), -1, -1)
    match = _PLUGIN_VERSION.fullmatch(path.parents[2].name)
    if not match:
        return ((), -1, -1)
    release = tuple(int(value) for value in match.group("release").split("."))
    release = release + (0,) * (4 - len(release))
    label = match.group("label")
    if label is None:
        return (release, 4, 0)
    return (
        release,
        _PRERELEASE_RANK[label.casefold()],
        int(match.group("number") or 0),
    )


def choose_enabled_skill_paths(skills: list[tuple[Path, str]], keep_names: set[str]) -> set[Path]:
    """Choose one canonical path per requested Skill name.

    A directly installed Skill is the user's explicit source and therefore outranks
    plugin-cache copies. When only cached plugin copies exist, the highest versioned
    path wins while older cache entries remain present and disabled in the profile.
    """
    enabled: set[Path] = set()
    for name in keep_names:
        candidates = [path for path, candidate_name in skills if candidate_name == name]
        if not candidates:
            continue
        direct = [path for path in candidates if not _is_plugin_cache_skill(path)]
        pool = direct or candidates
        enabled.add(
            max(
                pool,
                key=lambda path: (_plugin_version_key(path), str(path).casefold()),
            )
        )
    return enabled


def discover_inherited_mcp_servers(codex_home: Path) -> list[str]:
    """Return global MCP names that the narrow profile must explicitly disable."""

    path = codex_home / "config.toml"
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError(
            "cannot inspect global Codex config; refusing to generate a leaky EDA profile"
        ) from exc
    names: set[str] = set()
    for line in lines:
        if not line.lstrip().startswith("[mcp_servers"):
            continue
        match = _MCP_TABLE.match(line)
        if not match:
            raise ValueError(
                "cannot inspect global Codex config; refusing to generate a leaky EDA profile"
            )
        if match.group("double"):
            name = json.loads(match.group("double"))
        elif match.group("single"):
            name = match.group("single")[1:-1]
        else:
            name = match.group("bare")
        if name != "eda-bridge-runtime":
            names.add(name)
    return sorted(names)


def render_profile(
    skills: list[tuple[Path, str]],
    keep_names: set[str],
    *,
    disabled_mcp_servers: list[str] | None = None,
    runtime_command: str = "eda-runtime",
    approve_mutations: bool = False,
) -> str:
    enabled_paths = choose_enabled_skill_paths(skills, keep_names)
    lines = [
        "# Generated by EDA Bridge Runtime. Regenerate instead of editing path entries.",
        'approval_policy = "never"',
        'sandbox_mode = "read-only"',
        'model_reasoning_effort = "medium"',
        "",
        "[features]",
        "plugins = false",
        "apps = false",
        "browser_use = false",
        "code_mode = false",
        # Codex 0.151 uses the host process for direct MCP transport even when
        # Agent-visible Code Mode is disabled. Keep the transport, not the tool.
        "code_mode_host = true",
        "computer_use = false",
        "image_generation = false",
        "memories = false",
        "multi_agent = false",
        "goals = false",
        "skill_search = false",
        "workspace_dependencies = false",
        "shell_tool = false",
        "shell_snapshot = false",
        "",
        '[mcp_servers."eda-bridge-runtime"]',
        f"command = {json.dumps(runtime_command)}",
        'args = ["mcp", "serve"]',
        "required = true",
        'enabled_tools = ["eda.connections.list", "eda.connection.reset", '
        '"eda.context.resolve", "eda.capabilities", "eda.read", "eda.submit", '
        '"eda.run_plan", "eda.job.status", "eda.job.wait", "eda.job.events"]',
        "",
        "[[hooks.PreToolUse]]",
        'matcher = "^mcp__eda_bridge_runtime__.*$"',
        "",
        "[[hooks.PreToolUse.hooks]]",
        'type = "command"',
        'command = "eda-runtime hook codex-pre-tool-use"',
        "timeout = 3",
        "",
        "[[hooks.PostToolUse]]",
        'matcher = "^mcp__eda_bridge_runtime__.*$"',
        "",
        "[[hooks.PostToolUse.hooks]]",
        'type = "command"',
        'command = "eda-runtime hook codex-post-tool-use"',
        "timeout = 3",
        "",
    ]
    for name in disabled_mcp_servers or []:
        lines.extend(
            [
                f"[mcp_servers.{json.dumps(name)}]",
                "enabled = false",
                "",
            ]
        )
    if approve_mutations:
        lines.extend(
            [
                '[mcp_servers."eda-bridge-runtime".tools."eda.submit"]',
                'approval_mode = "approve"',
                "",
                '[mcp_servers."eda-bridge-runtime".tools."eda.run_plan"]',
                'approval_mode = "approve"',
                "",
            ]
        )
    for path, _name in skills:
        lines.extend(
            [
                "[[skills.config]]",
                f"path = {json.dumps(str(path))}",
                f"enabled = {'true' if path in enabled_paths else 'false'}",
                "",
            ]
        )
    return "\n".join(lines)


def install_profile(
    codex_home: Path,
    *,
    profile_name: str = "eda-runtime",
    keep_names: set[str] | None = None,
    runtime_command: str = "eda-runtime",
    approve_mutations: bool = False,
) -> tuple[Path, int, int]:
    skills = discover_skills(codex_home)
    disabled_mcp_servers = discover_inherited_mcp_servers(codex_home)
    selected = set(keep_names or DEFAULT_KEEP_NAMES)
    enabled_paths = choose_enabled_skill_paths(skills, selected)
    output = codex_home / f"{profile_name}.config.toml"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_profile(
            skills,
            selected,
            disabled_mcp_servers=disabled_mcp_servers,
            runtime_command=runtime_command,
            approve_mutations=approve_mutations,
        ),
        encoding="utf-8",
        newline="\n",
    )
    enabled = len(enabled_paths)
    return output, enabled, len(skills) - enabled


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--profile-name", default="eda-runtime")
    parser.add_argument("--runtime-command", default="eda-runtime")
    parser.add_argument(
        "--approve-mutations",
        action="store_true",
        help=(
            "Pre-approve only typed Runtime mutation tools for a separately authorized "
            "unattended profile."
        ),
    )
    parser.add_argument("--keep-name", action="append", dest="keep_names")
    args = parser.parse_args()
    output, enabled, disabled = install_profile(
        args.codex_home.expanduser().resolve(),
        profile_name=args.profile_name,
        keep_names=set(args.keep_names) if args.keep_names else None,
        runtime_command=args.runtime_command,
        approve_mutations=args.approve_mutations,
    )
    print(
        json.dumps(
            {
                "status": "installed",
                "profile": args.profile_name,
                "path": str(output),
                "enabled_skills": enabled,
                "disabled_skills": disabled,
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
