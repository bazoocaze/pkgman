"""Tests for KNOWN_MANAGERS – validates values to catch accidental changes."""

from src.constants import KNOWN_MANAGERS


def test_known_managers_values():
    assert KNOWN_MANAGERS == {
        "bash": {
            "exe": "bash",
            "install": "curl -fsSL {source} | bash",
            "remove": None,
            "update": None,
        },
        "zsh": {
            "exe": "zsh",
            "install": "curl -fsSL {source} | zsh",
            "remove": None,
            "update": None,
        },
        "pi": {
            "exe": "pi",
            "install": ["pi", "install", "{source}"],
            "remove": ["pi", "remove", "{source}"],
            "update": ["pi", "update", "{source}"],
        },
        "uv": {
            "exe": "uv",
            "install": ["uv", "tool", "install", "{source}"],
            "remove": ["uv", "tool", "uninstall", "{name}"],
            "update": ["uv", "tool", "upgrade", "{name}"],
        },
    }