import json

from database import Database


def test_new_database_is_empty(db_path):
    db = Database(db_path)
    pkgs = db.load()
    assert pkgs == []
    assert db.sudo == "no"


def test_add_package(db_path):
    db = Database(db_path)
    db.load()
    db.add({"type": "package", "name": "git"})
    pkgs = db.load()
    assert len(pkgs) == 1
    assert pkgs[0]["name"] == "git"
    assert db.sudo == "no"


def test_duplicate_is_ignored(db_path):
    db = Database(db_path)
    db.load()
    db.add({"type": "package", "name": "git"})
    db.add({"type": "package", "name": "git"})
    pkgs = db.load()
    assert len(pkgs) == 1


def test_find_package(db_path):
    db = Database(db_path)
    db.load()
    db.add({"type": "package", "name": "git"})
    assert db.find("git") is not None
    assert db.find("git")["name"] == "git"
    assert db.find("nonexistent") is None


def test_remove_package(db_path):
    db = Database(db_path)
    db.load()
    db.add({"type": "package", "name": "git"})
    db.remove("git")
    pkgs = db.load()
    assert len(pkgs) == 0


def test_sudo_persisted(db_path):
    data = {
        "version": 1,
        "sudo": "yes",
        "packages": [
            {"type": "script", "name": "uv", "url": "https://example.com"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)
    db = Database(db_path)
    pkgs = db.load()
    assert db.sudo == "yes"
    assert len(pkgs) == 1


def test_save_preserves_sudo(db_path):
    data = {
        "version": 1,
        "sudo": "yes",
        "packages": [
            {"type": "script", "name": "uv", "url": "https://example.com"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)
    db = Database(db_path)
    db.load()
    db.add({"type": "package", "name": "jq"})
    with open(db_path) as f:
        saved = json.load(f)
    assert saved["sudo"] == "yes"
    assert len(saved["packages"]) == 2


def test_malformed_file_returns_empty(db_path):
    with open(db_path, "w") as f:
        f.write("invalid json")
    db = Database(db_path)
    pkgs = db.load()
    assert pkgs == []
    assert db.sudo == "no"
