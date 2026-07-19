"""
managers.py – detection and execution of package managers.

Supported OS managers: apt (Debian/Ubuntu), yum (RHEL/CentOS), brew (macOS).
Custom managers defined in the JSON database are executed with placeholder substitution.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from constants import ManagerType


# ---------------------------------------------------------------------------
# OS-level package manager
# ---------------------------------------------------------------------------

class Manager:
    """Represents an OS package manager (apt / yum / brew)."""

    def __init__(self, name: str) -> None:
        self.name = name

    @staticmethod
    def detect() -> Manager | None:
        """Detect the available package manager on the system.

        Preference order: brew → apt → yum.
        Returns None if none is found.
        """
        for name in ("brew", "apt", "yum"):
            if shutil.which(name):
                return Manager(name)
        return None

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
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )

    def _build_cmd(self, action: str, package_name: str) -> list[str]:
        """Build the argument list for this manager."""
        if self.name in ("apt", "yum"):
            return [self.name, action, "-y", package_name]
        if self.name == "brew":
            resolved = "uninstall" if action == "remove" else action
            return [self.name, resolved, package_name]
        raise RuntimeError(f"Unknown manager: {self.name}")


# ---------------------------------------------------------------------------
# Custom manager (from JSON)
# ---------------------------------------------------------------------------

@dataclass
class CustomManager:
    """Represents a custom manager defined in the JSON database."""

    name: str
    install_cmd: list[str] | str | None = None
    remove_cmd: list[str] | str | None = None


# ---------------------------------------------------------------------------
# Registry – routes install/remove to the correct manager
# ---------------------------------------------------------------------------

@dataclass
class ManagerRegistry:
    """Unifies built-in @package manager with custom managers from JSON."""

    store: object = field(repr=False)  # PackageStore

    def get(self, manager_name: str) -> CustomManager | None:
        """Return a custom manager by name, or None for the built-in @package."""
        if manager_name == ManagerType.PACKAGE:
            return None
        mgr = self.store.managers.get(manager_name)
        if mgr is None:
            return None
        return CustomManager(
            name=manager_name,
            install_cmd=mgr.get("install"),
            remove_cmd=mgr.get("remove"),
        )

    def install(self, manager_name: str, name: str, source: str, *, sudo: bool = False) -> None:
        """Route install to the appropriate manager."""
        custom = self.get(manager_name)
        if custom is None:
            mgr = Manager.detect()
            if mgr is None:
                raise RuntimeError("No package manager detected (apt/yum/brew)")
            mgr.install(name, sudo=sudo)
            return

        cmd = self._substitute(custom.install_cmd, name, source)
        if cmd is not None:
            self._run_command(cmd)

    def remove(self, manager_name: str, name: str, source: str, *, sudo: bool = False) -> None:
        """Route remove to the appropriate manager."""
        custom = self.get(manager_name)
        if custom is None:
            mgr = Manager.detect()
            if mgr is None:
                raise RuntimeError("No package manager detected (apt/yum/brew)")
            mgr.remove(name, sudo=sudo)
            return

        cmd = self._substitute(custom.remove_cmd, name, source)
        if cmd is not None:
            self._run_command(cmd)

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

    # -- helpers --

    @staticmethod
    def _substitute(
        cmd: list[str] | str | None, name: str, source: str
    ) -> list[str] | str | None:
        """Substitute {name} and {source} placeholders in a command template."""
        if cmd is None:
            return None
        if isinstance(cmd, str):
            return cmd.replace("{name}", name).replace("{source}", source)
        return [part.replace("{name}", name).replace("{source}", source) for part in cmd]

    @staticmethod
    def _run_command(cmd: list[str] | str) -> None:
        """Execute a command, raising CalledProcessError on failure."""
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )