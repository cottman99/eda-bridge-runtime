"""Small operational CLI; EDA-specific commands are supplied by adapters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ._version import __version__
from .connections import ConnectionRegistry, ConnectionSpec, discover_connection_origin
from .context import EDAContext
from .ledger import ExecutionLedger
from .protocol import ActorIdentity, RuntimeFacts


def _configure_protocol_stdio() -> None:
    """Use the MCP/Hook wire encoding instead of the Windows active code page."""
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            # In-memory and captured streams may not support reconfiguration.
            continue


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eda-runtime")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    agent_profile = sub.add_parser("agent-profile")
    agent_profile_sub = agent_profile.add_subparsers(dest="agent_profile_command", required=True)
    codex_profile = agent_profile_sub.add_parser("codex")
    codex_profile_sub = codex_profile.add_subparsers(dest="codex_profile_command", required=True)
    codex_install = codex_profile_sub.add_parser("install")
    codex_install.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    codex_install.add_argument("--profile-name", default="eda-runtime")
    codex_install.add_argument("--runtime-command", default="eda-runtime")
    codex_install.add_argument("--approve-mutations", action="store_true")
    codex_install.add_argument("--keep-name", action="append", dest="keep_names")
    pi_profile = agent_profile_sub.add_parser("pi")
    pi_profile_sub = pi_profile.add_subparsers(dest="pi_profile_command", required=True)
    pi_install = pi_profile_sub.add_parser("install")
    pi_install.add_argument("--profile-dir", type=Path, required=True)
    pi_install.add_argument("--session-dir", type=Path, required=True)
    pi_install.add_argument("--launcher", type=Path, required=True)
    pi_install.add_argument("--login-launcher", type=Path)
    pi_install.add_argument("--status-launcher", type=Path)
    pi_install.add_argument("--auth-provider", default="openai-codex")
    pi_install.add_argument("--node", type=Path, required=True)
    pi_install.add_argument("--pi-cli", type=Path, required=True)
    pi_install.add_argument("--vendor-skill", type=Path, action="append", default=[])
    context = sub.add_parser("context")
    context_sub = context.add_subparsers(dest="context_command", required=True)
    decode = context_sub.add_parser("decode")
    decode.add_argument("token")
    ledger = sub.add_parser("ledger")
    ledger_sub = ledger.add_subparsers(dest="ledger_command", required=True)
    verify = ledger_sub.add_parser("verify")
    verify.add_argument("database", type=Path)
    verify.add_argument("run_id")
    export = ledger_sub.add_parser("export")
    export.add_argument("database", type=Path)
    export.add_argument("destination", type=Path)
    connection = sub.add_parser("connection")
    connection_sub = connection.add_subparsers(dest="connection_command", required=True)
    for action in ("list", "set", "remove"):
        item = connection_sub.add_parser(action)
        item.add_argument("--registry", type=Path)
        if action in {"set", "remove"}:
            item.add_argument("connection_id")
        if action == "set":
            item.add_argument("--eda", required=True)
            item.add_argument("--kind", choices=("local", "ssh"), required=True)
            item.add_argument("--host")
            item.add_argument("--origin-id")
            item.add_argument("--no-origin-probe", action="store_true")
            item.add_argument("--ssh-option", action="append", default=[])
            item.add_argument("--timeout-seconds", type=float, default=30)
            item.add_argument("launch_command", nargs=argparse.REMAINDER)
    mcp = sub.add_parser("mcp")
    mcp_sub = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_serve = mcp_sub.add_parser("serve")
    mcp_serve.add_argument("--registry", type=Path)
    hook = sub.add_parser("hook")
    hook_sub = hook.add_subparsers(dest="hook_command", required=True)
    for phase in ("codex-pre-tool-use", "codex-post-tool-use"):
        item = hook_sub.add_parser(phase)
        item.add_argument("--database", type=Path)
    audit = sub.add_parser("audit")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)
    audit_list = audit_sub.add_parser("list")
    audit_list.add_argument("--database", type=Path)
    audit_list.add_argument("--limit", type=int, default=20)
    audit_list.add_argument("--session-id")
    audit_list.add_argument("--execution-run-id")
    audit_list.add_argument(
        "--full",
        action="store_true",
        help="Return complete hash-chained events instead of compact call rows.",
    )
    audit_analyze = audit_sub.add_parser("analyze")
    audit_analyze.add_argument("--database", type=Path)
    audit_analyze.add_argument("--limit", type=int, default=1000)
    audit_analyze.add_argument("--session-id")
    audit_analyze.add_argument("--execution-run-id")
    audit_bypass = audit_sub.add_parser("bypass")
    audit_bypass.add_argument("--database", type=Path)
    audit_bypass.add_argument("--purpose", required=True)
    audit_bypass.add_argument(
        "--lane", choices=("shell", "gui", "vendor-cli", "other"), required=True
    )
    audit_bypass.add_argument("--reason", required=True)
    audit_bypass.add_argument(
        "--outcome", choices=("passed", "failed", "blocked", "unknown"), required=True
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command in {"mcp", "hook"}:
        _configure_protocol_stdio()
    if args.command == "doctor":
        print(
            json.dumps(
                {
                    "status": "ok",
                    "runtime": RuntimeFacts(__version__).to_dict(),
                    "actor": ActorIdentity.detect().to_dict(),
                    "protocols": {"request": 1, "context": [1, 2], "handshake": 1},
                },
                indent=2,
            )
        )
        return 0
    if args.command == "agent-profile" and args.agent_profile_command == "codex":
        from .codex_profile import install_profile

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
                    "agent": "codex",
                    "profile": args.profile_name,
                    "path": str(output),
                    "enabled_skills": enabled,
                    "disabled_skills": disabled,
                },
                indent=2,
            )
        )
        return 0
    if args.command == "agent-profile" and args.agent_profile_command == "pi":
        from .pi_profile import install_profile

        result = install_profile(
            profile_dir=args.profile_dir,
            session_dir=args.session_dir,
            launcher=args.launcher,
            login_launcher=args.login_launcher,
            status_launcher=args.status_launcher,
            auth_provider=args.auth_provider,
            node=args.node,
            pi_cli=args.pi_cli,
            vendor_skills=tuple(args.vendor_skill),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "context" and args.context_command == "decode":
        print(json.dumps(EDAContext.decode(args.token).__dict__, indent=2))
        return 0
    if args.command == "connection":
        registry = ConnectionRegistry(args.registry)
        if args.connection_command == "list":
            print(
                json.dumps(
                    {
                        "status": "ready",
                        "connections": [item.to_dict() for item in registry.list()],
                    },
                    indent=2,
                )
            )
            return 0
        if args.connection_command == "remove":
            removed = registry.remove(args.connection_id)
            print(json.dumps({"status": "removed" if removed else "not_found"}))
            return 0 if removed else 1
        launch_command = list(args.launch_command)
        if launch_command and launch_command[0] == "--":
            launch_command.pop(0)
        spec = ConnectionSpec(
            connection_id=args.connection_id,
            eda=args.eda,
            kind=args.kind,
            command=tuple(launch_command),
            host=args.host,
            ssh_options=tuple(args.ssh_option),
            timeout_seconds=args.timeout_seconds,
            origin_id=args.origin_id,
        )
        if not spec.origin_id and not args.no_origin_probe:
            spec = discover_connection_origin(spec)
        registry.upsert(spec)
        print(json.dumps({"status": "ready", "connection": spec.to_dict()}, indent=2))
        return 0
    if args.command == "mcp" and args.mcp_command == "serve":
        from .agent_audit import default_agent_audit_path
        from .mcp_server import serve_mcp

        serve_mcp(
            registry=ConnectionRegistry(args.registry),
            audit_database=default_agent_audit_path(),
        )
        return 0
    if args.command == "hook":
        from .agent_audit import record_codex_hook

        try:
            event = json.load(sys.stdin)
            phase = "pre" if args.hook_command == "codex-pre-tool-use" else "post"
            record_codex_hook(event, phase=phase, database=args.database)
        except Exception:
            # Audit is fail-open: telemetry must never alter or block an EDA call.
            return 0
        return 0
    if args.command == "audit" and args.audit_command == "list":
        from .agent_audit import compact_audit_calls_from_database, recent_audit_run_events

        if args.full:
            result = {
                "events": recent_audit_run_events(
                    args.database,
                    limit=args.limit,
                    session_id=args.session_id,
                    execution_run_id=args.execution_run_id,
                )
            }
        else:
            result = {
                "schema_version": "eda-runtime.audit-calls/v1",
                "source_policy": "mcp-runtime-preferred",
                "included_sources": ["mcp-runtime", "runtime-bypass"],
                "calls": compact_audit_calls_from_database(
                    args.database,
                    limit=args.limit,
                    session_id=args.session_id,
                    execution_run_id=args.execution_run_id,
                ),
            }
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "audit" and args.audit_command == "analyze":
        from .agent_audit import recent_audit_run_events
        from .audit_analysis import analyze_events

        events = recent_audit_run_events(
            args.database,
            limit=args.limit,
            session_id=args.session_id,
            execution_run_id=args.execution_run_id,
        )
        print(json.dumps(analyze_events(events), indent=2))
        return 0
    if args.command == "audit" and args.audit_command == "bypass":
        from .agent_audit import record_runtime_bypass

        run_id = record_runtime_bypass(
            purpose=args.purpose,
            lane=args.lane,
            reason=args.reason,
            outcome=args.outcome,
            database=args.database,
        )
        print(json.dumps({"status": "recorded", "run_id": run_id}))
        return 0
    if args.command == "ledger":
        with ExecutionLedger(args.database) as ledger:
            if args.ledger_command == "verify":
                valid = ledger.verify(args.run_id)
                print(json.dumps({"run_id": args.run_id, "valid": valid}))
                return 0 if valid else 1
            ledger.export_ndjson(args.destination)
            print(json.dumps({"status": "ok", "destination": str(args.destination)}))
            return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
