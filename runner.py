"""
runner.py – process execution abstraction for testability.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Protocol


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class ProcessRunner(Protocol):
    """Executes CLI commands. Mocked in tests to avoid real subprocess calls."""

    def run(self, cmd: list[str] | str, *, shell: bool = False) -> None:
        """Execute *cmd*. Must raise CalledProcessError on failure."""
        ...


# ---------------------------------------------------------------------------
# Real implementation
# ---------------------------------------------------------------------------

@dataclass
class SubprocessRunner(ProcessRunner):
    """Runs commands via ``subprocess.run``."""

    def run(self, cmd: list[str] | str, *, shell: bool = False) -> None:
        """Execute *cmd*, raising CalledProcessError on failure.

        Warning: When *shell* is True, *cmd* should be a string and is
        passed to the shell — this can pose a shell-injection risk if the
        command contains untrusted input.
        """
        if isinstance(cmd, str) and not shell:
            raise ValueError(
                "String command requires shell=True; pass a list or set shell=True"
            )
        result = subprocess.run(cmd, shell=shell)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd)