"""
doctor.py – diagnostic checks for pkgman.

Checks database integrity, OS package manager detection, manager
executability on PATH, duplicate package names, and type-to-manager
alignment. Produces a report with ok/warning/error states.
"""

from __future__ import annotations

import json
from typing import Any

from src.constants import DB_VERSION, KNOWN_MANAGERS
from src.output import _Colors


# ---------------------------------------------------------------------------
# DoctorReport
# ---------------------------------------------------------------------------

class DoctorReport:
    """Accumulates check results and prints a formatted summary.

    Methods: ok(), warn(), error() append entries.
    Property: has_errors is True when at least one error entry exists.
    Method: print() renders the full report to stdout.
    """

    def __init__(self) -> None:
        self._entries: list[dict[str, str]] = []

    def ok(self, detail: str) -> None:
        """Append a successful check."""
        self._entries.append({"status": "ok", "detail": detail})

    def warn(self, detail: str) -> None:
        """Append a warning check."""
        self._entries.append({"status": "warn", "detail": detail})

    def error(self, detail: str) -> None:
        """Append a failing check."""
        self._entries.append({"status": "error", "detail": detail})

    @property
    def has_errors(self) -> bool:
        """True if any entry has status 'error'."""
        return any(e["status"] == "error" for e in self._entries)

    def print(self) -> None:
        """Render the report to stdout with ANSI-colored icons and a summary."""
        C = _Colors
        ok_count = sum(1 for e in self._entries if e["status"] == "ok")
        warn_count = sum(1 for e in self._entries if e["status"] == "warn")
        error_count = sum(1 for e in self._entries if e["status"] == "error")

        out_lines: list[str] = []
        for entry in self._entries:
            if entry["status"] == "ok":
                icon = f"{C.OK()}✅{C.RESET()}"
            elif entry["status"] == "warn":
                icon = f"{C.WARN()}⚠️{C.RESET()}"
            else:
                icon = f"{C.FAIL()}❌{C.RESET()}"
            out_lines.append(f"  {icon}  {entry['detail']}")

        # Summary line – color depends on severity
        if error_count > 0:
            summary = (
                f"{C.FAIL()}Summary: {ok_count} ok, "
                f"{warn_count} warning(s), {error_count} error(s){C.RESET()}"
            )
        elif warn_count > 0:
            summary = (
                f"{C.WARN()}Summary: {ok_count} ok, "
                f"{warn_count} warning(s), {error_count} error(s){C.RESET()}"
            )
        else:
            summary = (
                f"{C.OK()}Summary: {ok_count} ok, "
                f"{warn_count} warning(s), {error_count} error(s){C.RESET()}"
            )

        out_lines.append(summary)
        print("\n".join(out_lines))


# ---------------------------------------------------------------------------
# run_doctor – entry point
# ---------------------------------------------------------------------------

def run_doctor(store: Any, sys_check: Any) -> DoctorReport:
    """Run all diagnostic checks and return the report.

    Parameters
    ----------
    store : PackageStore
        The loaded package store (provides ``.managers``, ``.packages``,
        and ``._db.path``).
    sys_check : SysCheck
        System check interface (provides ``.which(executable)``).

    Returns
    -------
    DoctorReport
        Report with ok/warning/error entries.
    """
    report = DoctorReport()

    _check_db(report, store)
    _check_os_manager(report, sys_check)
    _check_managers_path(report, store, sys_check)
    _check_duplicate_names(report, store)
    _check_duplicate_identifiers(report, store)
    _check_type_vs_manager(report, store)

    return report


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_db(report: DoctorReport, store: Any) -> None:
    """Check that the database file exists, is valid JSON, and has the
    expected schema version."""
    db_path = store._db.path

    if not db_path.exists():
        report.error(f"Database file not found: {db_path}")
        return

    if db_path.stat().st_size == 0:
        report.error("Database file is empty")
        return

    try:
        with open(db_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, ValueError):
        report.error("Database file is not valid JSON")
        return

    version = data.get("version")
    if version != DB_VERSION:
        report.error(
            f"Database schema version is {version}, "
            f"expected {DB_VERSION}"
        )
    else:
        report.ok(f"Database: valid JSON, schema v{DB_VERSION}")


