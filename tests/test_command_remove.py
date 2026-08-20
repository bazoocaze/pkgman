"""
Tests for the remove command.
"""

import json
from unittest.mock import patch

from src.commands import Commands


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