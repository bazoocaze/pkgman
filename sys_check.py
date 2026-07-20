"""
sys_check.py – abstraction over system-level checks (which, path, etc.)
for testability.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SysCheck(Protocol):
    """Executes OS checks. Mocked in tests to avoid depending on PATH."""

    def which(self, executable: str) -> str | None:
        ...


class RealSysCheck:
    """Real implementation using shutil.which."""

    def which(self, executable: str) -> str | None:
        import shutil

        return shutil.which(executable)
