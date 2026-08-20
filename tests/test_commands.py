"""
Tests for Commands base functionality (init).
"""

import json

from src.commands import Commands


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