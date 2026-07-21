"""Tests for KNOWN_MANAGERS – validates values to catch accidental changes."""

from constants import KNOWN_MANAGERS


def test_known_managers_values():
    assert KNOWN_MANAGERS == {
        "bash": (
            "bash",
            "curl -fsSL {source} | bash",
            None,
        ),
        "pi": (
            "pi",
            ["pi", "install", "{source}"],
            ["pi", "remove", "{source}"],
        ),
        "uv": (
            "uv",
            ["uv", "tool", "install", "{source}"],
            ["uv", "tool", "uninstall", "{source}"],
        ),
    }