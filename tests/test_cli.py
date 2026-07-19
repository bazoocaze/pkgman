import json
import subprocess
import tempfile


def run(*args):
    return subprocess.run(
        ["python3", "pkgman.py", *args],
        capture_output=True,
        text=True,
    )


def test_main_help():
    r = run("--help")
    assert r.returncode == 0
    assert "Manages manually installed packages" in r.stdout + r.stderr


def test_install_help():
    r = run("install", "-h")
    assert r.returncode == 0
    assert "@MANAGER" in r.stdout
    assert "NAME" in r.stdout
    assert "SOURCE" in r.stdout


def test_install_help_no_uv_flag():
    """--uv flag should no longer exist in v2."""
    r = run("install", "-h")
    assert r.returncode == 0
    assert "--uv" not in r.stdout


def test_remove_help():
    r = run("remove", "-h")
    assert r.returncode == 0
    assert "@MANAGER" in r.stdout
    assert "NAME" in r.stdout


def test_list_help():
    r = run("list", "-h")
    assert r.returncode == 0


def test_install_no_args_exits_nonzero():
    """install requires at least one arg -> non-zero exit code."""
    r = run("install")
    assert r.returncode != 0


def test_install_git_works(db_path):
    """pkgman install git -> @package implicit, works with -f."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    # This will fail to actually install (no apt), but we just test parsing
    # The important thing is it doesn't fail with argparse error
    r = run("-f", db_path, "install", "git")
    # It will fail at runtime because no package manager, but not at CLI parsing
    assert r.returncode != 2  # not an argparse error


def test_install_at_uv_ruff_parses(db_path):
    """pkgman install @uv ruff -> parses correctly."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    r = run("-f", db_path, "install", "@uv", "ruff")
    # Not an argparse error (exit code 2 would be argparse error)
    assert r.returncode != 2


def test_install_at_pi_name_source_parses(db_path):
    """pkgman install @pi name source -> parses correctly."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    r = run("-f", db_path, "install", "@pi", "pi-subagents", "npm:@tintinweb/pi-subagents")
    assert r.returncode != 2


def test_remove_git_parses(db_path):
    """pkgman remove git -> @auto implicit, parses correctly."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": [{"type": "package", "name": "git"}]}
    with open(db_path, "w") as f:
        json.dump(data, f)
    r = run("-f", db_path, "remove", "git")
    assert r.returncode != 2


def test_remove_at_pi_name_parses(db_path):
    """pkgman remove @pi name -> parses correctly."""
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)
    r = run("-f", db_path, "remove", "@pi", "pi-subagents")
    assert r.returncode != 2


def test_list_with_f_flag_v1_auto_migration(db_path):
    """Test that v1 DB is auto-migrated on list."""
    data = {
        "version": 1,
        "sudo": "no",
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "script", "name": "uv", "url": "https://example.com"},
            {"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)
    r = run("-f", db_path, "list")
    assert r.returncode == 0
    assert "PACKAGE  git" in r.stdout
    # After migration, script uses source field, not url
    assert "uv" in r.stdout
    assert "ruff" in r.stdout


def test_list_json_v1_auto_migration(db_path):
    """Test that v1 JSON output works after migration."""
    data = {
        "version": 1,
        "sudo": "no",
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "script", "name": "uv", "url": "https://example.com"},
            {"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)
    r = run("-f", db_path, "list", "--json")
    assert r.returncode == 0
    result = json.loads(r.stdout)
    assert len(result) == 3
    assert result[0]["name"] == "git"
    assert result[0]["type"] == "package"
    assert result[1]["name"] == "uv"
    assert result[1]["type"] == "script"
    assert result[2]["name"] == "ruff"
    assert result[2]["type"] == "uv"
    assert result[2]["source"] == "github:astral-sh/ruff"


def test_list_json_empty(db_path):
    with open(db_path, "w") as f:
        json.dump({"version": 2, "sudo": "no", "managers": {}, "packages": []}, f)
    r = run("-f", db_path, "list", "--json")
    assert r.returncode == 0
    assert json.loads(r.stdout) == []