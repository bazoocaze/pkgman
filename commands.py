"""
commands.py - Orchestrates install, remove, list commands
"""

import sys
from database import Database
from managers import Manager
from scripts import ScriptRunner


class Commands:
    """Orchestrates the execution of CLI commands."""

    def __init__(self, db_path=None):
        self.db = Database(db_path)
        self.db.load()  # loads the sudo flag (if file exists)
        self.manager = Manager.detect()
        if self.manager is None:
            print(
                "Error: No supported package manager found.\n"
                "  Need: apt, yum or brew.",
                file=sys.stderr,
            )
            sys.exit(1)

    @property
    def _use_sudo(self):
        return self.db.sudo == "yes"

    def install(self, names):
        """Install OS packages by name."""
        for name in names:
            print(f"Installing package: {name}")
            self.manager.install(name, sudo=self._use_sudo)
            self.db.add({"type": "package", "name": name})
            print(f"  -> {name} installed and registered.")

    def install_url(self, name, url):
        """Install a script from a URL."""
        print(f"Installing script: {name}")
        print(f"  URL: {url}")
        ScriptRunner.run(url)
        self.db.add({"type": "script", "name": name, "url": url})
        print(f"  -> {name} installed and registered.")

    def install_all(self):
        """Reinstall all packages from the database (replay)."""
        packages = self.db.load()
        if not packages:
            print("No registered packages to install.")
            return

        for pkg in packages:
            if pkg["type"] == "package":
                print(f"Installing package: {pkg['name']}")
                self.manager.install(pkg["name"], sudo=self._use_sudo)
            elif pkg["type"] == "script":
                print(f"Installing script: {pkg['name']}")
                print(f"  URL: {pkg['url']}")
                ScriptRunner.run(pkg["url"])
        print("Replay complete.")

    def remove(self, names):
        """Remove packages by name."""
        for name in names:
            pkg = self.db.find(name)
            if pkg is None:
                print(f"Warning: '{name}' not found in database. Skipping.")
                continue

            if pkg["type"] == "package":
                print(f"Removing package: {name}")
                self.manager.remove(name, sudo=self._use_sudo)

            self.db.remove(name)
            print(f"  -> {name} removed from database.")

    def list(self):
        """List all registered packages."""
        packages = self.db.load()
        if not packages:
            print("No registered packages.")
            return

        for pkg in packages:
            if pkg["type"] == "package":
                print(f"PACKAGE  {pkg['name']}")
            elif pkg["type"] == "script":
                print(f"SCRIPT   {pkg['name']}")
                print(f"         {pkg['url']}")