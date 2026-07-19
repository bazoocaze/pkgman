import json
import subprocess
from unittest.mock import patch

import pytest
from managers import Manager, CustomManager, ManagerRegistry


# ---- Manager tests (kept from v1) ----

def test_apt_install_command():
    m = Manager("apt")
    assert m._build_cmd("install", "git") == ["apt", "install", "-y", "git"]


def test_apt_remove_command():
    m = Manager("apt")
    assert m._build_cmd("remove", "git") == ["apt", "remove", "-y", "git"]


def test_yum_install_command():
    m = Manager("yum")
    assert m._build_cmd("install", "git") == ["yum", "install", "-y", "git"]


def test_brew_install_command():
    m = Manager("brew")
    assert m._build_cmd("install", "git") == ["brew", "install", "git"]


def test_brew_uninstall_command():
    m = Manager("brew")
    assert m._build_cmd("remove", "git") == ["brew", "uninstall", "git"]


def test_sudo_prefix():
    cmd = ["sudo"] + ["apt", "install", "-y", "git"]
    assert cmd == ["sudo", "apt", "install", "-y", "git"]


def test_unknown_manager_raises():
    m = Manager("nope")
    with pytest.raises(RuntimeError, match="Unknown manager"):
        m._build_cmd("install", "x")


# ---- CustomManager tests ----

def test_custom_manager_dataclass():
    cm = CustomManager(
        name="uv",
        install_cmd=["uv", "tool", "install", "{source}"],
        remove_cmd=["uv", "tool", "uninstall", "{name}"],
    )
    assert cm.name == "uv"
    assert cm.install_cmd == ["uv", "tool", "install", "{source}"]
    assert cm.remove_cmd == ["uv", "tool", "uninstall", "{name}"]


def test_custom_manager_none_remove():
    cm = CustomManager(
        name="script",
        install_cmd="curl -fsSL {source} | bash",
        remove_cmd=None,
    )
    assert cm.install_cmd == "curl -fsSL {source} | bash"
    assert cm.remove_cmd is None


# ---- ManagerRegistry tests ----

def _make_db(managers=None, packages=None):
    """Helper to create a minimal db-like object."""
    class FakeDB:
        def __init__(self):
            self.managers = managers or {}
            self.packages = packages or []
        def load(self):
            return self.packages
        def find(self, name):
            for p in self.packages:
                if p["name"] == name:
                    return p
            return None
    return FakeDB()


def test_registry_get_package_returns_none():
    db = _make_db()
    reg = ManagerRegistry(db)
    assert reg.get("package") is None


def test_registry_get_custom_manager():
    db = _make_db({"uv": {"install": ["uv", "tool", "install", "{source}"], "remove": ["uv", "tool", "uninstall", "{name}"]}})
    reg = ManagerRegistry(db)
    cm = reg.get("uv")
    assert cm is not None
    assert cm.name == "uv"
    assert cm.install_cmd == ["uv", "tool", "install", "{source}"]


def test_registry_get_unknown_returns_none():
    db = _make_db()
    reg = ManagerRegistry(db)
    assert reg.get("nonexistent") is None


# ---- _substitute tests ----

def test_substitute_list():
    cmd = ["pi", "install", "{source}"]
    result = ManagerRegistry._substitute(cmd, "pi-subagents", "npm:@tintinweb/pi-subagents")
    assert result == ["pi", "install", "npm:@tintinweb/pi-subagents"]


def test_substitute_string():
    cmd = "curl -fsSL {source} | bash"
    result = ManagerRegistry._substitute(cmd, "sdkman", "https://get.sdkman.io")
    assert result == "curl -fsSL https://get.sdkman.io | bash"


def test_substitute_name_placeholder():
    cmd = ["uv", "tool", "uninstall", "{name}"]
    result = ManagerRegistry._substitute(cmd, "ruff", "github:astral-sh/ruff")
    assert result == ["uv", "tool", "uninstall", "ruff"]


def test_substitute_none():
    assert ManagerRegistry._substitute(None, "x", "y") is None


# ---- resolve_auto tests ----

def test_resolve_auto_by_name(db_path):
    from database import Database
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": [{"type": "package", "name": "git"}]}
    with open(db_path, "w") as f:
        json.dump(data, f)
    db = Database(db_path)
    db.load()
    reg = ManagerRegistry(db)
    result = reg.resolve_auto("git")
    assert result is not None
    mgr, pkg = result
    assert mgr == "package"
    assert pkg["name"] == "git"


def test_resolve_auto_by_source(db_path):
    from database import Database
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": [{"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"}]}
    with open(db_path, "w") as f:
        json.dump(data, f)
    db = Database(db_path)
    db.load()
    reg = ManagerRegistry(db)
    result = reg.resolve_auto("github:astral-sh/ruff")
    assert result is not None
    mgr, pkg = result
    assert mgr == "uv"
    assert pkg["name"] == "ruff"


def test_resolve_auto_not_found(db_path):
    from database import Database
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    db = Database(db_path)
    db.load()
    reg = ManagerRegistry(db)
    assert reg.resolve_auto("nonexistent") is None


def test_resolve_auto_ambiguous_raises(db_path):
    from database import Database
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": [
        {"type": "pi", "name": "a", "source": "same-source"},
        {"type": "script", "name": "b", "source": "same-source"},
    ]}
    with open(db_path, "w") as f:
        json.dump(data, f)
    db = Database(db_path)
    db.load()
    reg = ManagerRegistry(db)
    with pytest.raises(ValueError, match="Ambiguous"):
        reg.resolve_auto("same-source")


# ---- registry.install with custom manager ---

@patch("managers.ManagerRegistry._run_command")
def test_registry_install_custom(mock_run_cmd, db_path):
    from database import Database
    data = {"version": 2, "sudo": "no", "managers": {
        "uv": {"install": ["uv", "tool", "install", "{source}"], "remove": ["uv", "tool", "uninstall", "{name}"]}
    }, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    db = Database(db_path)
    db.load()
    reg = ManagerRegistry(db)
    reg.install("uv", "ruff", "github:astral-sh/ruff", sudo=False)
    mock_run_cmd.assert_called_once_with(["uv", "tool", "install", "github:astral-sh/ruff"])


# ---- registry.remove with custom manager ---

@patch("managers.ManagerRegistry._run_command")
def test_registry_remove_custom(mock_run_cmd, db_path):
    from database import Database
    data = {"version": 2, "sudo": "no", "managers": {
        "uv": {"install": ["uv", "tool", "install", "{source}"], "remove": ["uv", "tool", "uninstall", "{name}"]}
    }, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    db = Database(db_path)
    db.load()
    reg = ManagerRegistry(db)
    reg.remove("uv", "ruff", "github:astral-sh/ruff", sudo=False)
    mock_run_cmd.assert_called_once_with(["uv", "tool", "uninstall", "ruff"])


# ---- registry.remove with null remove_cmd (DB-only) ---

def test_registry_remove_null_cmd_is_db_only(db_path):
    from database import Database
    data = {"version": 2, "sudo": "no", "managers": {
        "script": {"install": "curl {source}", "remove": None}
    }, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    db = Database(db_path)
    db.load()
    reg = ManagerRegistry(db)
    # Should not raise - null remove_cmd means DB-only
    reg.remove("script", "sdkman", "https://get.sdkman.io", sudo=False)
