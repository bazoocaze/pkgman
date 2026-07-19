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

# Default custom managers bundled with pkgman
DEFAULT_MANAGERS: dict[str, dict[str, list[str] | str | None]] = {
    "uv": {
        "install": ["uv", "tool", "install", "{source}"],
        "remove": ["uv", "tool", "uninstall", "{name}"],
    },
    "script": {
        "install": "curl -fsSL {source} | bash",
        "remove": None,
    },
}

# Current database schema version
DB_VERSION = 2