import json
import os
import subprocess
from unittest.mock import patch

import pytest

from commands import Commands


def test_commands_init_sudo_no(db_path):
    data = {"version": 1, "sudo": "no", "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    assert cmds.db.sudo == "no"
    assert cmds._use_sudo is False


def test_use_sudo_property(db_path):
    data = {"version": 1, "sudo": "yes", "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    assert cmds._use_sudo is True
    cmds.db.sudo = "no"
    assert cmds._use_sudo is False


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
            {"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    cmds.list()
    captured = capsys.readouterr()
    assert "PACKAGE  testpkg" in captured.out
    assert "UV       ruff" in captured.out


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
        "version": 1,
        "sudo": "no",
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "script", "name": "uv", "url": "https://example.com/uv.sh"},
            {"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with (
        patch.object(cmds.manager, "install") as mock_install,
        patch("scripts.ScriptRunner.run") as mock_script,
        patch("uv_tools.UvTool.install") as mock_uv,
    ):
        cmds.install_all()
    captured = capsys.readouterr()
    assert "Summary: 3 succeeded, 0 failed" in captured.out
    assert "PACKAGE" in captured.out
    assert "SCRIPT" in captured.out
    assert "UV" in captured.out
    mock_install.assert_called_once_with("git", sudo=False)
    mock_script.assert_called_once_with("https://example.com/uv.sh")
    mock_uv.assert_called_once_with("github:astral-sh/ruff")


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
    with patch.object(cmds.manager, "install") as mock_install:
        mock_install.side_effect = [None, subprocess.CalledProcessError(1, ["apt", "install", "-y", "jq"])]
        cmds.install_all()
    captured = capsys.readouterr()
    assert "Summary: 1 succeeded, 1 failed" in captured.out
