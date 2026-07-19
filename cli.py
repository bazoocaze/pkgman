"""
cli.py – argument parsing and command dispatch for pkgman.
"""

from __future__ import annotations

import argparse
import sys

from commands import Commands


# -- argument parsing ----------------------------------------------------

def parse_install_args(args: list[str]) -> tuple[str, str | list[str], str | None]:
    """Return (manager, names, source).

    - @package (default) -> list of names, source is None
    - @custom manager  -> single name; source == name if not provided
    """
    if args[0].startswith("@"):
        manager = args[0][1:]
        rest = args[1:]
    else:
        manager = "package"
        rest = args

    if manager == "package":
        return manager, rest, None

    if len(rest) == 0:
        raise ValueError("Missing package name")
    if len(rest) == 1:
        return manager, rest[0], rest[0]
    if len(rest) == 2:
        return manager, rest[0], rest[1]

    raise ValueError("Too many arguments for non-package manager")


def parse_remove_args(args: list[str]) -> tuple[str, str]:
    """Return (manager, name)."""
    if args[0].startswith("@"):
        manager = args[0][1:]
        if len(args) < 2:
            raise ValueError("Missing package name")
        return manager, args[1]
    return "auto", args[0]


# -- parser construction -------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
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

    return parser


# -- handler functions ---------------------------------------------------

def _handle_install(cmds: Commands, args: argparse.Namespace) -> None:
    if args.all:
        cmds.install_all()
    elif args.args:
        try:
            manager, names_or_name, source = parse_install_args(args.args)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        cmds.install(manager, names_or_name, source)
    else:
        print("install: error: the following arguments are required: [@MANAGER] NAME [SOURCE]", file=sys.stderr)
        sys.exit(1)


def _handle_remove(cmds: Commands, args: argparse.Namespace) -> None:
    try:
        manager, name = parse_remove_args(args.args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    cmds.remove(manager, name)


def _handle_list(cmds: Commands, args: argparse.Namespace) -> None:
    cmds.list(json_output=args.json)


# -- dispatch mapping ----------------------------------------------------

COMMAND_DISPATCH: dict[str, callable] = {
    "install": _handle_install,
    "remove": _handle_remove,
    "list": _handle_list,
}