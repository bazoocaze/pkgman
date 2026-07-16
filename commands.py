"""
commands.py - Orchestrates install, remove, list commands
"""

import json
import sys
from database import Database
from managers import Manager
from scripts import ScriptRunner
from uv_tools import UvTool


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

    def install_uv(self, name, source=None):
        """Install a Python tool via uv."""
        if source is None:
            source = name
        print(f"Installing uv tool: {name}")
        print(f"  Source: {source}")
        UvTool.install(source)
        self.db.add({"type": "uv", "name": name, "source": source})
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
            elif pkg["type"] == "uv":
                print(f"Installing uv tool: {pkg['name']}")
                print(f"  Source: {pkg['source']}")
                UvTool.install(pkg["source"])
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
            elif pkg["type"] == "uv":
                print(f"Removing uv tool: {name}")
                UvTool.remove(name)

            self.db.remove(name)
            print(f"  -> {name} removed from database.")

    def list(self, json_output=False):
        """List all registered packages."""
        packages = self.db.load()
        if not packages:
            if json_output:
                print(json.dumps([], indent=2))
            else:
                print("No registered packages.")
            return

        if json_output:
            print(json.dumps(packages, indent=2))
        else:
            for pkg in packages:
                if pkg["type"] == "package":
                    print(f"PACKAGE  {pkg['name']}")
                elif pkg["type"] == "script":
                    print(f"SCRIPT   {pkg['name']}  {pkg['url']}")
                elif pkg["type"] == "uv":
                    print(f"UV       {pkg['name']}  {pkg['source']}")