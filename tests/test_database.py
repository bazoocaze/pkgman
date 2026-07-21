"""Tests for database.py – PackageStore (cache) + Database (raw I/O)."""

import json

import pytest
from database import Database, PackageStore
from constants import ManagerType


# =========================================================================
# PackageStore tests (cache + domain logic)
# =========================================================================

class TestPackageStore:
    """Tests for the PackageStore cache layer."""

    def test_new_store_is_empty(self, db_path):
        store = PackageStore(Database(db_path))
        store.load()
        assert store.packages == []
        assert store.sudo == "no"
        assert "uv" not in store.managers
        assert "script" not in store.managers

    def test_load_returns_packages(self, db_path):
        store = PackageStore(Database(db_path))
        pkgs = store.load()
        assert pkgs == []

    def test_add(self, empty_db):
        empty_db.add({"type": "package", "name": "git"})
        assert len(empty_db.packages) == 1
        assert empty_db.packages[0]["name"] == "git"

    def test_duplicate_is_ignored(self, empty_db):
        empty_db.add({"type": "package", "name": "git"})
        empty_db.add({"type": "package", "name": "git"})
        assert len(empty_db.packages) == 1

    def test_find(self, empty_db):
        empty_db.add({"type": "package", "name": "git"})
        assert empty_db.find("git") is not None
        assert empty_db.find("git")["name"] == "git"
        assert empty_db.find("nonexistent") is None

    def test_find_by_source(self, empty_db):
        empty_db.add({"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"})
        assert empty_db.find_by_source("github:astral-sh/ruff") is not None
        assert empty_db.find_by_source("github:astral-sh/ruff")["name"] == "ruff"
        assert empty_db.find_by_source("nonexistent") is None

    def test_find_by_source_none_if_no_source(self, empty_db):
        empty_db.add({"type": "package", "name": "git"})
        assert empty_db.find_by_source("git") is None

    def test_remove(self, empty_db):
        empty_db.add({"type": "package", "name": "git"})
        empty_db.remove("git")
        assert len(empty_db.packages) == 0

    def test_sudo_setter(self, empty_db):
        empty_db.sudo = "yes"
        assert empty_db.sudo == "yes"

    def test_managers_default(self, empty_db):
        assert "uv" not in empty_db.managers
        assert "script" not in empty_db.managers

    def test_validate_managers_ok(self, empty_db):
        empty_db.validate_managers()  # no exception

    def test_validate_managers_reserved(self, tmp_path):
        path = tmp_path / "db.json"
        data = {
            "version": 2,
            "sudo": "no",
            "managers": {"package": {"install": ["x"]}},
            "packages": [],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        store = PackageStore(Database(str(path)))
        with pytest.raises(ValueError, match="reserved"):
            store.load()

    def test_validate_managers_reserved_auto(self, tmp_path):
        path = tmp_path / "db.json"
        data = {
            "version": 2,
            "sudo": "no",
            "managers": {"auto": {"install": ["x"]}},
            "packages": [],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        store = PackageStore(Database(str(path)))
        with pytest.raises(ValueError, match="reserved"):
            store.load()


# =========================================================================
# Database tests (raw I/O)
# =========================================================================

class TestDatabase:
    """Tests for the raw Database layer."""

    def test_read_empty_file(self, raw_db):
        data = raw_db.read()
        assert data["packages"] == []
        assert data["sudo"] == "no"
        assert data["version"] == 2
        assert "uv" not in data["managers"]

    def test_read_missing_file(self, tmp_path):
        db = Database(str(tmp_path / "missing.json"))
        data = db.read()
        assert data["packages"] == []
        assert "uv" not in data["managers"]

    def test_read_malformed_json(self, db_path):
        with open(db_path, "w") as f:
            f.write("not json")
        db = Database(db_path)
        data = db.read()
        assert data["packages"] == []

    def test_write_and_read_roundtrip(self, raw_db):
        data = raw_db.read()
        data["packages"].append({"type": "package", "name": "git"})
        raw_db.write(data)
        read_back = raw_db.read()
        assert len(read_back["packages"]) == 1
        assert read_back["packages"][0]["name"] == "git"


# =========================================================================
# Migration tests (v1 → v2)
# =========================================================================

class TestMigration:
    """v1 → v2 schema migration tests."""

    def test_v1_sudo_persisted(self, db_path):
        data = {
            "version": 1,
            "sudo": "yes",
            "packages": [
                {"type": "script", "name": "uv", "url": "https://example.com"},
            ],
        }
        with open(db_path, "w") as f:
            json.dump(data, f)
        store = PackageStore(Database(db_path))
        store.load()
        assert "uv" not in store.managers
        assert len(store.packages) == 1

    def test_save_preserves_sudo(self, db_path):
        data = {
            "version": 1,
            "sudo": "yes",
            "packages": [
                {"type": "script", "name": "uv", "url": "https://example.com"},
            ],
        }
        with open(db_path, "w") as f:
            json.dump(data, f)
        store = PackageStore(Database(db_path))
        store.load()
        store.add({"type": "package", "name": "jq"})
        with open(db_path) as f:
            saved = json.load(f)
        assert saved["sudo"] == "yes"
        assert saved["version"] == 2
        assert "managers" in saved
        assert len(saved["packages"]) == 2

    def test_v1_migration_injects_managers(self, db_path):
        data = {
            "version": 1,
            "sudo": "no",
            "packages": [
                {"type": "package", "name": "git"},
                {"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"},
            ],
        }
        with open(db_path, "w") as f:
            json.dump(data, f)
        store = PackageStore(Database(db_path))
        store.load()
        assert "uv" not in store.managers
        assert "script" not in store.managers
        assert len(store.packages) == 2

        with open(db_path) as f:
            saved = json.load(f)
        assert saved["version"] == 2
        assert "managers" in saved

    def test_v2_file_loads_managers(self, db_path):
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
            json.dump(data, f)
        store = PackageStore(Database(db_path))
        store.load()
        assert "uv" in store.managers
        assert "script" not in store.managers
        assert len(store.packages) == 1

    def test_existing_managers_not_overwritten(self, db_path):
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
            json.dump(data, f)
        store = PackageStore(Database(db_path))
        store.load()
        assert store.managers["uv"]["install"] == ["custom", "install", "{source}"]

        # Load again: still the same
        store._invalidate()
        store.load()
        assert store.managers["uv"]["install"] == ["custom", "install", "{source}"]

    def test_empty_file_gets_default_managers(self, db_path):
        with open(db_path, "w") as f:
            f.write("")
        store = PackageStore(Database(db_path))
        store.load()
        assert store.packages == []
        assert "uv" not in store.managers
        assert "script" not in store.managers