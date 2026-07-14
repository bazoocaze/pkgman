"""
managers.py - Detection and execution of package managers

Supported: apt (Debian/Ubuntu), yum (RHEL/CentOS), brew (macOS)
"""

import subprocess
import shutil


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
        subprocess.run(cmd, check=True)

    def remove(self, package_name, sudo=False):
        """Remove a package using the manager."""
        cmd = self._build_cmd("remove", package_name)
        if sudo:
            cmd = ["sudo"] + cmd
        subprocess.run(cmd, check=True)

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