def _check_os_manager(report: DoctorReport, sys_check: Any) -> None:
    """Detect the OS package manager (apt/yum/brew)."""
    # Lazy import to avoid circular dependencies at module level
    from src.managers import detect_os_manager

    mgr = detect_os_manager(sys_check=sys_check)
    if mgr is not None:
        report.ok(f"OS package manager: {mgr.name}")
    else:
        report.error("No OS package manager detected (apt/yum/brew)")


def _check_managers_path(
    report: DoctorReport, store: Any, sys_check: Any
) -> None:
    """For each registered manager, verify its executable is on PATH."""
    for mgr_name, mgr_config in store.managers.items():
        exe = _resolve_executable(mgr_name, mgr_config)
        if exe is not None and sys_check.which(exe) is None:
            report.error(
                f"Manager '@{mgr_name}': executable "
                f"'{exe}' not found on PATH"
            )


def _check_duplicate_names(report: DoctorReport, store: Any) -> None:
    """Check for duplicate package names in the database."""
    names = [pkg["name"] for pkg in store.packages]
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in names:
        if name in seen:
            duplicates.add(name)
        seen.add(name)

    if duplicates:
        for name in sorted(duplicates):
            report.warn(f"Duplicate package name: '{name}'")
    else:
        report.ok("No duplicate package names")


def _check_duplicate_identifiers(report: DoctorReport, store: Any) -> None:
    """Check for duplicate name/source values within the same manager.

    For each manager (type), warns if any value appears as ``name`` or
    ``source`` in more than one package.  This catches:

    - Same name in two packages of the same manager
    - Same source in two packages of the same manager
    - A package's name matching another package's source (and vice-versa)
    """
    # Group packages by type
    by_type: dict[str, list[dict]] = {}
    for pkg in store.packages:
        ptype = pkg.get("type", "package")
        by_type.setdefault(ptype, []).append(pkg)

    for ptype in sorted(by_type):
        packages = by_type[ptype]
        # value -> list of (pkg_name, field)
        value_map: dict[str, list[tuple[str, str]]] = {}
        for pkg in packages:
            name = pkg["name"]  # name is required
            src = pkg.get("source")
            value_map.setdefault(name, []).append((name, "name"))
            if src is not None and src != name:
                value_map.setdefault(src, []).append((name, "source"))

        for value in sorted(value_map):
            entries = value_map[value]
            # Only warn if value appears in more than one distinct package
            if len({e[0] for e in entries}) > 1:
                desc = "; ".join(f"{f} of '{n}'" for n, f in entries)
                report.warn(f"@{ptype}: '{value}' — {desc}")


def _check_type_vs_manager(report: DoctorReport, store: Any) -> None:
    """Check that every package with a non-``"package"`` type has a
    matching registered manager."""
    registered = set(store.managers.keys())
    mismatches: list[tuple[str, str]] = []

    for pkg in store.packages:
        ptype = pkg.get("type", "package")
        if ptype == "package":
            continue
        if ptype not in registered:
            mismatches.append((pkg["name"], ptype))

    if mismatches:
        for name, ptype in mismatches:
            report.error(
                f"Package '{name}' has type '{ptype}' but no "
                f"manager '@{ptype}' is registered"
            )
    else:
        report.ok("All package types match registered managers")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_executable(
    mgr_name: str, mgr_config: dict[str, Any]
) -> str | None:
    """Determine the executable to check for a given manager.

    For well-known managers (those listed in ``KNOWN_MANAGERS``), the
    executable is looked up from the ``"exe"`` key. For custom managers
    the first token of the first available command (install -> remove ->
    update) is used.
    """
    # Well-known manager - use the 'exe' key from KNOWN_MANAGERS
    if mgr_name in KNOWN_MANAGERS:
        return KNOWN_MANAGERS[mgr_name].get("exe")  # type: ignore[return-value]

    # Custom manager - extract from the first available command
    cmd: str | list[str] | None = (
        mgr_config.get("install")
        or mgr_config.get("remove")
        or mgr_config.get("update")
    )
    if isinstance(cmd, list) and cmd:
        return cmd[0]

    # String commands (e.g. shell pipes) or empty lists - can't
    # reliably determine the executable, so skip the check.
    return None
