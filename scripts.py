"""
scripts.py - Execução de scripts remotos via curl | bash
"""

import subprocess


class ScriptRunner:
    """Executa um script baixado de uma URL usando curl | bash."""

    @staticmethod
    def run(url):
        """Baixa e executa o script da URL."""
        cmd = f"curl -fsSL {url} | bash"
        subprocess.run(cmd, shell=True, check=True, executable="/bin/bash")