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
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, executable="/bin/bash")
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )