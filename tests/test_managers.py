"""Tests for managers.py – Manager, CustomManager, ManagerRegistry."""

import json
import subprocess
from unittest.mock import patch

import pytest
from managers import Manager, CustomManager, ManagerRegistry
from database import Database, PackageStore


# =========================================================================
# Helpers
# =========================================================================

def _make_store(managers=None, packages=None):
    """Create a PackageStore backed by a temp file with given data."""
    import tempfile, os, atexit
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    atexit.register(lambda: os.unlink(path) if os.path.exists(path) else None)

    data = {
        "version": 2,
        "sudo": "no",
        "managers": managers or {},
        "packages": packages or [],
    }
    with open(path, "w") as f:
        json.dump(data, f)

    db = Database(path)
    store = PackageStore(db)
    store.load()
    return store


# =========================================================================
# Manager tests
# =========================================================================

class TestManager:
    def test_apt_install_command(self):
        m = Manager("apt")
        assert m._build_cmd("install", "git") == ["apt", "install", "-y", "git"]

    def test_apt_remove_command(self):
        m = Manager("apt")
        assert m._build_cmd("remove", "git") == ["apt", "remove", "-y", "git"]

    def test_yum_install_command(self):
        m = Manager("yum")
        assert m._build_cmd("install", "git") == ["yum", "install", "-y", "git"]

    def test_brew_install_command(self):
        m = Manager("brew")
        assert m._build_cmd("install", "git") == ["brew", "install", "git"]

    def test_brew_uninstall_command(self):
        m = Manager("brew")
        assert m._build_cmd("remove", "git") == ["brew", "uninstall", "git"]

    def test_sudo_prefix(self):
        cmd = ["sudo"] + ["apt", "install", "-y", "git"]
        assert cmd == ["sudo", "apt", "install", "-y", "git"]

    def test_unknown_manager_raises(self):
        m = Manager("nope")
        with pytest.raises(RuntimeError, match="Unknown manager"):
            m._build_cmd("install", "x")


# =========================================================================
# CustomManager tests
# =========================================================================

class TestCustomManager:
    def test_dataclass(self):
        cm = CustomManager(
            name="uv",
            install_cmd=["uv", "tool", "install", "{source}"],
            remove_cmd=["uv", "tool", "uninstall", "{name}"],
        )
        assert cm.name == "uv"
        assert cm.install_cmd == ["uv", "tool", "install", "{source}"]
        assert cm.remove_cmd == ["uv", "tool", "uninstall", "{name}"]

    def test_none_remove(self):
        cm = CustomManager(
            name="script",
            install_cmd="curl -fsSL {source} | bash",
            remove_cmd=None,
        )
        assert cm.install_cmd == "curl -fsSL {source} | bash"
        assert cm.remove_cmd is None


# =========================================================================
# ManagerRegistry tests
# =========================================================================

class TestManagerRegistry:
    def test_get_package_returns_none(self):
        reg = ManagerRegistry(_make_store())
        assert reg.get("package") is None

    def test_get_custom_manager(self):
        store = _make_store({"uv": {"install": ["uv", "tool", "install", "{source}"],
                                     "remove": ["uv", "tool", "uninstall", "{name}"]}})
        reg = ManagerRegistry(store)
        cm = reg.get("uv")
        assert cm is not None
        assert cm.name == "uv"
        assert cm.install_cmd == ["uv", "tool", "install", "{source}"]

    def test_get_unknown_returns_none(self):
        reg = ManagerRegistry(_make_store())
        assert reg.get("nonexistent") is None


# =========================================================================
# _substitute tests
# =========================================================================

class TestSubstitute:
    def test_list(self):
        result = ManagerRegistry._substitute(
            ["pi", "install", "{source}"], "pi-subagents", "npm:@tintinweb/pi-subagents"
        )
        assert result == ["pi", "install", "npm:@tintinweb/pi-subagents"]

    def test_string(self):
        result = ManagerRegistry._substitute(
            "curl -fsSL {source} | bash", "sdkman", "https://get.sdkman.io"
        )
        assert result == "curl -fsSL https://get.sdkman.io | bash"

    def test_name_placeholder(self):
        result = ManagerRegistry._substitute(
            ["uv", "tool", "uninstall", "{name}"], "ruff", "github:astral-sh/ruff"
        )
        assert result == ["uv", "tool", "uninstall", "ruff"]

    def test_none(self):
        assert ManagerRegistry._substitute(None, "x", "y") is None


# =========================================================================
# resolve_auto tests
# =========================================================================

class TestResolveAuto:
    def test_by_name(self):
        store = _make_store(packages=[{"type": "package", "name": "git"}])
        reg = ManagerRegistry(store)
        result = reg.resolve_auto("git")
        assert result == ("package", {"type": "package", "name": "git"})

    def test_by_source(self):
        store = _make_store(packages=[{"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"}])
        reg = ManagerRegistry(store)
        result = reg.resolve_auto("github:astral-sh/ruff")
        assert result is not None
        mgr, pkg = result
        assert mgr == "uv"
        assert pkg["name"] == "ruff"

    def test_not_found(self):
        reg = ManagerRegistry(_make_store())
        assert reg.resolve_auto("nonexistent") is None

    def test_ambiguous_raises(self):
        store = _make_store(packages=[
            {"type": "pi", "name": "a", "source": "same-source"},
            {"type": "script", "name": "b", "source": "same-source"},
        ])
        reg = ManagerRegistry(store)
        with pytest.raises(ValueError, match="Ambiguous"):
            reg.resolve_auto("same-source")


# =========================================================================
# registry.install / registry.remove with custom manager
# =========================================================================

class TestCustomManagerExecution:
    @patch("managers.ManagerRegistry._run_command")
    def test_registry_install_custom(self, mock_run_cmd):
        store = _make_store(managers={
            "uv": {"install": ["uv", "tool", "install", "{source}"],
                   "remove": ["uv", "tool", "uninstall", "{name}"]},
        })
        reg = ManagerRegistry(store)
        reg.install("uv", "ruff", "github:astral-sh/ruff")
        mock_run_cmd.assert_called_once_with(["uv", "tool", "install", "github:astral-sh/ruff"])

    @patch("managers.ManagerRegistry._run_command")
    def test_registry_remove_custom(self, mock_run_cmd):
        store = _make_store(managers={
            "uv": {"install": ["uv", "tool", "install", "{source}"],
                   "remove": ["uv", "tool", "uninstall", "{name}"]},
        })
        reg = ManagerRegistry(store)
        reg.remove("uv", "ruff", "github:astral-sh/ruff")
        mock_run_cmd.assert_called_once_with(["uv", "tool", "uninstall", "ruff"])

    def test_registry_remove_null_cmd_is_db_only(self):
        store = _make_store(managers={
            "script": {"install": "curl {source}", "remove": None},
        })
        reg = ManagerRegistry(store)
        # Should not raise – null remove_cmd means DB-only removal
        reg.remove("script", "sdkman", "https://get.sdkman.io")