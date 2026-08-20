"""
Tests for the update command.
"""

import json
import subprocess
from unittest.mock import patch

from src.commands import Commands


def test_update_single_package(db_path, capsys):
    """Update a single package by name."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "package", "name": "git"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "update") as mock_update:
        cmds.update(["git"])
    mock_update.assert_called_once_with("package", "git", "git", sudo=False)
    captured = capsys.readouterr()
    assert "git updated" in captured.out


def test_update_multiple_packages(db_path, capsys):
    """Update multiple packages by name."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "package", "name": "jq"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "update") as mock_update:
        cmds.update(["git", "jq"])
    assert mock_update.call_count == 2
    captured = capsys.readouterr()
    assert "git updated" in captured.out
    assert "jq updated" in captured.out


def test_update_not_found(db_path, capsys):
    """Update warns when package not in database."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    cmds.update(["nonexistent"])
    captured = capsys.readouterr()
    assert "not found" in captured.out


def test_update_all_empty(db_path, capsys):
    """update_all prints message when no packages registered."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    cmds.update_all()
    captured = capsys.readouterr()
    assert "No registered packages to update" in captured.out


def test_update_all_all_success(db_path, capsys):
    """update_all succeeds for all packages."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "package", "name": "jq"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "update") as mock_update:
        cmds.update_all()
    assert mock_update.call_count == 2
    captured = capsys.readouterr()
    assert "Summary: 2 succeeded, 0 failed" in captured.out


def test_update_all_partial_fail(db_path, capsys):
    """update_all reports partial failures."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "package", "name": "jq"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "update") as mock_update:
        mock_update.side_effect = [
            None,
            subprocess.CalledProcessError(1, ["apt", "install", "--only-upgrade", "-y", "jq"]),
        ]
        cmds.update_all()
    captured = capsys.readouterr()
    assert "Summary: 1 succeeded, 1 failed" in captured.out


def test_update_all_with_manager_filter(db_path, capsys):
    """update_all(manager='pi') only updates packages of that type."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "pi", "name": "golang", "source": "https://go.dev"},
            {"type": "pi", "name": "node", "source": "https://nodejs.org"},
            {"type": "uv", "name": "ruff"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "update") as mock_update:
        cmds.update_all(manager="pi")
    assert mock_update.call_count == 2
    captured = capsys.readouterr()
    assert "PI" in captured.out
    assert "PACKAGE" not in captured.out
    assert "UV" not in captured.out


def test_update_all_with_manager_empty(db_path, capsys):
    """update_all(manager='pi') warns when no packages of that type."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [
            {"type": "package", "name": "git"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    cmds.update_all(manager="pi")
    captured = capsys.readouterr()
    assert "No registered packages for '@pi' to update" in captured.out


def test_update_with_manager_match(db_path, capsys):
    """update(name, manager='pi') updates package when type matches."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [
            {"type": "pi", "name": "golang", "source": "https://go.dev"},
            {"type": "uv", "name": "ruff"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "update") as mock_update:
        cmds.update(["golang"], manager="pi")
    mock_update.assert_called_once_with("pi", "golang", "https://go.dev", sudo=False)
    captured = capsys.readouterr()
    assert "golang updated" in captured.out


def test_update_with_manager_mismatch(db_path, capsys):
    """update(name, manager='pi') warns when package type mismatch."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [
            {"type": "uv", "name": "ruff"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "update") as mock_update:
        cmds.update(["ruff"], manager="pi")
    mock_update.assert_not_called()
    captured = capsys.readouterr()
    assert "not found under '@pi'" in captured.out