"""
constants.py – shared constants and enumerations.
"""

from enum import StrEnum


class ManagerType(StrEnum):
    PACKAGE = "package"
    AUTO = "auto"


class SudoSetting(StrEnum):
    YES = "yes"
    NO = "no"


# Manager names that cannot be used as custom managers
RESERVED_MANAGERS = frozenset({ManagerType.PACKAGE, ManagerType.AUTO})

# Known managers that "configure" can detect and offer to add.
# Maps manager name → {exe, install, remove, update}.
KNOWN_MANAGERS: dict[str, dict[str, str | list[str] | None]] = {
    "bash": {
        "exe": "bash",
        "install": "curl -fsSL {source} | bash",
        "remove": None,
        # Script managers have no upgrade mechanism: update re-runs the
        # installer, which is the only way to refresh them.
        "update": "curl -fsSL {source} | bash",
    },
    "zsh": {
        "exe": "zsh",
        "install": "curl -fsSL {source} | zsh",
        "remove": None,
        "update": "curl -fsSL {source} | zsh",
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
        # User scope: works without root, keeping custom managers
        # independent from the database "sudo" setting.
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

# Current database schema version
DB_VERSION = 2
