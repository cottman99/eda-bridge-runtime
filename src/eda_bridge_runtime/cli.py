"""Small operational CLI; EDA-specific commands are supplied by adapters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ._version import __version__
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
                    "protocols": {"request": 1, "context": 1, "handshake": 1},
                },
                indent=2,
            )
        )
        return 0
    if args.command == "context" and args.context_command == "decode":
        print(json.dumps(EDAContext.decode(args.token).__dict__, indent=2))
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
