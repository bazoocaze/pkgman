"""
commands.py - Orchestrates install, remove, list commands
"""

import json
import subprocess
import sys
from database import Database
from managers import ManagerRegistry


class _Colors:
    if sys.stdout.isatty():
        _ok = "\033[92m"
        _fail = "\033[91m"
        _snippet = "\033[93m"
        _bold = "\033[1m"
        _reset = "\033[0m"
    else:
        _ok = _fail = _snippet = _bold = _reset = ""

    OK = f"{_ok}{_bold}"
    FAIL = f"{_fail}{_bold}"
    SNIPPET = f"{_snippet}"
    RESET = _reset


class _Report:
    """Accumulates results and prints a formatted report."""

    def __init__(self):
        self.entries = []

    def add_ok(self, ptype, name, detail=""):
        self.entries.append((True, ptype, name, detail))

    def add_fail(self, ptype, name, detail="", snippet=""):
        self.entries.append((False, ptype, name, detail, snippet))

    @staticmethod
    def _snippet(stderr="", stdout="", maxlen=60):
        text = stderr or stdout
        if not text:
            return ""
        line = text.strip().split("\n")[0]
        if len(line) > maxlen:
            line = line[:maxlen] + "..."
        return line

    def print(self):
        C = _Colors
        ok_count = sum(1 for ok, *_ in self.entries if ok)
        fail_count = len(self.entries) - ok_count

        out_lines = []
        for entry in self.entries:
            ok = entry[0]
            ptype, name = entry[1], entry[2]
            detail = entry[3] if len(entry) > 3 else ""
            snippet = entry[4] if len(entry) > 4 else ""
            icon = f"{C.OK}✅{C.RESET}" if ok else f"{C.FAIL}❌{C.RESET}"
            text = f"  {icon}  {ptype:<8} {name}"
            if detail:
                text += f"  {detail}"
            if snippet:
                text += f"  {C.SNIPPET}{snippet}{C.RESET}"
            out_lines.append(text)

        summary_color = C.OK if fail_count == 0 else C.FAIL
        summary = f"{summary_color}Summary: {ok_count} succeeded, {fail_count} failed{C.RESET}"
        out_lines.append(summary)

        print("\n".join(out_lines))


class Commands:
    """Orchestrates the execution of CLI commands."""

    def __init__(self, db_path=None):
        self.db = Database(db_path)
        self.db.load()  # loads the sudo flag (if file exists)
        self.registry = ManagerRegistry(self.db)

    @property
    def _use_sudo(self):
        return self.db.sudo == "yes"

    def install(self, manager, name_or_names, source=None):
        """Install packages by manager type.

        For "package", name_or_names is a list and each is installed via the OS manager.
        For other managers, name_or_names is a single name.
        If source is not provided, source defaults to name.
        """
        if manager == "package":
            for name in name_or_names:
                print(f"Installing package: {name}")
                self.registry.install("package", name, name, self._use_sudo)
                self.db.add({"type": "package", "name": name})
                print(f"  -> {name} installed and registered.")
        else:
            name = name_or_names
            if source is None:
                source = name
            print(f"Installing {manager} package: {name}")
            if source != name:
                print(f"  Source: {source}")
            self.registry.install(manager, name, source, sudo=False)
            pkg_entry = {"type": manager, "name": name}
            if source != name:
                pkg_entry["source"] = source
            self.db.add(pkg_entry)
            print(f"  -> {name} installed and registered.")

    def install_all(self):
        """Reinstall all packages from the database (replay)."""
        packages = self.db.load()
        if not packages:
            print("No registered packages to install.")
            return

        report = _Report()

        for pkg in packages:
            ptype = pkg["type"]
            name = pkg["name"]
            source = pkg.get("source", name)
            try:
                sudo = self._use_sudo if ptype == "package" else False
                self.registry.install(ptype, name, source, sudo=sudo)
                report.add_ok(ptype.upper(), name, source)
            except subprocess.CalledProcessError as e:
                report.add_fail(ptype.upper(), name, f"exit {e.returncode}",
                                snippet=_Report._snippet(e.stderr, e.stdout))
            except Exception as e:
                report.add_fail(ptype.upper(), name, str(e))

        report.print()

    def remove(self, manager, name):
        """Remove a package by name.

        If manager is "auto" (or None), resolves the manager automatically
        by searching the database by name, then by source.
        """
        if manager == "auto" or manager is None:
            result = self.registry.resolve_auto(name)
            if result is None:
                print(f"Warning: '{name}' not found in database. Skipping.")
                return
            manager, pkg = result
        else:
            pkg = self.db.find(name)
            if pkg is None:
                print(f"Warning: '{name}' not found in database. Skipping.")
                return

        print(f"Removing {manager} package: {name}")
        source = pkg.get("source", name)
        sudo = self._use_sudo if manager == "package" else False
        self.registry.remove(manager, name, source, sudo=sudo)
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
                ptype = pkg["type"]
                name = pkg["name"]
                source = pkg.get("source", "")
                if ptype == "package":
                    print(f"PACKAGE  {name}")
                elif source:
                    print(f"{ptype.upper():8} {name}  {source}")
                else:
                    print(f"{ptype.upper():8} {name}")