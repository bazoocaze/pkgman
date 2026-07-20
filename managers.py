"""
managers.py – detection and execution of package managers.

Supported OS managers: apt (Debian/Ubuntu), yum (RHEL/CentOS), brew (macOS).
Custom managers defined in the JSON database are executed with placeholder substitution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from constants import ManagerType
from runner import ProcessRunner, SubprocessRunner
from sys_check import RealSysCheck, SysCheck


# ---------------------------------------------------------------------------
# OS-level package manager
# ---------------------------------------------------------------------------

def detect_os_manager(*, sys_check: SysCheck | None = None) -> Manager | None:
    """Detect the available package manager on the system.

    Preference order: brew → apt → yum.
    Returns None if none is found.
    """
    sc = sys_check or RealSysCheck()
    for name in ("brew", "apt", "yum"):
        if sc.which(name):
            return Manager(name)
    return None


class Manager:
    """Represents an OS package manager (apt / yum / brew)."""

    def __init__(self, name: str, *, runner: ProcessRunner | None = None) -> None:
        self.name = name
        self._runner = runner or SubprocessRunner()

    def install(self, package_name: str, *, sudo: bool = False) -> None:
        """Install a package."""
        self._run("install", package_name, sudo)

    def remove(self, package_name: str, *, sudo: bool = False) -> None:
        """Remove a package."""
        self._run("remove", package_name, sudo)

    def _run(self, action: str, package_name: str, sudo: bool) -> None:
        cmd = self._build_cmd(action, package_name)
        if sudo:
            cmd = ["sudo", *cmd]
        self._runner.run(cmd)

    def _build_cmd(self, action: str, package_name: str) -> list[str]:
        """Build the argument list for this manager."""
        if self.name in ("apt", "yum"):
            return [self.name, action, "-y", package_name]
        if self.name == "brew":
            resolved = "uninstall" if action == "remove" else action
            return [self.name, resolved, package_name]
        raise ValueError(f"Unknown manager: {self.name}")


# ---------------------------------------------------------------------------
# Custom manager (from JSON)
# ---------------------------------------------------------------------------

@dataclass
class CustomManager:
    """Represents a custom manager defined in the JSON database."""

    name: str
    install_cmd: list[str] | str | None = None
    remove_cmd: list[str] | str | None = None

    @classmethod
    def from_dict(cls, name: str, data: dict) -> CustomManager:
        """Construct a CustomManager from a dictionary."""
        return cls(
            name=name,
            install_cmd=data.get("install"),
            remove_cmd=data.get("remove"),
        )


# ---------------------------------------------------------------------------
# Protocol – minimal store interface
# ---------------------------------------------------------------------------

@runtime_checkable
class ManagerStore(Protocol):
    """Minimal interface expected by ManagerRegistry for a package store."""

    @property
    def managers(self) -> dict[str, dict[str, str | list[str] | None]]:
        ...

    @property
    def packages(self) -> list[dict]:
        ...

    def find(self, name: str) -> dict | None:
        ...


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _substitute(
    cmd: list[str] | str | None, name: str, source: str
) -> list[str] | str | None:
    """Substitute {name} and {source} placeholders in a command template."""
    if cmd is None:
        return None
    if isinstance(cmd, str):
        return cmd.replace("{name}", name).replace("{source}", source)
    return [part.replace("{name}", name).replace("{source}", source) for part in cmd]


# ---------------------------------------------------------------------------
# Registry – routes install/remove to the correct manager
# ---------------------------------------------------------------------------

@dataclass
class ManagerRegistry:
    """Unifies built-in @package manager with custom managers from JSON."""

    store: ManagerStore = field(repr=False)
    runner: ProcessRunner = field(default_factory=SubprocessRunner, repr=False)
    sys_check: SysCheck = field(default_factory=RealSysCheck, repr=False)

    def _detect_os_manager(self) -> Manager:
        """Detect an OS-level manager or raise RuntimeError if none found."""
        mgr = detect_os_manager(sys_check=self.sys_check)
        if mgr is None:
            raise RuntimeError("No package manager detected (apt/yum/brew)")
        # Inject our runner so the OS manager uses the same runner
        mgr._runner = self.runner
        return mgr

    def get(self, manager_name: str) -> CustomManager | None:
        """Return a custom manager by name, or None for the built-in @package."""
        if manager_name == ManagerType.PACKAGE:
            return None
        mgr = self.store.managers.get(manager_name)
        if mgr is None:
            return None
        return CustomManager.from_dict(name=manager_name, data=mgr)

    def install(self, manager_name: str, name: str, source: str, *, sudo: bool = False) -> None:
        """Route install to the appropriate manager."""
        custom = self.get(manager_name)
        if custom is None:
            mgr = self._detect_os_manager()
            mgr.install(name, sudo=sudo)
            return

        cmd = _substitute(custom.install_cmd, name, source)
        if cmd is not None:
            self.runner.run(cmd, shell=isinstance(cmd, str))

    def remove(self, manager_name: str, name: str, source: str, *, sudo: bool = False) -> None:
        """Route remove to the appropriate manager."""
        custom = self.get(manager_name)
        if custom is None:
            mgr = self._detect_os_manager()
            mgr.remove(name, sudo=sudo)
            return

        cmd = _substitute(custom.remove_cmd, name, source)
        if cmd is not None:
            self.runner.run(cmd, shell=isinstance(cmd, str))

    def resolve_auto(self, name_or_source: str) -> tuple[str, dict] | None:
        """@auto: search DB by name, then by source.

        Returns (manager_name, package_dict) or None.
        If ambiguous (>1 match), raises ValueError.
        """
        pkg = self.store.find(name_or_source)
        if pkg is not None:
            return (pkg["type"], pkg)

        packages = self.store.packages
        matches = [p for p in packages if p.get("source") == name_or_source]
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous: {len(matches)} packages match source "
                f"'{name_or_source}'. Specify a manager explicitly."
            )
        if len(matches) == 1:
            return (matches[0]["type"], matches[0])
        return None