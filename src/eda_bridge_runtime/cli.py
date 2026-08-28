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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eda-runtime")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
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
        from .mcp_server import serve_mcp

        serve_mcp(registry=ConnectionRegistry(args.registry))
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
