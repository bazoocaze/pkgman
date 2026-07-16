import pytest
from uv_tools import UvTool


def test_uv_install_command():
    cmd = UvTool._build_cmd("install", "github:astral-sh/ruff")
    assert cmd == ["uv", "tool", "install", "github:astral-sh/ruff"]


def test_uv_remove_command():
    cmd = UvTool._build_cmd("remove", "ruff")
    assert cmd == ["uv", "tool", "uninstall", "ruff"]


def test_unknown_uv_action_raises():
    with pytest.raises(RuntimeError, match="Unknown uv action"):
        UvTool._build_cmd("upgrade", "ruff")
