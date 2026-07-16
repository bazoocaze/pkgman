import json
import tempfile

import pytest


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        path = f.name
    yield path
    import os
    os.unlink(path)


@pytest.fixture
def empty_db(db_path):
    from database import Database
    db = Database(db_path)
    db.load()
    return db
