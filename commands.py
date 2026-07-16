"""
commands.py - Orchestrates install, remove, list commands
"""

import json
import subprocess
import sys
from database import Database
from managers import Manager
from scripts import ScriptRunner
from uv_tools import UvTool


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

        report = _Report()

        for pkg in packages:
            ptype = pkg["type"]
            name = pkg["name"]
            if ptype == "package":
                try:
                    self.manager.install(name, sudo=self._use_sudo)
                    report.add_ok("PACKAGE", name)
                except subprocess.CalledProcessError as e:
                    report.add_fail("PACKAGE", name, f"exit {e.returncode}",
                                    snippet=_Report._snippet(e.stderr, e.stdout))
                except Exception as e:
                    report.add_fail("PACKAGE", name, str(e))
            elif ptype == "script":
                url = pkg.get("url", "?")
                try:
                    ScriptRunner.run(url)
                    report.add_ok("SCRIPT", name, url)
                except subprocess.CalledProcessError as e:
                    report.add_fail("SCRIPT", name, f"exit {e.returncode}",
                                    snippet=_Report._snippet(e.stderr, e.stdout))
                except Exception as e:
                    report.add_fail("SCRIPT", name, str(e))
            elif ptype == "uv":
                source = pkg.get("source", name)
                try:
                    UvTool.install(source)
                    report.add_ok("UV", name, source)
                except subprocess.CalledProcessError as e:
                    report.add_fail("UV", name, f"exit {e.returncode}",
                                    snippet=_Report._snippet(e.stderr, e.stdout))
                except Exception as e:
                    report.add_fail("UV", name, str(e))

        report.print()

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