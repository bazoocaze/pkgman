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
    assert "Names of OS packages to install" in r.stdout


def test_install_help_mentions_uv():
    r = run("install", "-h")
    assert r.returncode == 0
    assert "-uv" in r.stdout or "--uv" in r.stdout


def test_remove_help():
    r = run("remove", "-h")
    assert r.returncode == 0
    assert "Names of packages to remove" in r.stdout


def test_list_help():
    r = run("list", "-h")
    assert r.returncode == 0


def test_list_with_f_flag():
    data = {
        "version": 1,
        "sudo": "no",
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "script", "name": "uv", "url": "https://example.com"},
            {"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"},
        ],
    }
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        tmp = f.name
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    r = run("-f", tmp, "list")
    assert r.returncode == 0
    assert "PACKAGE  git" in r.stdout
    assert "SCRIPT   uv" in r.stdout
    assert "UV       ruff" in r.stdout
    import os
    os.unlink(tmp)


def test_install_no_args_exits_1():
    r = run("install")
    assert r.returncode == 1


def test_list_json():
    data = {
        "version": 1,
        "sudo": "no",
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "script", "name": "uv", "url": "https://example.com"},
            {"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"},
        ],
    }
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        tmp = f.name
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    r = run("-f", tmp, "list", "--json")
    assert r.returncode == 0
    result = json.loads(r.stdout)
    assert len(result) == 3
    assert result[0]["name"] == "git"
    assert result[0]["type"] == "package"
    assert result[1]["name"] == "uv"
    assert result[1]["url"] == "https://example.com"
    assert result[2]["name"] == "ruff"
    assert result[2]["type"] == "uv"
    assert result[2]["source"] == "github:astral-sh/ruff"
    import os
    os.unlink(tmp)


def test_list_json_empty():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        tmp = f.name
    with open(tmp, "w") as f:
        json.dump({"version": 1, "sudo": "no", "packages": []}, f)
    r = run("-f", tmp, "list", "--json")
    assert r.returncode == 0
    assert json.loads(r.stdout) == []
    import os
    os.unlink(tmp)
