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

# Current database schema version
DB_VERSION = 2
