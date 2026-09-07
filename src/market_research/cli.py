from __future__ import annotations

import argparse
import json
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="market-research")
    subparsers = parser.add_subparsers(dest="command")
    config = subparsers.add_parser("config")
    config_subparsers = config.add_subparsers(dest="config_command")
    inspect = config_subparsers.add_parser("inspect")
    inspect.add_argument("--output-root", default="outputs")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            return 0
        raise
    if args.command == "config" and args.config_command == "inspect":
        print(json.dumps({"output_root": str(Path(args.output_root).expanduser().resolve())}))
        return 0
    if args.command is None:
        parser.print_help()
    return 0
