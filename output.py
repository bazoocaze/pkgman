"""
output.py – console formatting helpers.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import NamedTuple


def _snippet(stderr: str = "", stdout: str = "", maxlen: int = 60) -> str:
    """Extract a one-line snippet from stderr or stdout."""
    text = stderr or stdout
    if not text:
        return ""
    line = text.strip().split("\n")[0]
    if len(line) > maxlen:
        line = line[:maxlen] + "..."
    return line


def format_package_list(packages: list[dict], *, json_output: bool = False) -> str:
    """Format the package list for display."""
    if not packages:
        return "[]" if json_output else "No registered packages."

    if json_output:
        return json.dumps(packages, indent=2)

    lines: list[str] = []
    for pkg in packages:
        ptype = pkg["type"]
        name = pkg["name"]
        source = pkg.get("source", "")
        if ptype == "package":
            lines.append(f"PACKAGE  {name}")
        elif source:
            lines.append(f"{ptype.upper():8} {name}  {source}")
        else:
            lines.append(f"{ptype.upper():8} {name}")
    return "\n".join(lines)


class _Colors:
    """ANSI escape sequences (noop if not a tty)."""

    @staticmethod
    def _enabled() -> bool:
        return sys.stdout.isatty()

    @staticmethod
    def OK() -> str:
        if _Colors._enabled():
            return "\033[92m\033[1m"
        return ""

    @staticmethod
    def FAIL() -> str:
        if _Colors._enabled():
            return "\033[91m\033[1m"
        return ""

    @staticmethod
    def SNIPPET() -> str:
        if _Colors._enabled():
            return "\033[93m"
        return ""

    @staticmethod
    def RESET() -> str:
        if _Colors._enabled():
            return "\033[0m"
        return ""


class ReportEntry(NamedTuple):
    success: bool
    ptype: str
    name: str
    detail: str = ""
    snippet: str = ""


@dataclass
class Report:
    """Accumulates results and prints a formatted summary."""

    entries: list[ReportEntry] = field(default_factory=list)

    def add_ok(self, ptype: str, name: str, detail: str = "") -> None:
        self.entries.append(ReportEntry(True, ptype, name, detail))

    def add_fail(self, ptype: str, name: str, detail: str = "", snippet: str = "") -> None:
        self.entries.append(ReportEntry(False, ptype, name, detail, snippet))

    def print(self) -> None:
        C = _Colors
        ok_count = sum(1 for e in self.entries if e.success)
        fail_count = len(self.entries) - ok_count

        out_lines: list[str] = []
        for entry in self.entries:
            icon = f"{C.OK()}✅{C.RESET()}" if entry.success else f"{C.FAIL()}❌{C.RESET()}"
            text = f"  {icon}  {entry.ptype:<8} {entry.name}"
            if entry.detail:
                text += f"  {entry.detail}"
            if entry.snippet:
                text += f"  {C.SNIPPET()}{entry.snippet}{C.RESET()}"
            out_lines.append(text)

        summary_color = C.OK if fail_count == 0 else C.FAIL
        summary = f"{summary_color()}Summary: {ok_count} succeeded, {fail_count} failed{C.RESET()}"
        out_lines.append(summary)

        print("\n".join(out_lines))