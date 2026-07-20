#!/usr/bin/env python3
"""
pkgman – Declarative layer over OS package managers.

Manages the list of manually installed packages and enables full replay
on fresh machines.
"""

import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Optional

from cli import COMMAND_DISPATCH, build_parser
from commands import Commands
from sys_check import SysCheck

# -- version detection ---------------------------------------------------

VERSION: str | None
try:
    VERSION = version("pkgman")
except PackageNotFoundError:
    VERSION = None


# -- main ----------------------------------------------------------------

def main(
    argv: list[str] | None = None,
    *,
    sys_check: SysCheck | None = None,
) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(VERSION or "unknown", flush=True)
        return

    if not args.command:
        parser.print_help()
        sys.stdout.flush()
        sys.exit(1)

    cmds = Commands(db_path=args.file, sys_check=sys_check)
    handler = COMMAND_DISPATCH[args.command]
    handler(cmds, args)


if __name__ == "__main__":
    main()