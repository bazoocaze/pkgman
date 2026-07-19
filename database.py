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


DEFAULT_MANAGERS = {
    "uv": {
        "install": ["uv", "tool", "install", "{source}"],
        "remove": ["uv", "tool", "uninstall", "{name}"],
    },
    "script": {
        "install": "curl -fsSL {source} | bash",
        "remove": None,
    },
}


_RESERVED_MANAGERS = {"package", "auto"}


class Database:
    """Manages the database of manually installed packages."""

    def __init__(self, path=None):
        self.path = Path(path) if path else Path.home() / ".config" / ".pkgman_database.json"
        self.sudo = "no"
        self.version = 2
        self.managers = {}

    def load(self):
        """Return the list of packages from the file.
        If the file doesn't exist or is empty/malformed, return an empty list."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            self.sudo = "no"
            self.version = 2
            self.managers = dict(DEFAULT_MANAGERS)
            return []
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, KeyError):
            self.sudo = "no"
            self.version = 2
            self.managers = dict(DEFAULT_MANAGERS)
            return []

        self.sudo = data.get("sudo", "no")
        version = data.get("version", 1)

        if version == 1:
            # Migrate v1 -> v2
            self.version = 2
            self.managers = dict(DEFAULT_MANAGERS)
            data["version"] = 2
            data["managers"] = dict(DEFAULT_MANAGERS)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(data, f, indent=2)
            return data.get("packages", [])

        # v2 path
        self.version = 2
        raw_managers = data.get("managers", {})
        if not raw_managers:
            self.managers = dict(DEFAULT_MANAGERS)
        else:
            # Validate reserved names
            for key in raw_managers:
                if key in _RESERVED_MANAGERS:
                    raise ValueError(
                        f"Manager name '{key}' is reserved and cannot be used as a custom manager"
                    )
            self.managers = dict(raw_managers)
        return data.get("packages", [])

    def save(self, packages):
        """Save the list of packages to the file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 2,
            "sudo": self.sudo,
            "managers": self.managers,
            "packages": packages,
        }
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

    def find_by_source(self, source):
        """Find a package by its source field. Returns None if not found."""
        for pkg in self.load():
            if pkg.get("source") == source:
                return pkg
        return None