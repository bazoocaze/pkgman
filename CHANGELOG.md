# Changelog

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