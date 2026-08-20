"""Tests for the doctor module."""

import json

from src.database import Database, PackageStore
from src.command_doctor import DoctorReport, run_doctor


class FakeSysCheck:
    def __init__(self, mapping: dict[str, str | None] | None = None) -> None:
        self._mapping = mapping or {}

    def which(self, executable: str) -> str | None:
        if executable in self._mapping:
            return self._mapping[executable]
        return "/usr/bin/" + executable


def test_report_ok_warn_error(capsys):
    report = DoctorReport()
    report.ok("one")
    report.warn("two")
    report.error("three")
    assert report.has_errors is True
    report.print()
    captured = capsys.readouterr()
    assert "one" in captured.out
    assert "two" in captured.out
    assert "three" in captured.out


def test_report_no_errors():
    report = DoctorReport()
    report.ok("all good")
    report.warn("minor issue")
    assert report.has_errors is False


def test_run_doctor_all_ok(db_path, capsys):
    data = {"version": 2, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)

    db = Database(db_path)
    store = PackageStore(db)
    store.load()

    sys_check = FakeSysCheck()
    report = run_doctor(store, sys_check)
    report.print()
    captured = capsys.readouterr()

    assert report.has_errors is False
    assert "Database: valid JSON, schema" in captured.out
    assert "OS package manager" in captured.out
    assert "No duplicate" in captured.out
    assert "All package types match" in captured.out


def test_run_doctor_db_not_found(capsys):
    db = Database("/tmp/.pkgman_nonexistent_test.json")
    store = PackageStore(db)
    store.load()

    report = run_doctor(store, FakeSysCheck())
    report.print()
    captured = capsys.readouterr()

    assert report.has_errors is True
    assert "Database file not found" in captured.out


def test_run_doctor_invalid_json(db_path, capsys):
    with open(db_path, "w") as f:
        f.write("not valid json")

    db = Database(db_path)
    store = PackageStore(db)
    store.load()

    report = run_doctor(store, FakeSysCheck())
    report.print()
    captured = capsys.readouterr()

    assert report.has_errors is True
    assert "not valid JSON" in captured.out


def test_run_doctor_wrong_schema(db_path, capsys):
    data = {"version": 99, "sudo": "no", "managers": {}, "packages": []}
    with open(db_path, "w") as f:
        json.dump(data, f)

    db = Database(db_path)
    store = PackageStore(db)
    store.load()

    report = run_doctor(store, FakeSysCheck())
    report.print()
    captured = capsys.readouterr()

    assert report.has_errors is True
    assert "schema version" in captured.out or "99" in captured.out


def test_run_doctor_duplicate_names(db_path, capsys):
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {},
        "packages": [
            {"type": "package", "name": "git"},
            {"type": "package", "name": "git"},
        ],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)

    db = Database(db_path)
    store = PackageStore(db)
    store.load()

    report = run_doctor(store, FakeSysCheck())
    report.print()
    captured = capsys.readouterr()

    assert report.has_errors is False
    assert "Duplicate" in captured.out


def test_run_doctor_type_without_manager(db_path, capsys):
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {},
        "packages": [{"type": "foobar", "name": "ruff"}],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)

    db = Database(db_path)
    store = PackageStore(db)
    store.load()

    report = run_doctor(store, FakeSysCheck())
    report.print()
    captured = capsys.readouterr()

    assert report.has_errors is True
    assert "no manager '@foobar' is registered" in captured.out


def test_run_doctor_manager_not_on_path(db_path, capsys):
    data = {
        "version": 2,
        "sudo": "no",
        "managers": {
            "uv": {"install": ["uv", "tool", "install", "{source}"]},
        },
        "packages": [],
    }
    with open(db_path, "w") as f:
        json.dump(data, f)

    db = Database(db_path)
    store = PackageStore(db)
    store.load()

    sys_check = FakeSysCheck(mapping={"uv": None})
    report = run_doctor(store, sys_check)
    report.print()
    captured = capsys.readouterr()

    assert report.has_errors is True
    assert "uv" in captured.out
    assert "not found on PATH" in captured.out