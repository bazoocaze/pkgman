"""
commands.py – orchestrates install, remove, list, and configure commands.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from constants import KNOWN_MANAGERS, RESERVED_MANAGERS, ManagerType, SudoSetting
from database import Database, PackageStore
from managers import ManagerRegistry
from output import Report, _snippet, format_package_list
from runner import ProcessRunner, SubprocessRunner


class Commands:
    """Orchestrates the execution of CLI commands."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        runner: ProcessRunner | None = None,
    ) -> None:
        self._db = Database(db_path)
        self.store = PackageStore(self._db)
        self.store.load()               # prime cache + migrate if needed
        self.registry = ManagerRegistry(self.store, runner=runner or SubprocessRunner())

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
            if shutil.which(exe) is None:
                print(f"Manager '@{mgr_name}' ({exe!r}) not found on PATH — skipping.")
                continue
            candidates.append((mgr_name, exe, install_cmd, remove_cmd))

        if not candidates:
            print("\nNo new managers found.")
            self._print_manager_summary()
            return

        # -- select ------------------------------------------------------
        if yes:
            selected = candidates
        else:
            selected = self._prompt_checkbox(candidates)

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
        self._print_manager_summary()

    @staticmethod
    def _prompt_checkbox(
        candidates: list[tuple[str, str, list[str] | str, list[str] | str | None]],
    ) -> list[tuple[str, str, list[str] | str, list[str] | str | None]]:
        """Show a numbered checkbox list and return selected items.

        Input format: space- or comma-separated numbers, ranges (1-3),
        'all', or empty for none.  Repeat until valid.
        """
        print(f"\nFound {len(candidates)} new manager(s):")
        for i, (mgr_name, exe, _install, _remove) in enumerate(candidates, 1):
            print(f"  [{i}] @{mgr_name:<14} ({exe})")
        print()
        while True:
            answer = input(
                "Select managers to add (numbers, e.g. '1 3' or '1-3' or 'all'): "
            ).strip().lower()
            if answer in ("", "none"):
                return []
            if answer == "all":
                return candidates
            selected: list[int] = []
            try:
                for part in answer.replace(",", " ").split():
                    if "-" in part:
                        a, b = part.split("-", 1)
                        selected.extend(range(int(a), int(b) + 1))
                    else:
                        selected.append(int(part))
            except ValueError:
                print(f"  Invalid input: '{answer}'. Try again.")
                continue
            selected = sorted(set(selected))
            if not selected or selected[0] < 1 or selected[-1] > len(candidates):
                print(f"  Numbers out of range (1-{len(candidates)}). Try again.")
                continue
            return [candidates[i - 1] for i in selected]

    def _print_manager_summary(self) -> None:
        """Print a summary of all registered custom managers."""
        print("\nRegistered custom managers:")
        custom_managers = {
            k: v for k, v in self.store.managers.items()
            if k not in RESERVED_MANAGERS
        }
        if not custom_managers:
            print("  (none)")
        else:
            for name, cfg in sorted(custom_managers.items()):
                has_install = "🔧" if cfg.get("install") else "  "
                has_remove = "🗑️" if cfg.get("remove") else "  "
                print(f"  @{name:<12} {has_install} install  {has_remove} remove")

    # -- list ------------------------------------------------------------

    def list(self, *, json_output: bool = False) -> None:
        """List all registered packages."""
        packages = self.store.packages
        print(format_package_list(packages, json_output=json_output))