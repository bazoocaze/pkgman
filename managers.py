"""
managers.py - Detecção e execução dos gerenciadores de pacotes

Suporta: apt (Debian/Ubuntu), yum (RHEL/CentOS), brew (macOS)
"""

import subprocess
import shutil


class Manager:
    """Representa um gerenciador de pacotes do SO."""

    def __init__(self, name):
        self.name = name

    @staticmethod
    def detect():
        """Detecta o gerenciador disponível no sistema.

        Ordem de preferência: brew -> apt -> yum
        Retorna None se nenhum for encontrado.
        """
        for mgr in ["brew", "apt", "yum"]:
            if shutil.which(mgr):
                return Manager(mgr)
        return None

    def install(self, package_name, sudo=False):
        """Instala um pacote usando o gerenciador."""
        cmd = self._build_cmd("install", package_name)
        if sudo:
            cmd = ["sudo"] + cmd
        subprocess.run(cmd, check=True)

    def remove(self, package_name, sudo=False):
        """Remove um pacote usando o gerenciador."""
        cmd = self._build_cmd("remove", package_name)
        if sudo:
            cmd = ["sudo"] + cmd
        subprocess.run(cmd, check=True)

    def _build_cmd(self, action, package_name):
        """Monta a lista de argumentos para o subprocess."""
        if self.name == "apt":
            return [self.name, action, "-y", package_name]
        elif self.name == "yum":
            return [self.name, action, "-y", package_name]
        elif self.name == "brew":
            if action == "remove":
                action = "uninstall"
            return [self.name, action, package_name]
        else:
            raise RuntimeError(f"Unknown manager: {self.name}")
