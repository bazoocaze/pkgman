import json

import pytest
from database import Database


def test_new_database_is_empty(db_path):
    db = Database(db_path)
    pkgs = db.load()
    assert pkgs == []
    assert db.sudo == "no"
    assert db.version == 2
    assert "uv" in db.managers
    assert "script" in db.managers


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


def test_find_by_source(db_path):
    db = Database(db_path)
    db.load()
    db.add({"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"})
    assert db.find_by_source("github:astral-sh/ruff") is not None
    assert db.find_by_source("github:astral-sh/ruff")["name"] == "ruff"
    assert db.find_by_source("nonexistent") is None


def test_find_by_source_none_if_no_source(db_path):
    db = Database(db_path)
    db.load()
    db.add({"type": "package", "name": "git"})
    # package type has no source, so find_by_source should return None
    assert db.find_by_source("git") is None


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
    assert db.version == 2
    assert "uv" in db.managers
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
    assert saved["version"] == 2
    assert "managers" in saved
    assert len(saved["packages"]) == 2


def test_malformed_file_returns_empty(db_path):
    with open(db_path, "w") as f:
        f.write("invalid json")
    db = Database(db_path)
    pkgs = db.load()
    assert pkgs == []
    assert db.sudo == "no"
    assert "uv" in db.managers


def test_v1_migration_injects_managers(db_path):
    """v1 -> v2 migration: managers dict is injected."""
    data = {
        "version": 1,
        "sudo": "no",
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)

    db = Database(db_path)
    pkgs = db.load()

    assert db.version == 2
    assert "uv" in db.managers
    assert "script" in db.managers
    assert db.managers["uv"]["install"] == ["uv", "tool", "install", "{source}"]
    assert len(pkgs) == 2

    # Verify the file was updated to v2
    with open(db_path) as f:
        saved = json.load(f)
    assert saved["version"] == 2
    assert "managers" in saved
    assert saved["managers"]["uv"]["install"] == ["uv", "tool", "install", "{source}"]


def test_v2_file_loads_managers_correctly(db_path):
    """Test that loading a v2 file reads managers correctly."""
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            "uv": {
                "install": ["uv", "tool", "install", "{source}"],
                "remove": ["uv", "tool", "uninstall", "{name}"],
            },
        },
        "packages": [{"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)

    db = Database(db_path)
    pkgs = db.load()

    assert db.version == 2
    assert "uv" in db.managers
    assert "script" not in db.managers  # only what's in the file
    assert len(pkgs) == 1


def test_existing_managers_not_overwritten_on_subsequent_loads(db_path):
    """Managers already in the JSON are NOT overwritten by defaults."""
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            "uv": {
                "install": ["custom", "install", "{source}"],
                "remove": ["custom", "remove", "{name}"],
            },
        },
        "packages": [],
    }
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)

    db = Database(db_path)
    db.load()

    # The custom uv command should be preserved
    assert db.managers["uv"]["install"] == ["custom", "install", "{source}"]

    # Load again to ensure it's still preserved
    pkgs = db.load()
    assert db.managers["uv"]["install"] == ["custom", "install", "{source}"]


def test_reserved_manager_name_package_raises(db_path):
    """Using 'package' as a custom manager name should raise ValueError."""
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            "package": {
                "install": ["something"],
            },
        },
        "packages": [],
    }
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)

    db = Database(db_path)
    with pytest.raises(ValueError, match="reserved"):
        db.load()


def test_reserved_manager_name_auto_raises(db_path):
    """Using 'auto' as a custom manager name should raise ValueError."""
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            "auto": {
                "install": ["something"],
            },
        },
        "packages": [],
    }
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)

    db = Database(db_path)
    with pytest.raises(ValueError, match="reserved"):
        db.load()


def test_empty_file_gets_default_managers(db_path):
    """An empty file should get default managers injected."""
    with open(db_path, "w") as f:
        f.write("")
    db = Database(db_path)
    pkgs = db.load()
    assert pkgs == []
    assert "uv" in db.managers
    assert "script" in db.managers


def test_missing_file_gets_default_managers(tmp_path):
    """A non-existent file should get default managers."""
    path = tmp_path / "nonexistent.json"
    db = Database(str(path))
    pkgs = db.load()
    assert pkgs == []
    assert "uv" in db.managers
    assert "script" in db.managers
