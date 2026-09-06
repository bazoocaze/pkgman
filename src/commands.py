"""
commands.py – orchestrates install, remove, list, and configure commands.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from src.constants import KNOWN_MANAGERS, ManagerType, SudoSetting
from src.database import Database, PackageStore
from src.managers import ManagerRegistry
from src.output import Report, _snippet, format_package_list
from src.runner import DryRunRunner, ProcessRunner, SubprocessRunner
from src.sys_check import RealSysCheck, SysCheck
from src.ui import print_manager_summary, prompt_checkbox


@dataclass
class InstallConflictResult:
    """Result of a conflict check during install."""

    action: str  # "new" | "reinstall" | "update" | "error"
    run_source: str
    db_name: str | None = None  # existing name in DB (may differ from CLI name on rename)
    error_msg: str | None = None


class Commands:
    """Orchestrates the execution of CLI commands."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        runner: ProcessRunner | None = None,
        sys_check: SysCheck | None = None,
        dry_run: bool = False,
    ) -> None:
        self._db = Database(db_path)
        self.store = PackageStore(self._db)
        self.store.load()               # prime cache + migrate if needed
        self._sys_check = sys_check or RealSysCheck()
        actual_runner = runner or (DryRunRunner() if dry_run else SubprocessRunner())
        self.registry = ManagerRegistry(
            self.store,
            runner=actual_runner,
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

    def _check_install_conflict(self, manager: str, name: str, source: str) -> InstallConflictResult:
        """Check if *name*/*source* conflicts with existing packages of the same type.

        Returns an ``InstallConflictResult`` describing what action to take:

        * ``"new"`` — no conflict, safe to install and register.
        * ``"reinstall"`` — same name and source already match; re-run install
          without touching the DB.
        * ``"update"`` — existing entry differs from what the user wants;
          run install and update the DB record to ``{type, name, source}``.
          ``db_name`` holds the existing name (may differ from *name* when
          renaming).
        * ``"error"`` — conflict detected; check ``error_msg`` for details.
        """
        has_explicit_source = source != name

        for pkg in self.store.packages:
            if pkg["type"] != manager:
                continue

            existing_name = pkg["name"]
            existing_source = pkg.get("source")

            # Case 1: same source, different name → update (rename)
            if existing_source == source and existing_name != name:
                return InstallConflictResult(
                    action="update",
                    run_source=source,
                    db_name=existing_name,
                )

            if existing_name != name:
                # Case 6: existing name == new source, existing has no source → update (rename)
                if has_explicit_source and existing_source is None and existing_name == source:
                    return InstallConflictResult(
                        action="update",
                        run_source=source,
                        db_name=existing_name,
                    )
                continue

            # Same name ————————————————

            # Cases 3 & 5: no source change → reinstall, DB untouched
            if not has_explicit_source or existing_source == source:
                run_source = existing_source or source
                return InstallConflictResult(action="reinstall", run_source=run_source)

            # Cases 2 & 4: source changed → update DB
            return InstallConflictResult(action="update", run_source=source, db_name=name)

        # No conflict
        return InstallConflictResult(action="new", run_source=source)

    def _install_single(self, manager: str, name: str, source: str | None) -> None:
        source = source or name
        has_explicit_source = source != name

        # Name extraction from a single-argument source (custom managers only).
        # When the user provides just a source (implicit name == source) and the
        # manager has a name_regex, derive the name from the source.
        if not has_explicit_source:
            custom = self.registry.get(manager)
            if custom is not None and custom.name_regex:
                extracted = custom.extract_name(source)
                if extracted and extracted != source:
                    name = extracted
                    has_explicit_source = True

        result = self._check_install_conflict(manager, name, source)

        if result.action == "error":
            print(result.error_msg, file=sys.stderr)
            return

        # Single point of execution — run install regardless of action
        sudo = self._sudo_for(manager)
        try:
            self.registry.install(manager, name, result.run_source, sudo=sudo)
        except subprocess.CalledProcessError as e:
            print(f"Error installing {name}: exit {e.returncode}", file=sys.stderr)
            return

        # DB mutations — only if install succeeded
        if result.action == "new":
            if has_explicit_source:
                print(f"  Source: {source}")
            entry: dict = {"type": manager, "name": name}
            if has_explicit_source:
                entry["source"] = source
            self.store.add(entry)
            print(f"  -> {name} installed and registered.")
        elif result.action == "update":
            entry = {"type": manager, "name": name}
            if has_explicit_source:
                entry["source"] = source
            self.store.update(result.db_name, entry)
            print(f"  -> {name} installed and registered.")
        else:  # reinstall
            print(f"  -> {name} already registered. Reinstalled.")

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

    # -- update ----------------------------------------------------------

    def update(self, names: list[str], manager: str | None = None) -> None:
        """Update one or more packages by name from the database.

        If *manager* is given, only packages whose type matches it are updated.
        """
        if not names:
            print("No package names provided.")
            return
        for name in names:
            pkg = self.store.find(name)
            if pkg is None:
                print(f"Warning: '{name}' not found in database. Skipping.")
                continue
            if manager is not None and pkg["type"] != manager:
                print(f"Warning: '{name}' not found under '@{manager}'. Skipping.")
                continue
            mgr = pkg["type"]
            source = pkg.get("source", name)
            sudo = self._sudo_for(mgr)
            try:
                self.registry.update(mgr, name, source, sudo=sudo)
                print(f"  -> {name} updated.")
            except subprocess.CalledProcessError as e:
                print(f"  -> {name} update failed (exit {e.returncode}).")

    def update_all(self, manager: str | None = None) -> None:
        """Update all packages from the database.

        If *manager* is given, only packages of that type are updated.
        """
        packages = self.store.packages
        if manager is not None:
            packages = [p for p in packages if p["type"] == manager]
        if not packages:
            msg = (
                f"No registered packages for '@{manager}' to update."
                if manager
                else "No registered packages to update."
            )
            print(msg)
            return

        report = Report()
        for pkg in packages:
            ptype = pkg["type"]
            name = pkg["name"]
            source = pkg.get("source", name)
            sudo = self._sudo_for(ptype)
            try:
                self.registry.update(ptype, name, source, sudo=sudo)
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
        candidates: list[tuple[str, dict]] = []
        for mgr_name, mgr in KNOWN_MANAGERS.items():
            if mgr_name in managers:
                print(f"Manager '@{mgr_name}' already registered — skipping.")
                continue
            if self._sys_check.which(mgr["exe"]) is None:
                print(f"Manager '@{mgr_name}' ({mgr['exe']!r}) not found on PATH — skipping.")
                continue
            candidates.append((mgr_name, mgr))

        if not candidates:
            print("\nNo new managers found.")
            print_manager_summary(managers)
            return

        # -- select ------------------------------------------------------
        if yes:
            selected = candidates
        else:
            labels = [f"@{name:<14} ({mgr['exe']})" for name, mgr in candidates]
            selected = [candidates[i] for i in prompt_checkbox(labels)]

        # -- add ---------------------------------------------------------
        added = 0
        for mgr_name, mgr in selected:
            entry: dict = {
                "install": mgr["install"],
                "remove": mgr["remove"],
                "update": mgr["update"],
            }
            if mgr.get("name_regex"):
                entry["name_regex"] = mgr["name_regex"]
            managers[mgr_name] = entry
            added += 1
            print(f"  -> '@{mgr_name}' added.")

        if added:
            self.store.save()
            print(f"\n{added} manager(s) added to database.")
        else:
            print("\nNo managers added.")

        # -- summary ------------------------------------------------------
        print_manager_summary(managers)

    # -- doctor ----------------------------------------------------------

    def doctor(self) -> bool:
        """Run diagnostic checks and return True if no errors found."""
        from src.command_doctor import run_doctor

        report = run_doctor(self.store, self._sys_check)
        report.print()
        return not report.has_errors

    # -- list ------------------------------------------------------------

    def list(self, *, json_output: bool = False) -> None:
        """List all registered packages."""
        packages = self.store.packages
        print(format_package_list(packages, json_output=json_output))