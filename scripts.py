"""
scripts.py - Execute remote scripts via curl | bash
"""

import subprocess


class ScriptRunner:
    """Downloads and executes a script from a URL using curl | bash."""

    @staticmethod
    def run(url):
        """Download and execute the script from the URL."""
        cmd = f"curl -fsSL {url} | bash"
        subprocess.run(cmd, shell=True, check=True, executable="/bin/bash")