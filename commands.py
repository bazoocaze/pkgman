"""
commands.py – orchestrates install, remove, and list commands.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from database import Database, PackageStore
from managers import ManagerRegistry
from output import Report
from constants import ManagerType, SudoSetting


class Commands:
    """Orchestrates the execution of CLI commands."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db = Database(db_path)
        self.store = PackageStore(self._db)
        self.store.load()               # prime cache + migrate if needed
        self.store.validate_managers()  # reject reserved names early
        self.registry = ManagerRegistry(self.store)

    # -- helpers ---------------------------------------------------------

    @property
    def _sudo(self) -> bool:
        return self.store.sudo == SudoSetting.YES

    def _sudo_for(self, manager: str) -> bool:
        """Sudo only applies to the built-in OS package manager."""
        return self._sudo and manager == ManagerType.PACKAGE

    # -- install ---------------------------------------------------------

    def install(
        self,
        manager: str,
        name_or_names: str | list[str],
        source: str | None = None,
    ) -> None:
        """Install packages by manager type.

        For @package, *name_or_names* is a list and each is installed via
        the OS manager.  For custom managers it is a single name.
        """
        if manager == ManagerType.PACKAGE and isinstance(name_or_names, list):
            self._install_packages(name_or_names)
        else:
            name = name_or_names if isinstance(name_or_names, str) else name_or_names[0]
            self._install_custom(manager, name, source)

    def _install_packages(self, names: list[str]) -> None:
        for name in names:
            print(f"Installing package: {name}")
            self.registry.install(ManagerType.PACKAGE, name, name, sudo=self._sudo)
            self.store.add({"type": ManagerType.PACKAGE, "name": name})
            print(f"  -> {name} installed and registered.")

    def _install_custom(self, manager: str, name: str, source: str | None) -> None:
        source = source or name
        print(f"Installing {manager} package: {name}")
        if source != name:
            print(f"  Source: {source}")
        self.registry.install(manager, name, source, sudo=False)
        entry: dict = {"type": manager, "name": name}
        if source != name:
            entry["source"] = source
        self.store.add(entry)
        print(f"  -> {name} installed and registered.")

    # -- install-all (replay) --------------------------------------------

    def install_all(self) -> None:
        """Reinstall all packages from the database (replay)."""
        packages = self.store.packages
        if not packages:
            print("No registered packages to install.")
            return

        report = Report()
        for pkg in packages:
            ptype = pkg["type"]
            name = pkg["name"]
            source = pkg.get("source", name)
            sudo = self._sudo_for(ptype)
            try:
                self.registry.install(ptype, name, source, sudo=sudo)
                report.add_ok(ptype.upper(), name, source)
            except subprocess.CalledProcessError as e:
                report.add_fail(
                    ptype.upper(), name,
                    detail=f"exit {e.returncode}",
                    snippet=Report._snippet(stderr=e.stderr, stdout=e.stdout),
                )
            except Exception as e:
                report.add_fail(ptype.upper(), name, detail=str(e))

        report.print()

    # -- remove ----------------------------------------------------------

    def remove(self, manager: str, name: str) -> None:
        """Remove a package by name.

        If *manager* is @auto, resolves automatically by searching the
        database by name, then by source.
        """
        if manager == ManagerType.AUTO:
            result = self.registry.resolve_auto(name)
            if result is None:
                print(f"Warning: '{name}' not found in database. Skipping.")
                return
            manager, pkg = result
        else:
            pkg = self.store.find(name)
            if pkg is None:
                print(f"Warning: '{name}' not found in database. Skipping.")
                return

        print(f"Removing {manager} package: {name}")
        source = pkg.get("source", name)
        sudo = self._sudo_for(manager)
        self.registry.remove(manager, name, source, sudo=sudo)
        self.store.remove(name)
        print(f"  -> {name} removed from database.")

    # -- list ------------------------------------------------------------

    def list(self, *, json_output: bool = False) -> None:
        """List all registered packages."""
        packages = self.store.packages
        if not packages:
            print("[]" if json_output else "No registered packages.")
            return

        if json_output:
            print(json.dumps(packages, indent=2))
            return

        for pkg in packages:
            ptype = pkg["type"]
            name = pkg["name"]
            source = pkg.get("source", "")
            if ptype == ManagerType.PACKAGE:
                print(f"PACKAGE  {name}")
            elif source:
                print(f"{ptype.upper():8} {name}  {source}")
            else:
                print(f"{ptype.upper():8} {name}")