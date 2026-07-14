"""
commands.py - Lógica dos comandos install, remove, list
"""

import sys
from database import Database
from managers import Manager
from scripts import ScriptRunner


class Commands:
    """Orquestra a execução dos comandos da CLI."""

    def __init__(self, db_path=None):
        self.db = Database(db_path)
        self.db.load()  # carrega o flag sudo (se arquivo existir)
        self.manager = Manager.detect()
        if self.manager is None:
            print(
                "Erro: Nenhum gerenciador de pacotes suportado encontrado.\n"
                "  Necessário: apt, yum ou brew.",
                file=sys.stderr,
            )
            sys.exit(1)

    @property
    def _use_sudo(self):
        return self.db.sudo == "yes"

    def install(self, names):
        """Instala pacotes do SO pelo nome."""
        for name in names:
            print(f"Instalando pacote: {name}")
            self.manager.install(name, sudo=self._use_sudo)
            self.db.add({"type": "package", "name": name})
            print(f"  -> {name} instalado e registrado.")

    def install_url(self, name, url):
        """Instala um script a partir de uma URL."""
        print(f"Instalando script: {name}")
        print(f"  URL: {url}")
        ScriptRunner.run(url)
        self.db.add({"type": "script", "name": name, "url": url})
        print(f"  -> {name} instalado e registrado.")

    def install_all(self):
        """Reinstala todos os pacotes do banco de dados (replay)."""
        packages = self.db.load()
        if not packages:
            print("Nenhum pacote registrado para instalar.")
            return

        for pkg in packages:
            if pkg["type"] == "package":
                print(f"Instalando pacote: {pkg['name']}")
                self.manager.install(pkg["name"], sudo=self._use_sudo)
            elif pkg["type"] == "script":
                print(f"Instalando script: {pkg['name']}")
                print(f"  URL: {pkg['url']}")
                ScriptRunner.run(pkg["url"])
        print("Replay concluído.")

    def remove(self, names):
        """Remove pacotes pelo nome."""
        for name in names:
            pkg = self.db.find(name)
            if pkg is None:
                print(f"Aviso: '{name}' não encontrado no banco de dados. Ignorando.")
                continue

            if pkg["type"] == "package":
                print(f"Removendo pacote: {name}")
                self.manager.remove(name, sudo=self._use_sudo)

            self.db.remove(name)
            print(f"  -> {name} removido do banco de dados.")

    def list(self):
        """Lista todos os pacotes registrados."""
        packages = self.db.load()
        if not packages:
            print("Nenhum pacote registrado.")
            return

        for pkg in packages:
            if pkg["type"] == "package":
                print(f"PACKAGE  {pkg['name']}")
            elif pkg["type"] == "script":
                print(f"SCRIPT   {pkg['name']}")
                print(f"         {pkg['url']}")