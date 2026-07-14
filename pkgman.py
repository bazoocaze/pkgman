#!/usr/bin/env python3
"""
pkgman - Declarative layer over OS package managers

Manages the list of manually installed packages and enables full replay
on fresh machines.

Usage:
    pkgman install git jq
    pkgman install --url uv https://astral.sh/uv/install.sh
    pkgman install -a
    pkgman remove git
    pkgman remove uv
    pkgman list
"""

import argparse
import sys

from commands import Commands


def main():
    parser = argparse.ArgumentParser(
        prog="pkgman",
        description="Manages manually installed packages with replay support.",
    )
    parser.add_argument(
        "-f", "--file",
        metavar="FILE",
        help="Path to the database file (default: ~/.installed_packages.json)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- install ---
    install_parser = subparsers.add_parser("install", help="Install one or more packages")
    install_parser.add_argument(
        "names",
        nargs="*",
        metavar="PACKAGE",
        help="Names of OS packages to install",
    )
    install_parser.add_argument(
        "--url",
        nargs=2,
        metavar=("NAME", "URL"),
        help="Install a script from a URL (name + url)",
    )
    install_parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Install all packages from the database (replay)",
    )

    # --- remove ---
    remove_parser = subparsers.add_parser("remove", help="Remove one or more packages")
    remove_parser.add_argument(
        "names",
        nargs="+",
        metavar="PACKAGE",
        help="Names of packages to remove",
    )

    # --- list ---
    list_parser = subparsers.add_parser("list", help="List registered packages")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    args = parser.parse_args()

    cmds = Commands(db_path=args.file)

    if args.command == "install":
        if args.all:
            cmds.install_all()
        elif args.url:
            name, url = args.url
            cmds.install_url(name, url)
        elif args.names:
            cmds.install(args.names)
        else:
            install_parser.print_help()
            sys.exit(1)
    elif args.command == "remove":
        cmds.remove(args.names)
    elif args.command == "list":
        cmds.list(json_output=args.json)


if __name__ == "__main__":
    main()