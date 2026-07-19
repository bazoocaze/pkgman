#!/usr/bin/env python3
"""
pkgman – Declarative layer over OS package managers.

Manages the list of manually installed packages and enables full replay
on fresh machines.
"""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from commands import Commands
from constants import ManagerType

# -- version detection ---------------------------------------------------

VERSION: str | None
try:
    VERSION = version("pkgman")
except PackageNotFoundError:
    VERSION = None

# -- argument parsing ----------------------------------------------------

def _parse_install_args(args: list[str]) -> tuple[str, str | list[str], str | None]:
    """Return (manager, names, source).

    - @package (default) → list of names, source is None
    - @custom manager  → single name; source == name if not provided
    """
    if args[0].startswith("@"):
        manager = args[0][1:]
        rest = args[1:]
    else:
        manager = ManagerType.PACKAGE
        rest = args

    if manager == ManagerType.PACKAGE:
        return manager, rest, None

    if len(rest) == 0:
        print("Error: Missing package name", file=sys.stderr)
        sys.exit(1)
    if len(rest) == 1:
        return manager, rest[0], rest[0]
    if len(rest) == 2:
        return manager, rest[0], rest[1]

    print("Error: Too many arguments for non-package manager", file=sys.stderr)
    sys.exit(1)


def _parse_remove_args(args: list[str]) -> tuple[str, str]:
    """Return (manager, name)."""
    if args[0].startswith("@"):
        manager = args[0][1:]
        if len(args) < 2:
            print("Error: Missing package name", file=sys.stderr)
            sys.exit(1)
        return manager, args[1]
    return ManagerType.AUTO, args[0]


# -- main ----------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pkgman",
        description="Manages manually installed packages with replay support.",
    )
    parser.add_argument(
        "-f", "--file",
        metavar="FILE",
        help="Path to the database file (default: ~/.config/.pkgman_database.json)",
    )
    parser.add_argument(
        "-V", "--version",
        action="store_true",
        help="Show version and exit",
    )
    subparsers = parser.add_subparsers(dest="command")

    # install
    install_parser = subparsers.add_parser("install", help="Install one or more packages")
    install_parser.add_argument(
        "args", nargs="*", metavar="[@MANAGER] NAME [SOURCE]",
        help="Package to install. Default manager is @package (OS packages). "
             "Use @manager prefix for custom managers (e.g. @uv, @script).",
    )
    install_parser.add_argument(
        "-a", "--all", action="store_true",
        help="Install all packages from the database (replay)",
    )

    # remove
    remove_parser = subparsers.add_parser("remove", help="Remove a package")
    remove_parser.add_argument(
        "args", nargs="+", metavar="[@MANAGER] NAME",
        help="Package to remove. Default is @auto (searches DB by name). "
             "Use @manager prefix for an explicit manager.",
    )

    # list
    list_parser = subparsers.add_parser("list", help="List registered packages")
    list_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    args = parser.parse_args()

    if args.version:
        print(VERSION or "unknown", flush=True)
        return

    if not args.command:
        parser.print_help()
        sys.stdout.flush()
        sys.exit(1)

    cmds = Commands(db_path=args.file)

    if args.command == "install":
        if args.all:
            cmds.install_all()
        elif args.args:
            manager, names_or_name, source = _parse_install_args(args.args)
            cmds.install(manager, names_or_name, source)
        else:
            install_parser.print_help()
            sys.exit(1)
    elif args.command == "remove":
        manager, name = _parse_remove_args(args.args)
        cmds.remove(manager, name)
    elif args.command == "list":
        cmds.list(json_output=args.json)


if __name__ == "__main__":
    main()