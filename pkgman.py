#!/usr/bin/env python3
"""
pkgman - Layer declarativo sobre gerenciadores de pacotes do SO

Gerencia a lista de pacotes instalados manualmente e permite replay
em estações novas.

Uso:
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
        description="Gerencia pacotes instalados manualmente com suporte a replay.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- install ---
    install_parser = subparsers.add_parser("install", help="Instala um ou mais pacotes")
    install_parser.add_argument(
        "names",
        nargs="*",
        metavar="PACKAGE",
        help="Nomes dos pacotes do SO para instalar",
    )
    install_parser.add_argument(
        "--url",
        nargs=2,
        metavar=("NAME", "URL"),
        help="Instala um script a partir de uma URL (nome + url)",
    )
    install_parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Instala todos os pacotes do banco de dados (replay)",
    )

    # --- remove ---
    remove_parser = subparsers.add_parser("remove", help="Remove um ou mais pacotes")
    remove_parser.add_argument(
        "names",
        nargs="+",
        metavar="PACKAGE",
        help="Nomes dos pacotes a remover",
    )

    # --- list ---
    subparsers.add_parser("list", help="Lista os pacotes registrados")

    args = parser.parse_args()

    cmds = Commands()

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
        cmds.list()


if __name__ == "__main__":
    main()