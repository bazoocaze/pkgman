# Changelog

## [2.2.10] - 2026-08-19

### Changed

- All source modules moved from project root to `src/` package directory.
- Internal imports updated to use `src.` prefix (`from src.cli import ...`).
- `pyproject.toml`: replaced flat `py-modules` list with `packages = ["src"]`.
- `test.sh` / `test-integration.sh` renamed to `run-tests.sh` / `run-integration-tests.sh`.
- `AGENTS.md` updated to reflect new `src/` layout and scripts.

## [2.2.9] - 2026-08-05

### Added

- `pkgman doctor`: new check `_check_duplicate_identifiers` — warns when the
  same value appears as `name` or `source` in more than one package of the
  same manager type (cross-field, name-vs-source included).
- `PackageStore.update_source(name, source)` — add or update source on an
  existing package by name.

### Changed

- `pkgman install` now protects against duplicate `type`+`source` entries:
  errors on conflicting name/source, silently reinstalls when already
  registered, and allows upgrade from name-only to name+source.

## [2.2.8] - 2026-08-05

### Added

- New `pkgman doctor` command: diagnostic checks for database integrity, OS manager detection, manager executability on PATH, duplicate package names, and type-to-manager alignment.
- New module: `command_doctor.py` with `DoctorReport` and `run_doctor()`.

## [2.2.7] - 2026-08-05

### Added

- `pkgman update @manager -a` now filters updates to packages of that manager type only.
- `pkgman update @manager name` updates a specific package, verifying it belongs to the given manager.
- `update()` and `update_all()` in `Commands` accept optional `manager` parameter for programmatic filtering.

## [2.2.6] - 2026-08-05

### Added

- New `update` subcommand: `pkgman update <name>`, `pkgman update -a` to update registered packages.
- New `update_cmd` field on custom managers — each manager defines its own update command.
- `print_manager_summary` now shows update capability (🔄 icon) per custom manager.

### Changed

- `KNOWN_MANAGERS` restructured from tuple-of-4 to dict-of-dicts (`{exe, install, remove, update}`) for better encapsulation.
- `prompt_checkbox` refactored to generic `list[str] -> list[int]` — no longer coupled to manager data structure.
- `DEFAULT_MANAGERS` removed (always empty, unused indirection).

## [2.2.5] - 2026-07-21

### Fixed

- Manager subprocesses now run with real stdout/stderr and stdin/tty passthrough instead of capturing output, restoring interactive prompts and live output.

## [2.2.4] - 2026-07-20

### Added

- New known manager `@zsh` (script from URL piped to zsh, similar to `@bash`).

### Changed

- `configure` tests refactored to use `KNOWN_MANAGERS` dynamically — no hardcoded manager names in assertions, resilient to future additions.

## [2.2.3] - 2026-07-20

### Fixed

- Break encapsulation between KNOWN_MANAGERS and tests: synthetic manager `foobar` replaces real manager names (uv/bash/pi) in custom-manager test scenarios. Single validation test in `test_known_managers.py` guards against accidental changes to KNOWN_MANAGERS values.

## [2.2.2] - 2026-07-20

### Breaking

- Rename manager `script` → `bash`; moved from DEFAULT_MANAGERS to KNOWN_MANAGERS (now opt-in via `configure`).
  - Existing databases with `"type": "script"` packages must be manually migrated to `"type": "bash"`.
  - The `@script` prefix is no longer recognized; use `@bash` instead.

### Fixed

- `uv` remove command now uses `{source}` instead of `{name}` for correct uninstall of packages with explicit sources.

## [1.0.0] - 2026-07-16

### Added

- `--uv` now accepts 1 argument (name only, source defaults to name).
  - `pkgman install --uv ruff` installs `ruff` from PyPI.
  - `pkgman install --uv ruff github:astral-sh/ruff` still works (2 args).

## [Unreleased]

### Added

- Support for `uv` tool packages via `pkgman install --uv <name> <source>`.
  - Installs Python tools using `uv tool install <source>`.
  - Removes them using `uv tool uninstall <name>`.
  - Replay (`install -a`) and list work for `"type": "uv"` entries.
  - New database entry format: `{"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"}`
  - New module: `uv_tools.py` with `UvTool` class.
  - Updated `commands.py`, `pkgman.py` (argparse), `tests.py`, and `AGENTS.md`.