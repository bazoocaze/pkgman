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
            "name_regex": r"npm:(?:@[^/]+/)?(.+)",
        },
        "uv": {
            "exe": "uv",
            "install": ["uv", "tool", "install", "{source}"],
            "remove": ["uv", "tool", "uninstall", "{name}"],
            "update": ["uv", "tool", "upgrade", "{name}"],
            "name_regex": r"(?:git\+https?://[^/]+/[^/]+/|github:[^/]+/)?([^@=<>/]+)",
        },
        "flatpak": {
            "exe": "flatpak",
            "install": ["flatpak", "install", "--user", "-y", "flathub", "{source}"],
            "remove": ["flatpak", "uninstall", "--user", "{name}"],
            "update": ["flatpak", "update", "--user", "{name}"],
        },
        "npm": {
            "exe": "npm",
            "install": ["npm", "install", "-g", "{source}"],
            "remove": ["npm", "uninstall", "-g", "{name}"],
            "update": ["npm", "update", "-g", "{name}"],
        },
    }