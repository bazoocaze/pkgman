"""Tests for managers.py – Manager, CustomManager, ManagerRegistry."""

import json
import subprocess
from unittest.mock import patch, MagicMock

import pytest
from src.managers import Manager, CustomManager, ManagerRegistry, _substitute
from src.runner import ProcessRunner
from src.database import Database, PackageStore


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

    def test_apt_update_command(self):
        m = Manager("apt")
        assert m._build_update_cmd("git") == ["apt", "install", "--only-upgrade", "-y", "git"]

    def test_yum_install_command(self):
        m = Manager("yum")
        assert m._build_cmd("install", "git") == ["yum", "install", "-y", "git"]

    def test_yum_update_command(self):
        m = Manager("yum")
        assert m._build_update_cmd("git") == ["yum", "update", "-y", "git"]

    def test_brew_install_command(self):
        m = Manager("brew")
        assert m._build_cmd("install", "git") == ["brew", "install", "git"]

    def test_brew_uninstall_command(self):
        m = Manager("brew")
        assert m._build_cmd("remove", "git") == ["brew", "uninstall", "git"]

    def test_brew_update_command(self):
        m = Manager("brew")
        assert m._build_update_cmd("git") == ["brew", "upgrade", "git"]

    def test_sudo_prefix(self):
        cmd = ["sudo"] + ["apt", "install", "-y", "git"]
        assert cmd == ["sudo", "apt", "install", "-y", "git"]

    def test_unknown_manager_raises(self):
        m = Manager("nope")
        with pytest.raises(ValueError, match="Unknown manager"):
            m._build_cmd("install", "x")

    def test_unknown_manager_update_raises(self):
        m = Manager("nope")
        with pytest.raises(ValueError, match="Unknown manager"):
            m._build_update_cmd("x")


# =========================================================================
# CustomManager tests
# =========================================================================

class TestCustomManager:
    def test_dataclass(self):
        cm = CustomManager(
            name="foobar",
            install_cmd=["foobar", "install", "{source}"],
            remove_cmd=["foobar", "remove", "{source}"],
            update_cmd=["foobar", "update", "{name}"],
        )
        assert cm.name == "foobar"
        assert cm.install_cmd == ["foobar", "install", "{source}"]
        assert cm.remove_cmd == ["foobar", "remove", "{source}"]
        assert cm.update_cmd == ["foobar", "update", "{name}"]

    def test_none_remove(self):
        cm = CustomManager(
            name="foobar",
            install_cmd="curl -fsSL {source} | bash",
            remove_cmd=None,
        )
        assert cm.install_cmd == "curl -fsSL {source} | bash"
        assert cm.remove_cmd is None
        assert cm.update_cmd is None

    def test_from_dict_with_update(self):
        cm = CustomManager.from_dict("foobar", {
            "install": ["foobar", "install", "{source}"],
            "remove": ["foobar", "remove", "{source}"],
            "update": ["foobar", "update", "{name}"],
        })
        assert cm.update_cmd == ["foobar", "update", "{name}"]

    def test_from_dict_without_update(self):
        cm = CustomManager.from_dict("foobar", {
            "install": ["foobar", "install", "{source}"],
            "remove": ["foobar", "remove", "{source}"],
        })
        assert cm.update_cmd is None


# =========================================================================
# ManagerRegistry tests
# =========================================================================

class TestManagerRegistry:
    def test_get_package_returns_none(self):
        reg = ManagerRegistry(_make_store())
        assert reg.get("package") is None

    def test_get_custom_manager(self):
        store = _make_store({"foobar": {"install": ["foobar", "install", "{source}"],
                                      "remove": ["foobar", "remove", "{source}"]}})
        reg = ManagerRegistry(store)
        cm = reg.get("foobar")
        assert cm is not None
        assert cm.name == "foobar"
        assert cm.install_cmd == ["foobar", "install", "{source}"]

    def test_get_unknown_returns_none(self):
        reg = ManagerRegistry(_make_store())
        assert reg.get("nonexistent") is None

    def test_resolve_package_returns_manager(self):
        reg = ManagerRegistry(_make_store())
        with patch("src.managers.detect_os_manager") as mock_detect:
            mock_detect.return_value = Manager("apt")
            mgr = reg.resolve("package")
            assert isinstance(mgr, Manager)
            assert mgr.name == "apt"

    def test_resolve_raises_for_unknown_manager(self):
        from src.exceptions import PkgmanError
        reg = ManagerRegistry(_make_store())
        with pytest.raises(PkgmanError, match="not configured"):
            reg.resolve("nonexistent")

    def test_resolve_returns_custom_manager(self):
        store = _make_store(
            {"my": {"install": ["my", "install", "{source}"]}}
        )
        reg = ManagerRegistry(store)
        mgr = reg.resolve("my")
        assert isinstance(mgr, CustomManager)
        assert mgr.name == "my"


