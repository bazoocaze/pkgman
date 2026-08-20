import json
import os
import tempfile

import pytest

from src.database import Database, PackageStore


class FakeSysCheck:
    """Mock SysCheck that returns custom PATH mappings."""

    def __init__(self, mapping: dict[str, str | None] | None = None) -> None:
        self._mapping = mapping or {}

    def which(self, executable: str) -> str | None:
        if executable in self._mapping:
            return self._mapping[executable]
        return "/usr/bin/" + executable


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def empty_db(db_path):
    """Return a Database + PackageStore ready for tests."""
    db = Database(db_path)
    store = PackageStore(db)
    store.load()
    return store


@pytest.fixture
def raw_db(db_path):
    """Return the raw Database (no cache)."""
    return Database(db_path)