"""
Tests for the configure command.
"""

import json
from unittest.mock import patch

from src.commands import Commands
from src.constants import KNOWN_MANAGERS

from .conftest import FakeSysCheck


def test_configure_all_already_registered(db_path, capsys):
    """configure prints skip messages when all known managers are already in DB."""
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            name: {"install": mgr["install"], "remove": mgr["remove"], "update": mgr["update"]}
            for name, mgr in KNOWN_MANAGERS.items()
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
    cmds = Commands(
        db_path=db_path,
        sys_check=FakeSysCheck({name: None for name in KNOWN_MANAGERS}),
    )
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
    for name, mgr in KNOWN_MANAGERS.items():
        assert name in cmds.store.managers
        assert cmds.store.managers[name]["install"] == mgr["install"]
        assert cmds.store.managers[name]["remove"] == mgr["remove"]
        assert cmds.store.managers[name]["update"] == mgr["update"]
    assert f"{len(KNOWN_MANAGERS)} manager(s) added" in captured.out


def test_configure_yes_persists_name_regex(db_path, capsys):
    """configure --yes persists name_regex when the known manager defines it."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    cmds.configure(yes=True)
    for name, mgr in KNOWN_MANAGERS.items():
        stored = cmds.store.managers[name]
        if mgr.get("name_regex"):
            assert stored["name_regex"] == mgr["name_regex"]
        else:
            assert "name_regex" not in stored


def test_configure_checkbox_select_some(db_path, capsys):
    """configure checkbox: user selects specific numbers."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    with patch("builtins.input", return_value="1"):
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
    with patch("builtins.input", return_value="all"):
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
    with patch("builtins.input", return_value=""):
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
    with patch("builtins.input", return_value="1-1"):
        cmds.configure()
    captured = capsys.readouterr()
    assert "1 manager(s) added" in captured.out


def test_configure_checkbox_invalid_then_valid(db_path, capsys):
    """configure checkbox: retries on invalid input."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    with patch("builtins.input", side_effect=["abc", "99", "1"]):
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
    with patch("builtins.input", return_value="1"):
        cmds.configure()
    assert len(cmds.store.managers) > 0


def test_configure_shows_summary(db_path, capsys):
    """configure prints registered custom managers summary."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path, sys_check=FakeSysCheck())
    with patch("builtins.input", return_value="3"):
        cmds.configure()
    captured = capsys.readouterr()
    assert "Registered custom managers" in captured.out
    assert "🔧" in captured.out
    assert "🗑️" in captured.out
    assert "🔄" in captured.out