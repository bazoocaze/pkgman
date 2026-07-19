"""
database.py – JSON-backed storage with in-memory cache.

Architecture:
  Database      – low-level JSON read/write (no cache, no domain logic)
  PackageStore  – cache layer + domain operations on top of Database
"""

import json
from pathlib import Path

from constants import (
    DB_VERSION,
    DEFAULT_MANAGERS,
    RESERVED_MANAGERS,
    ManagerType,
    SudoSetting,
)


# ---------------------------------------------------------------------------
# Database – raw I/O
# ---------------------------------------------------------------------------

class Database:
    """Read and write the JSON database file. Stateless – every call hits the disk."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else Path.home() / ".config" / ".pkgman_database.json"

    def read(self) -> dict:
        """Return the raw data dict from disk, or a safe empty default."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            return self._empty()
        try:
            with open(self.path) as f:
                data = json.load(f)
            # Basic structural validation
            if not isinstance(data, dict):
                return self._empty()
        except (json.JSONDecodeError, KeyError):
            return self._empty()
        return data

    def write(self, data: dict) -> None:
        """Persist the data dict to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _empty() -> dict:
        return {
            "version": DB_VERSION,
            "sudo": SudoSetting.NO,
            "managers": dict(DEFAULT_MANAGERS),
            "packages": [],
        }


# ---------------------------------------------------------------------------
# PackageStore – cache + domain logic
# ---------------------------------------------------------------------------

class PackageStore:
    """Wraps Database with in-memory caching and domain operations.

    Loads once from disk on first access; subsequent operations keep state
    in memory until the next explicit save().
    """

    def __init__(self, db: Database) -> None:
        self._db = db
        self._loaded = False
        self._packages: list[dict] = []
        self._sudo: str = SudoSetting.NO
        self._managers: dict[str, dict[str, list[str] | str | None]] = {}

    # -- cache helpers --

    def _ensure_loaded(self) -> None:
        """Populate cache from disk if not already loaded."""
        if self._loaded:
            return
        data = self._db.read()
        self._packages = data.get("packages", [])
        self._sudo = data.get("sudo", SudoSetting.NO)
        self._managers = data.get("managers", dict(DEFAULT_MANAGERS))
        if self._migrate(data):
            self._db.write(data)
        self._loaded = True
        self.validate_managers()

    def _migrate(self, data: dict) -> bool:
        """Handle v1 → v2 migration if needed.

        Returns True if data was migrated (caller should persist).
        """
        version = data.get("version", 1)
        if version >= DB_VERSION:
            return False
        # v1 → v2: inject managers + bump version
        self._managers = dict(DEFAULT_MANAGERS)
        data["version"] = DB_VERSION
        data["managers"] = dict(DEFAULT_MANAGERS)
        return True

    def validate_managers(self) -> None:
        """Raise ValueError if any custom manager uses a reserved name."""
        for key in self._managers or {}:
            if key in RESERVED_MANAGERS:
                raise ValueError(
                    f"Manager name '{key}' is reserved and cannot be used as a custom manager"
                )

    def _invalidate(self) -> None:
        """Force reload on next access (useful for tests)."""
        self._loaded = False

    # -- public properties --

    @property
    def sudo(self) -> str:
        self._ensure_loaded()
        return self._sudo

    @sudo.setter
    def sudo(self, value: str) -> None:
        self._ensure_loaded()
        self._sudo = value

    @property
    def managers(self) -> dict:
        self._ensure_loaded()
        return self._managers

    @property
    def packages(self) -> list[dict]:
        """Return a copy of the package list."""
        self._ensure_loaded()
        return list(self._packages)

    # -- public methods --

    def load(self) -> list[dict]:
        """Load packages (from cache or disk). Returns the package list."""
        self._ensure_loaded()
        return self.packages

    def save(self) -> None:
        """Persist current state to disk."""
        if not self._loaded:
            raise RuntimeError("store not loaded; call load() first")
        self._db.write({
            "version": DB_VERSION,
            "sudo": self._sudo,
            "managers": self._managers,
            "packages": self._packages,
        })

    def add(self, package: dict) -> None:
        """Add a package, ignoring duplicates by name."""
        self._ensure_loaded()
        for pkg in self._packages:
            if pkg["name"] == package["name"]:
                return
        self._packages.append(package)
        self.save()

    def remove(self, name: str) -> None:
        """Remove a package by name from the store."""
        self._ensure_loaded()
        self._packages = [p for p in self._packages if p["name"] != name]
        self.save()

    def find(self, name: str) -> dict | None:
        """Find a package by name."""
        self._ensure_loaded()
        for pkg in self._packages:
            if pkg["name"] == name:
                return pkg
        return None

    def find_by_source(self, source: str) -> dict | None:
        """Find a package by its source field."""
        self._ensure_loaded()
        for pkg in self._packages:
            if pkg.get("source") == source:
                return pkg
        return None