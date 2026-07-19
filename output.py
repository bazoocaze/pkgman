"""
output.py – console formatting helpers.
"""

import sys
from dataclasses import dataclass, field


class _Colors:
    """ANSI escape sequences (noop if not a tty)."""

    if sys.stdout.isatty():
        _ok = "\033[92m"
        _fail = "\033[91m"
        _snippet = "\033[93m"
        _bold = "\033[1m"
        _reset = "\033[0m"
    else:
        _ok = _fail = _snippet = _bold = _reset = ""

    OK: str = f"{_ok}{_bold}"
    FAIL: str = f"{_fail}{_bold}"
    SNIPPET: str = f"{_snippet}"
    RESET: str = _reset


@dataclass
class ReportEntry:
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

    @staticmethod
    def _snippet(stderr: str = "", stdout: str = "", maxlen: int = 60) -> str:
        text = stderr or stdout
        if not text:
            return ""
        line = text.strip().split("\n")[0]
        if len(line) > maxlen:
            line = line[:maxlen] + "..."
        return line

    def print(self) -> None:
        C = _Colors
        ok_count = sum(1 for e in self.entries if e.success)
        fail_count = len(self.entries) - ok_count

        out_lines: list[str] = []
        for entry in self.entries:
            icon = f"{C.OK}✅{C.RESET}" if entry.success else f"{C.FAIL}❌{C.RESET}"
            text = f"  {icon}  {entry.ptype:<8} {entry.name}"
            if entry.detail:
                text += f"  {entry.detail}"
            if entry.snippet:
                text += f"  {C.SNIPPET}{entry.snippet}{C.RESET}"
            out_lines.append(text)

        summary_color = C.OK if fail_count == 0 else C.FAIL
        summary = f"{summary_color}Summary: {ok_count} succeeded, {fail_count} failed{C.RESET}"
        out_lines.append(summary)

        print("\n".join(out_lines))