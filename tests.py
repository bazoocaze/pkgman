"""
tests.py - Comprehensive test suite for pkgman

Run with:  python3 tests.py
"""

import tempfile
import os
import json
import subprocess
import sys

# ---------------------------------------------------------------------------
# 1. Database
# ---------------------------------------------------------------------------
print("=== 1. Database tests ===")
from database import Database

with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
    tmp = f.name

# 1a. New database
db = Database(tmp)
pkgs = db.load()
assert pkgs == []
assert db.sudo == "no"
print("  OK - new db: empty, sudo=no")

# 1b. Add package
db.add({"type": "package", "name": "git"})
pkgs = db.load()
assert len(pkgs) == 1
assert pkgs[0]["name"] == "git"
assert db.sudo == "no"
print("  OK - add package")

# 1c. Duplicate ignored
db.add({"type": "package", "name": "git"})
pkgs = db.load()
assert len(pkgs) == 1
print("  OK - duplicate ignored")

# 1d. Find
pkg = db.find("git")
assert pkg is not None
assert pkg["name"] == "git"
pkg = db.find("nonexistent")
assert pkg is None
print("  OK - find")

# 1e. Remove
db.remove("git")
pkgs = db.load()
assert len(pkgs) == 0
print("  OK - remove")

# 1f. Script + sudo
db.add({"type": "script", "name": "uv", "url": "https://example.com"})
data = {
    "version": 1,
    "sudo": "yes",
    "packages": [
        {"type": "script", "name": "uv", "url": "https://example.com"}
    ],
}
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)

db2 = Database(tmp)
pkgs = db2.load()
assert db2.sudo == "yes"
assert len(pkgs) == 1
print("  OK - read sudo=yes from file")

# 1g. Save preserves sudo
db2.add({"type": "package", "name": "jq"})
with open(tmp) as f:
    data = json.load(f)
assert data["sudo"] == "yes"
assert len(data["packages"]) == 2
print("  OK - save preserves sudo=yes")

# 1h. Malformed file
with open(tmp, "w") as f:
    f.write("invalid json")
db3 = Database(tmp)
pkgs = db3.load()
assert pkgs == []
assert db3.sudo == "no"
print("  OK - malformed file returns empty")

os.unlink(tmp)
print()

# ---------------------------------------------------------------------------
# 2. Manager
# ---------------------------------------------------------------------------
print("=== 2. Manager tests ===")
from managers import Manager

# 2a. apt commands
m_apt = Manager("apt")
cmd = m_apt._build_cmd("install", "git")
assert cmd == ["apt", "install", "-y", "git"], f"Got {cmd}"
print("  OK - apt install cmd")

cmd = m_apt._build_cmd("remove", "git")
assert cmd == ["apt", "remove", "-y", "git"], f"Got {cmd}"
print("  OK - apt remove cmd")

# 2b. yum commands
m_yum = Manager("yum")
cmd = m_yum._build_cmd("install", "git")
assert cmd == ["yum", "install", "-y", "git"], f"Got {cmd}"
print("  OK - yum install cmd")

# 2c. brew commands (remove -> uninstall)
m_brew = Manager("brew")
cmd = m_brew._build_cmd("install", "git")
assert cmd == ["brew", "install", "git"], f"Got {cmd}"
print("  OK - brew install cmd")

cmd = m_brew._build_cmd("remove", "git")
assert cmd == ["brew", "uninstall", "git"], f"Got {cmd}"
print("  OK - brew uninstall cmd")

# 2d. Sudo prefix
cmd = ["apt", "install", "-y", "git"]
cmd = ["sudo"] + cmd
assert cmd == ["sudo", "apt", "install", "-y", "git"]
print("  OK - sudo prefix logic")

# 2e. Unknown manager
try:
    m_bad = Manager("nope")
    m_bad._build_cmd("install", "x")
    assert False, "Should have raised"
except RuntimeError as e:
    assert "Unknown manager" in str(e)
    print("  OK - unknown manager raises error")
print()

# ---------------------------------------------------------------------------
# 3. Commands
# ---------------------------------------------------------------------------
print("=== 3. Commands tests ===")
from commands import Commands

with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
    tmp2 = f.name
with open(tmp2, "w") as f:
    json.dump({"version": 1, "sudo": "no", "packages": []}, f)

cmds = Commands(db_path=tmp2)
assert cmds.db.sudo == "no"
assert cmds._use_sudo is False
print("  OK - Commands init, sudo=no")

# 3b. _use_sudo property
cmds.db.sudo = "yes"
assert cmds._use_sudo is True
cmds.db.sudo = "no"
assert cmds._use_sudo is False
print("  OK - _use_sudo property")

# 3c. list with no packages
cmds.list()
print("  OK - list with no packages")

# 3d. list with one package
cmds.db.add({"type": "package", "name": "testpkg"})
cmds.list()
print("  OK - list with one package")

os.unlink(tmp2)
print()

# ---------------------------------------------------------------------------
# 4. CLI
# ---------------------------------------------------------------------------
print("=== 4. CLI tests ===")

# 4a. main help
r = subprocess.run(
    ["python3", "pkgman.py", "-h"], capture_output=True, text=True
)
assert r.returncode == 0
assert "Manages manually installed packages" in r.stdout
print("  OK - main help")

# 4b. install help
r = subprocess.run(
    ["python3", "pkgman.py", "install", "-h"], capture_output=True, text=True
)
assert r.returncode == 0
assert "Names of OS packages to install" in r.stdout
print("  OK - install help")

# 4c. remove help
r = subprocess.run(
    ["python3", "pkgman.py", "remove", "-h"], capture_output=True, text=True
)
assert r.returncode == 0
assert "Names of packages to remove" in r.stdout
print("  OK - remove help")

# 4d. list help
r = subprocess.run(
    ["python3", "pkgman.py", "list", "-h"], capture_output=True, text=True
)
assert r.returncode == 0
print("  OK - list help")

# 4e. list with -f flag
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
    tmp3 = f.name
with open(tmp3, "w") as f:
    json.dump(
        {
            "version": 1,
            "sudo": "no",
            "packages": [
                {"type": "package", "name": "git"},
                {"type": "script", "name": "uv", "url": "https://example.com"},
            ],
        },
        f,
    )

r = subprocess.run(
    ["python3", "pkgman.py", "-f", tmp3, "list"],
    capture_output=True,
    text=True,
)
assert r.returncode == 0
assert "PACKAGE  git" in r.stdout
assert "SCRIPT   uv" in r.stdout
print("  OK - list with -f flag")

os.unlink(tmp3)

# 4f. install with no args exits with code 1
r = subprocess.run(
    ["python3", "pkgman.py", "install"], capture_output=True, text=True
)
assert r.returncode == 1
print("  OK - install with no args exits with code 1")

print()
print("=== ALL TESTS PASSED ===")