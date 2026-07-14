"""
database.py - Leitura e escrita do arquivo ~/.installed_packages

Formato:
{
    "version": 1,
    "packages": [
        {"type": "package", "name": "git"},
        {"type": "script",  "name": "uv", "url": "https://..."}
    ]
}
"""

import json
from pathlib import Path

DB_PATH = Path.home() / ".installed_packages"


class Database:
    """Gerencia o banco de dados de pacotes instalados manualmente."""

    @staticmethod
    def load():
        """Retorna a lista de pacotes do arquivo.
        Se não existir ou estiver vazio/malformado, retorna lista vazia."""
        if not DB_PATH.exists() or DB_PATH.stat().st_size == 0:
            return []
        try:
            with open(DB_PATH) as f:
                data = json.load(f)
            return data.get("packages", [])
        except (json.JSONDecodeError, KeyError):
            return []

    @staticmethod
    def save(packages):
        """Salva a lista de pacotes no arquivo."""
        data = {"version": 1, "packages": packages}
        with open(DB_PATH, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def add(package):
        """Adiciona um pacote, ignorando duplicações (por nome)."""
        packages = Database.load()
        for pkg in packages:
            if pkg["name"] == package["name"]:
                return  # já existe, ignora
        packages.append(package)
        Database.save(packages)

    @staticmethod
    def remove(name):
        """Remove um pacote do banco pelo nome."""
        packages = Database.load()
        packages = [p for p in packages if p["name"] != name]
        Database.save(packages)

    @staticmethod
    def find(name):
        """Busca um pacote pelo nome. Retorna None se não encontrar."""
        for pkg in Database.load():
            if pkg["name"] == name:
                return pkg
        return None