# =========================================================================
# _substitute tests
# =========================================================================

class TestSubstitute:
    def test_list(self):
        result = _substitute(
            ["foobar", "install", "{source}"], "pi-subagents", "npm:@tintinweb/pi-subagents"
        )
        assert result == ["foobar", "install", "npm:@tintinweb/pi-subagents"]

    def test_string(self):
        result = _substitute(
            "curl -fsSL {source} | bash", "sdkman", "https://get.sdkman.io"
        )
        assert result == "curl -fsSL https://get.sdkman.io | bash"

    def test_name_placeholder(self):
        result = _substitute(
            ["foobar", "tool", "uninstall", "{name}"], "ruff", "github:astral-sh/ruff"
        )
        assert result == ["foobar", "tool", "uninstall", "ruff"]

    def test_none(self):
        assert _substitute(None, "x", "y") is None


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
        store = _make_store(packages=[{"type": "foobar", "name": "ruff", "source": "github:astral-sh/ruff"}])
        reg = ManagerRegistry(store)
        result = reg.resolve_auto("github:astral-sh/ruff")
        assert result is not None
        mgr, pkg = result
        assert mgr == "foobar"
        assert pkg["name"] == "ruff"

    def test_not_found(self):
        reg = ManagerRegistry(_make_store())
        assert reg.resolve_auto("nonexistent") is None

    def test_ambiguous_raises(self):
        store = _make_store(packages=[
            {"type": "foobar", "name": "a", "source": "same-source"},
            {"type": "foobar", "name": "b", "source": "same-source"},
        ])
        reg = ManagerRegistry(store)
        with pytest.raises(ValueError, match="Ambiguous"):
            reg.resolve_auto("same-source")


# =========================================================================
# registry.install / registry.remove with custom manager
# =========================================================================

class TestCustomManagerExecution:
    def _make_mock_runner(self):
        """Return a ProcessRunner mock and a registry wired to it."""
        mock_runner = MagicMock(spec=ProcessRunner)
        return mock_runner

    def test_registry_install_custom(self):
        mock_runner = self._make_mock_runner()
        store = _make_store(managers={
            "foobar": {"install": ["foobar", "install", "{source}"],
                       "remove": ["foobar", "remove", "{source}"]},
        })
        reg = ManagerRegistry(store, runner=mock_runner)
        reg.install("foobar", "ruff", "github:astral-sh/ruff")
        mock_runner.run.assert_called_once_with(["foobar", "install", "github:astral-sh/ruff"], shell=False)

    def test_registry_remove_custom(self):
        mock_runner = self._make_mock_runner()
        store = _make_store(managers={
            "foobar": {"install": ["foobar", "install", "{source}"],
                       "remove": ["foobar", "remove", "{source}"]},
        })
        reg = ManagerRegistry(store, runner=mock_runner)
        reg.remove("foobar", "ruff", "github:astral-sh/ruff")
        mock_runner.run.assert_called_once_with(["foobar", "remove", "github:astral-sh/ruff"], shell=False)

    def test_registry_remove_null_cmd_is_db_only(self):
        mock_runner = self._make_mock_runner()
        store = _make_store(managers={
            "foobar": {"install": "curl {source}", "remove": None},
        })
        reg = ManagerRegistry(store, runner=mock_runner)
        # Should not raise – null remove_cmd means DB-only removal
        reg.remove("foobar", "sdkman", "https://get.sdkman.io")
        mock_runner.run.assert_not_called()

    def test_registry_update_custom(self):
        mock_runner = self._make_mock_runner()
        store = _make_store(managers={
            "foobar": {"install": ["foobar", "install", "{source}"],
                       "remove": ["foobar", "remove", "{source}"],
                       "update": ["foobar", "update", "{name}"]},
        })
        reg = ManagerRegistry(store, runner=mock_runner)
        reg.update("foobar", "ruff", "github:astral-sh/ruff")
        mock_runner.run.assert_called_once_with(["foobar", "update", "ruff"], shell=False)

    def test_registry_update_null_cmd_is_noop(self):
        mock_runner = self._make_mock_runner()
        store = _make_store(managers={
            "foobar": {"install": "curl {source}", "remove": None, "update": None},
        })
        reg = ManagerRegistry(store, runner=mock_runner)
        reg.update("foobar", "sdkman", "https://get.sdkman.io")
        mock_runner.run.assert_not_called()