"""
database.py - Read and write ~/.config/.pkgman_database.json

Format:
{
    "version": 1,
    "sudo": "no",
    "packages": [
        {"type": "package", "name": "git"},
        {"type": "script",  "name": "uv", "url": "https://..."}
    ]
}
"""

import json
from pathlib import Path


class Database:
    """Manages the database of manually installed packages."""

    def __init__(self, path=None):
        self.path = Path(path) if path else Path.home() / ".config" / ".pkgman_database.json"
        self.sudo = "no"

    def load(self):
        """Return the list of packages from the file.
        If the file doesn't exist or is empty/malformed, return an empty list."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            self.sudo = "no"
            return []
        try:
            with open(self.path) as f:
                data = json.load(f)
            self.sudo = data.get("sudo", "no")
            return data.get("packages", [])
        except (json.JSONDecodeError, KeyError):
            self.sudo = "no"
            return []

    def save(self, packages):
        """Save the list of packages to the file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": 1, "sudo": self.sudo, "packages": packages}
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def add(self, package):
        """Add a package, ignoring duplicates by name."""
        packages = self.load()
        for pkg in packages:
            if pkg["name"] == package["name"]:
                return  # already exists, skip
        packages.append(package)
        self.save(packages)

    def remove(self, name):
        """Remove a package from the database by name."""
        packages = self.load()
        packages = [p for p in packages if p["name"] != name]
        self.save(packages)

    def find(self, name):
        """Find a package by name. Returns None if not found."""
        for pkg in self.load():
            if pkg["name"] == name:
                return pkg
        return None