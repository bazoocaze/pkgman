"""
managers.py - Detection and execution of package managers

Supported: apt (Debian/Ubuntu), yum (RHEL/CentOS), brew (macOS)
"""

import subprocess
import shutil
from dataclasses import dataclass


class Manager:
    """Represents an OS package manager."""

    def __init__(self, name):
        self.name = name

    @staticmethod
    def detect():
        """Detect the available package manager on the system.

        Preference order: brew -> apt -> yum
        Returns None if none is found.
        """
        for mgr in ["brew", "apt", "yum"]:
            if shutil.which(mgr):
                return Manager(mgr)
        return None

    def install(self, package_name, sudo=False):
        """Install a package using the manager."""
        cmd = self._build_cmd("install", package_name)
        if sudo:
            cmd = ["sudo"] + cmd
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )

    def remove(self, package_name, sudo=False):
        """Remove a package using the manager."""
        cmd = self._build_cmd("remove", package_name)
        if sudo:
            cmd = ["sudo"] + cmd
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )

    def _build_cmd(self, action, package_name):
        """Build the argument list for subprocess."""
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


@dataclass
class CustomManager:
    """Represents a custom manager defined in the JSON database."""

    name: str
    install_cmd: list[str] | str | None
    remove_cmd: list[str] | str | None


class ManagerRegistry:
    """Unifies built-in @package manager with custom managers from JSON."""

    def __init__(self, db):
        self.db = db

    def get(self, manager_name: str) -> CustomManager | None:
        """Return a custom manager by name, or None if it's @package (built-in)."""
        if manager_name == "package":
            return None
        managers = self.db.managers if hasattr(self.db, "managers") else {}
        mgr = managers.get(manager_name)
        if mgr is None:
            return None
        return CustomManager(
            name=manager_name,
            install_cmd=mgr.get("install"),
            remove_cmd=mgr.get("remove"),
        )

    def install(self, manager_name: str, name: str, source: str, sudo: bool):
        """Route install to @package (built-in) or execute custom manager."""
        custom = self.get(manager_name)
        if custom is None:
            # Use built-in @package manager
            mgr = Manager.detect()
            if mgr is None:
                raise RuntimeError("No package manager detected (apt/yum/brew)")
            mgr.install(name, sudo=sudo)
            return

        cmd = self._substitute(custom.install_cmd, name, source)
        if cmd is None:
            return
        self._run_command(cmd)

    def remove(self, manager_name: str, name: str, source: str, sudo: bool):
        """Route remove to @package (built-in) or execute custom manager."""
        custom = self.get(manager_name)
        if custom is None:
            # Use built-in @package manager
            mgr = Manager.detect()
            if mgr is None:
                raise RuntimeError("No package manager detected (apt/yum/brew)")
            mgr.remove(name, sudo=sudo)
            return

        cmd = self._substitute(custom.remove_cmd, name, source)
        if cmd is None:
            # DB-only removal, do nothing
            return
        self._run_command(cmd)

    def resolve_auto(self, name_or_source: str) -> tuple[str, dict] | None:
        """@auto: search DB by name, then by source.

        Returns (manager_name, package_dict) or None.
        If ambiguous (>1 match), raises ValueError.
        """
        # Search by name first
        pkg = self.db.find(name_or_source)
        if pkg is not None:
            return (pkg["type"], pkg)

        # Search by source
        packages = self.db.load()
        matches = [p for p in packages if p.get("source") == name_or_source]
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous: {len(matches)} packages match source '{name_or_source}'. "
                f"Specify a manager explicitly."
            )
        if len(matches) == 1:
            return (matches[0]["type"], matches[0])

        return None

    @staticmethod
    def _substitute(cmd: list[str] | str | None, name: str, source: str) -> list[str] | str | None:
        """Substitute {name} and {source} placeholders in a command."""
        if cmd is None:
            return None
        if isinstance(cmd, str):
            return cmd.replace("{name}", name).replace("{source}", source)
        return [part.replace("{name}", name).replace("{source}", source) for part in cmd]

    @staticmethod
    def _run_command(cmd: list[str] | str):
        """Execute a command, raising CalledProcessError on failure."""
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
