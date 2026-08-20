"""
Tests for the install command (_install_single, install_all, _check_install_conflict).
"""

import json
import subprocess
from unittest.mock import patch

from src.commands import Commands, InstallConflictResult


# ---------------------------------------------------------------------------
# install (public API)
# ---------------------------------------------------------------------------


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
        mock_install.side_effect = [
            None,
            subprocess.CalledProcessError(1, ["apt", "install", "-y", "jq"]),
        ]
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
    pkg = cmds.store.find("ruff")
    assert pkg is not None
    assert pkg["source"] == "github:astral-sh/ruff"


# ---------------------------------------------------------------------------
# _check_install_conflict
# ---------------------------------------------------------------------------


def test_check_conflict_new(db_path):
    """No existing packages → action='new'."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    result = cmds._check_install_conflict("package", "git", "git")
    assert result.action == "new"
    assert result.run_source == "git"
    assert result.error_msg is None


def test_check_conflict_new_other_type(db_path):
    """Existing packages of different types → action='new'."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    result = cmds._check_install_conflict("package", "git", "git")
    assert result.action == "new"
    assert result.run_source == "git"


def test_check_conflict_case1_error(db_path):
    """Case 1: same type+source (explicit), different name → error."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    result = cmds._check_install_conflict("uv", "ruff-package", "github:astral-sh/ruff")
    assert result.action == "error"
    assert "same source" in result.error_msg


def test_check_conflict_case2_upgrade(db_path):
    """Case 2: same name, existing no source, new explicit source → upgrade."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "foobar", "name": "ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    result = cmds._check_install_conflict("foobar", "ruff", "github:astral-sh/ruff")
    assert result.action == "upgrade"
    assert result.run_source == "github:astral-sh/ruff"
    assert result.error_msg is None


def test_check_conflict_case3_reinstall(db_path):
    """Case 3: exact match (same name+source) → reinstall."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    result = cmds._check_install_conflict("uv", "ruff", "github:astral-sh/ruff")
    assert result.action == "reinstall"
    assert result.run_source == "github:astral-sh/ruff"
    assert result.error_msg is None


def test_check_conflict_case4_error(db_path):
    """Case 4: same name, existing source, new different source → error."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "foobar", "name": "ruff", "source": "github:astral-sh/ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    result = cmds._check_install_conflict("foobar", "ruff", "github:astral-sh/ruff-old")
    assert result.action == "error"
    assert "refusing to overwrite" in result.error_msg


def test_check_conflict_case5_reinstall(db_path):
    """Case 5: same name, existing has source, new has no source → reinstall with stored source."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "foobar", "name": "ruff", "source": "github:astral-sh/ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    result = cmds._check_install_conflict("foobar", "ruff", "ruff")
    assert result.action == "reinstall"
    assert result.run_source == "github:astral-sh/ruff"
    assert result.error_msg is None


def test_check_conflict_skips_unrelated_type(db_path):
    """Packages of other types don't affect conflict detection."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [
            {"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"},
            {"type": "bash", "name": "sdkman", "source": "https://get.sdkman.io"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    result = cmds._check_install_conflict("package", "git", "git")
    assert result.action == "new"


def test_check_conflict_multiple_packages_only_one_match(db_path):
    """Only the matching package triggers a conflict, others are ignored."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [
            {"type": "foobar", "name": "pkg-a"},
            {"type": "foobar", "name": "pkg-b"},
            {"type": "foobar", "name": "ruff", "source": "github:astral-sh/ruff"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    result = cmds._check_install_conflict("foobar", "ruff", "other-source")
    assert result.action == "error"


def test_check_conflict_case1_ignores_non_explicit_source(db_path):
    """Case 1 only triggers when both sources are explicit (source != name)."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "package", "name": "git"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    result = cmds._check_install_conflict("package", "jq", "jq")
    assert result.action == "new"


# ---------------------------------------------------------------------------
# _install_single – consolidated install flow
# ---------------------------------------------------------------------------


def test_install_single_new_calls_registry_once(db_path, capsys):
    """New install: registry.install is called exactly once, then store.add."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "install") as mock_install:
        cmds._install_single("package", "git", None)
    mock_install.assert_called_once_with("package", "git", "git", sudo=False)
    assert cmds.store.find("git") is not None
    captured = capsys.readouterr()
    assert "installed and registered" in captured.out


def test_install_single_reinstall_no_db_change(db_path, capsys):
    """Reinstall: registry.install is called but DB is not mutated."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    original_packages = list(cmds.store.packages)
    with patch.object(cmds.registry, "install") as mock_install:
        cmds._install_single("uv", "ruff", "github:astral-sh/ruff")
    mock_install.assert_called_once_with("uv", "ruff", "github:astral-sh/ruff", sudo=False)
    assert cmds.store.packages == original_packages


def test_install_single_upgrade_calls_update_source(db_path, capsys):
    """Upgrade: registry.install called then store.update_source."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "foobar", "name": "ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(cmds.registry, "install") as mock_install:
        cmds._install_single("foobar", "ruff", "github:astral-sh/ruff")
    mock_install.assert_called_once_with("foobar", "ruff", "github:astral-sh/ruff", sudo=False)
    pkg = cmds.store.find("ruff")
    assert pkg["source"] == "github:astral-sh/ruff"


def test_install_single_error_no_registry_call(db_path, capsys):
    """Conflict error: registry.install is NOT called, DB unchanged."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "foobar", "name": "ruff", "source": "github:astral-sh/ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    original_packages = list(cmds.store.packages)
    with patch.object(cmds.registry, "install") as mock_install:
        cmds._install_single("foobar", "ruff", "other-source")
    mock_install.assert_not_called()
    assert cmds.store.packages == original_packages


def test_install_single_registry_fails_no_db_mutation(db_path, capsys):
    """When registry.install raises, DB must NOT be mutated."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    original_packages = list(cmds.store.packages)
    with patch.object(
        cmds.registry, "install", side_effect=subprocess.CalledProcessError(1, ["apt"])
    ):
        cmds._install_single("package", "git", None)
    assert cmds.store.packages == original_packages


def test_install_single_upgrade_registry_fails_no_db_mutation(db_path, capsys):
    """Upgrade: when registry.install raises, update_source must NOT be called."""
    data = {
        "version": 2, "sudo": "no", "managers": {},
        "packages": [{"type": "foobar", "name": "ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    cmds = Commands(db_path=db_path)
    with patch.object(
        cmds.registry, "install", side_effect=subprocess.CalledProcessError(1, ["foobar"])
    ):
        cmds._install_single("foobar", "ruff", "github:astral-sh/ruff")
    pkg = cmds.store.find("ruff")
    assert pkg is not None
    assert "source" not in pkg or pkg["source"] is None