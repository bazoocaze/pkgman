"""
commands.py – orchestrates install, remove, list, and configure commands.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from constants import KNOWN_MANAGERS, ManagerType, SudoSetting
from database import Database, PackageStore
from managers import ManagerRegistry
from output import Report, _snippet, format_package_list
from runner import ProcessRunner, SubprocessRunner
from sys_check import RealSysCheck, SysCheck
from ui import print_manager_summary, prompt_checkbox


class Commands:
    """Orchestrates the execution of CLI commands."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        runner: ProcessRunner | None = None,
        sys_check: SysCheck | None = None,
    ) -> None:
        self._db = Database(db_path)
        self.store = PackageStore(self._db)
        self.store.load()               # prime cache + migrate if needed
        self._sys_check = sys_check or RealSysCheck()
        self.registry = ManagerRegistry(
            self.store,
            runner=runner or SubprocessRunner(),
            sys_check=self._sys_check,
        )

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
            for name in name_or_names:
                self._install_single(manager, name, name)
        else:
            name = name_or_names if isinstance(name_or_names, str) else name_or_names[0]
            self._install_single(manager, name, source)

    def _install_single(self, manager: str, name: str, source: str | None) -> None:
        source = source or name
        print(f"Installing {manager} package: {name}")
        sudo = self._sudo_for(manager)
        if source != name:
            print(f"  Source: {source}")
        self.registry.install(manager, name, source, sudo=sudo)
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
                    snippet=_snippet(stderr=e.stderr, stdout=e.stdout),
                )
            except Exception as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
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

    # -- configure --------------------------------------------------------

    def configure(self, *, yes: bool = False) -> None:
        """Scan for known managers on the system and offer to add them.

        In interactive mode (default), shows a checkbox-style list of all
        newly detected managers and lets the user pick which ones to add.

        If *yes* is True, automatically add all detected managers without
        prompting (non-interactive mode).
        """
        managers = self.store.managers

        # -- collect candidates ------------------------------------------
        candidates: list[tuple[str, str, list[str] | str, list[str] | str | None]] = []
        for mgr_name, (exe, install_cmd, remove_cmd) in KNOWN_MANAGERS.items():
            if mgr_name in managers:
                print(f"Manager '@{mgr_name}' already registered — skipping.")
                continue
            if self._sys_check.which(exe) is None:
                print(f"Manager '@{mgr_name}' ({exe!r}) not found on PATH — skipping.")
                continue
            candidates.append((mgr_name, exe, install_cmd, remove_cmd))

        if not candidates:
            print("\nNo new managers found.")
            print_manager_summary(managers)
            return

        # -- select ------------------------------------------------------
        if yes:
            selected = candidates
        else:
            selected = prompt_checkbox(candidates)

        # -- add ---------------------------------------------------------
        added = 0
        for mgr_name, _exe, install_cmd, remove_cmd in selected:
            managers[mgr_name] = {
                "install": install_cmd,
                "remove": remove_cmd,
            }
            added += 1
            print(f"  -> '@{mgr_name}' added.")

        if added:
            self.store.save()
            print(f"\n{added} manager(s) added to database.")
        else:
            print("\nNo managers added.")

        # -- summary ------------------------------------------------------
        print_manager_summary(managers)

    # -- list ------------------------------------------------------------

    def list(self, *, json_output: bool = False) -> None:
        """List all registered packages."""
        packages = self.store.packages
        print(format_package_list(packages, json_output=json_output))