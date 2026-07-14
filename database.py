"""
database.py - Leitura e escrita do arquivo ~/.installed_packages.json

Formato:
{
    "version": 1,
    "sudo": "no",
    "packages": [
        {"type": "package", "name": "git"},
        {"type": "script",  "name": "uv", "url": "https://..."}
    ]
}
"""

import json
from pathlib import Path


class Database:
    """Gerencia o banco de dados de pacotes instalados manualmente."""

    def __init__(self, path=None):
        self.path = Path(path) if path else Path.home() / ".installed_packages.json"
        self.sudo = "no"

    def load(self):
        """Retorna a lista de pacotes do arquivo.
        Se não existir ou estiver vazio/malformado, retorna lista vazia."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            self.sudo = "no"
            return []
        try:
            with open(self.path) as f:
                data = json.load(f)
            self.sudo = data.get("sudo", "no")
            return data.get("packages", [])
        except (json.JSONDecodeError, KeyError):
            self.sudo = "no"
            return []

    def save(self, packages):
        """Salva a lista de pacotes no arquivo."""
        data = {"version": 1, "sudo": self.sudo, "packages": packages}
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def add(self, package):
        """Adiciona um pacote, ignorando duplicações (por nome)."""
        packages = self.load()
        for pkg in packages:
            if pkg["name"] == package["name"]:
                return  # já existe, ignora
        packages.append(package)
        self.save(packages)

    def remove(self, name):
        """Remove um pacote do banco pelo nome."""
        packages = self.load()
        packages = [p for p in packages if p["name"] != name]
        self.save(packages)

    def find(self, name):
        """Busca um pacote pelo nome. Retorna None se não encontrar."""
        for pkg in self.load():
            if pkg["name"] == name:
                return pkg
        return None