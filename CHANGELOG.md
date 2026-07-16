# Changelog

## [Unreleased]

### Added

- Support for `uv` tool packages via `pkgman install --uv <name> <source>`.
  - Installs Python tools using `uv tool install <source>`.
  - Removes them using `uv tool uninstall <name>`.
  - Replay (`install -a`) and list work for `"type": "uv"` entries.
  - New database entry format: `{"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"}`
  - New module: `uv_tools.py` with `UvTool` class.
  - Updated `commands.py`, `pkgman.py` (argparse), `tests.py`, and `AGENTS.md`.