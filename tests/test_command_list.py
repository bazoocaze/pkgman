"""
Tests for the list command.
"""

import json

from src.commands import Commands


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