import json
import os
import subprocess
from unittest.mock import patch

import pytest

from commands import Commands
from constants import KNOWN_MANAGERS



class FakeSysCheck:
    def __init__(self, mapping: dict[str, str | None] | None = None) -> None:
        self._mapping = mapping or {}

    def which(self, executable: str) -> str | None:
        if executable in self._mapping:
            return self._mapping[executable]
        return "/usr/bin/" + executable


def test_commands_init_sudo_no(db_path):
    data = {"version": 1, "sudo": "no", "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    assert cmds.store.sudo == "no"
    assert cmds._sudo is False


def test_use_sudo_property(db_path):
    data = {"version": 1, "sudo": "yes", "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    assert cmds._sudo is True
    cmds.store.sudo = "no"
    assert cmds._sudo is False


def test_list_no_packages(db_path, capsys):
    data = {"version": 1, "sudo": "no", "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    cmds.list()
    captured = capsys.readouterr()
    assert "No registered packages" in captured.out


def test_list_with_package(db_path, capsys):
    data = {
        "version": 1,
        "sudo": "no",
        "packages": [{"type": "package", "name": "testpkg"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    cmds.list()
    captured = capsys.readouterr()
    assert "PACKAGE  testpkg" in captured.out


def test_list_with_uv_package(db_path, capsys):
    data = {
        "version": 1,
        "sudo": "no",
        "packages": [
            {"type": "package", "name": "testpkg"},
            {"type": "foobar", "name": "ruff", "source": "github:astral-sh/ruff"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    cmds.list()
    captured = capsys.readouterr()
    assert "PACKAGE  testpkg" in captured.out
    assert "FOOBAR   ruff" in captured.out


def test_list_with_bash_package(db_path, capsys):
    data = {
        "version": 1,
        "sudo": "no",
        "packages": [
            {"type": "foobar", "name": "sdkman", "source": "https://get.sdkman.io"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    cmds.list()
    captured = capsys.readouterr()
    assert "FOOBAR   sdkman" in captured.out


def test_install_all_empty(db_path, capsys):
    data = {"version": 1, "sudo": "no", "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    cmds.install_all()
    captured = capsys.readouterr()
    assert "No registered packages" in captured.out


def test_install_all_all_success(db_path, capsys):
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            "foobar": {
                "install": ["foobar", "install", "{source}"],
                "remove": ["foobar", "remove", "{source}"],
            },
        },
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "foobar", "name": "ruff", "source": "github:astral-sh/ruff"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "install") as mock_install:
        cmds.install_all()
    captured = capsys.readouterr()
    assert "Summary: 2 succeeded, 0 failed" in captured.out
    assert "PACKAGE" in captured.out
    assert "FOOBAR" in captured.out
    assert mock_install.call_count == 2


def test_install_all_partial_fail(db_path, capsys):
    data = {
        "version": 1,
        "sudo": "no",
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "package", "name": "jq"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "install") as mock_install:
        mock_install.side_effect = [None, subprocess.CalledProcessError(1, ["apt", "install", "-y", "jq"])]
        cmds.install_all()
    captured = capsys.readouterr()
    assert "Summary: 1 succeeded, 1 failed" in captured.out


def test_install_package(db_path, capsys):
    """Test install with @package manager (list of names)."""
    data = {"version": 1, "sudo": "no", "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "install") as mock_install:
        cmds.install("package", ["git", "jq"])
    assert mock_install.call_count == 2
    captured = capsys.readouterr()
    assert "git installed and registered" in captured.out
    assert "jq installed and registered" in captured.out


def test_install_custom_manager(db_path, capsys):
    """Test install with a custom manager (single name)."""
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            "foobar": {
                "install": ["foobar", "install", "{source}"],
                "remove": ["foobar", "remove", "{source}"],
            },
        },
        "packages": [],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "install") as mock_install:
        cmds.install("foobar", "ruff")
    mock_install.assert_called_once_with("foobar", "ruff", "ruff", sudo=False)
    captured = capsys.readouterr()
    assert "ruff installed and registered" in captured.out


def test_install_custom_manager_with_source(db_path, capsys):
    """Test install with a custom manager and explicit source."""
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            "foobar": {
                "install": ["foobar", "install", "{source}"],
                "remove": ["foobar", "remove", "{name}"],
            },
        },
        "packages": [],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "install") as mock_install:
        cmds.install("foobar", "pi-subagents")
    mock_install.assert_called_once_with("foobar", "pi-subagents", "pi-subagents", sudo=False)


def test_install_custom_manager_source_saved(db_path, capsys):
    """Test install with custom manager and explicit source != name saves source in DB."""
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            "foobar": {
                "install": ["foobar", "install", "{source}"],
                "remove": ["foobar", "remove", "{source}"],
            },
        },
        "packages": [],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "install") as mock_install:
        cmds.install("foobar", "ruff", "github:astral-sh/ruff")
    mock_install.assert_called_once_with("foobar", "ruff", "github:astral-sh/ruff", sudo=False)
    captured = capsys.readouterr()
    assert "ruff installed and registered" in captured.out
    assert "Source: github:astral-sh/ruff" in captured.out
    # Verify source was saved in the database
    pkg = cmds.store.find("ruff")
    assert pkg is not None
    assert pkg["source"] == "github:astral-sh/ruff"


def test_remove_auto_found(db_path, capsys):
    """Test remove with @auto (finds package by name)."""
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {},
        "packages": [{"type": "package", "name": "git"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "remove") as mock_remove:
        cmds.remove("auto", "git")
    captured = capsys.readouterr()
    assert "git removed from database" in captured.out


def test_remove_auto_not_found(db_path, capsys):
    """Test remove with @auto when package not found."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    cmds.remove("auto", "nonexistent")
    captured = capsys.readouterr()
    assert "not found" in captured.out


def test_remove_custom_manager(db_path, capsys):
    """Test remove with explicit @manager."""
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            "foobar": {
                "install": ["foobar", "install", "{source}"],
                "remove": ["foobar", "remove", "{source}"],
            },
        },
        "packages": [{"type": "foobar", "name": "ruff", "source": "github:astral-sh/ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "remove") as mock_remove:
        cmds.remove("foobar", "ruff")
    captured = capsys.readouterr()
    assert "ruff removed from database" in captured.out


# -- configure ----------------------------------------------------------


def test_configure_all_already_registered(db_path, capsys):
    """configure prints skip messages when all known managers are already in DB."""
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            name: {"install": install_cmd, "remove": remove_cmd}
            for name, (_, install_cmd, remove_cmd) in KNOWN_MANAGERS.items()
        },
        "packages": [],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    cmds.configure()
    captured = capsys.readouterr()
    assert "already registered" in captured.out
    assert "No new managers found" in captured.out


def test_configure_not_found_on_path(db_path, capsys):
    """configure skips manager when the executable is not on PATH."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck({name: None for name in KNOWN_MANAGERS}))
    cmds.configure()
    captured = capsys.readouterr()
    assert "not found on PATH" in captured.out
    assert "No new managers found" in captured.out


def test_configure_yes_adds_without_prompt(db_path, capsys):
    """configure --yes adds all detected managers without prompting."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    cmds.configure(yes=True)
    captured = capsys.readouterr()
    assert len(cmds.store.managers) == len(KNOWN_MANAGERS)
    for name, (_, install_cmd, remove_cmd) in KNOWN_MANAGERS.items():
        assert name in cmds.store.managers
        assert cmds.store.managers[name]["install"] == install_cmd
        assert cmds.store.managers[name]["remove"] == remove_cmd
    assert f"{len(KNOWN_MANAGERS)} manager(s) added" in captured.out


def test_configure_checkbox_select_some(db_path, capsys):
    """configure checkbox: user selects specific numbers."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    # Simulate first candidate; user picks '1'
    with (
        patch("builtins.input", return_value="1"),
    ):
        cmds.configure()
    captured = capsys.readouterr()
    assert "1 manager(s) added" in captured.out
    assert len(cmds.store.managers) == 1
    assert "[1]" in captured.out


def test_configure_checkbox_select_all(db_path, capsys):
    """configure checkbox: user types 'all'."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    with (
        patch("builtins.input", return_value="all"),
    ):
        cmds.configure()
    captured = capsys.readouterr()
    assert len(cmds.store.managers) == len(KNOWN_MANAGERS)
    assert f"{len(KNOWN_MANAGERS)} manager(s) added" in captured.out


def test_configure_checkbox_select_none(db_path, capsys):
    """configure checkbox: user types empty → selects none."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    with (
        patch("builtins.input", return_value=""),
    ):
        cmds.configure()
    captured = capsys.readouterr()
    assert "No managers added" in captured.out
    assert len(cmds.store.managers) == 0


def test_configure_checkbox_range(db_path, capsys):
    """configure checkbox: user selects a range '1-3'."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    with (
        patch("builtins.input", return_value="1-1"),
    ):
        cmds.configure()
    captured = capsys.readouterr()
    assert "1 manager(s) added" in captured.out


def test_configure_checkbox_invalid_then_valid(db_path, capsys):
    """configure checkbox: retries on invalid input."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    with (
        patch("builtins.input", side_effect=["abc", "99", "1"]),
    ):
        cmds.configure()
    captured = capsys.readouterr()
    assert "Invalid input" in captured.out
    assert "out of range" in captured.out
    assert "1 manager(s) added" in captured.out


def test_configure_partial_already_registered(db_path, capsys):
    """configure handles mix of already-registered and new managers."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    with (
        patch("builtins.input", return_value="1"),
    ):
        cmds.configure()
    assert len(cmds.store.managers) > 0


def test_configure_shows_summary(db_path, capsys):
    """configure prints registered custom managers summary."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    with (
        patch("builtins.input", return_value="3"),
    ):
        cmds.configure()
    captured = capsys.readouterr()
    assert "Registered custom managers" in captured.out
    assert "🔧" in captured.out
    assert "🗑️" in captured.out