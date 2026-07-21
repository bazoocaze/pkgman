# pkgman

Declarative layer over OS package managers. Manages the list of **manually**
installed packages (separating them from system dependencies) and allows
full **replay** on fresh machines.

## Install

```
uv tool install git+https://github.com/bazoocaze/pkgman
pipx install git+https://github.com/bazoocaze/pkgman
```

## Commands

```
pkgman install git jq                                # OS packages (default @package)
pkgman install @uv ruff                              # Python tool via uv (name == source)
pkgman install @uv ruff github:astral-sh/ruff        # uv tool with explicit source
pkgman install @bash sdkman https://get.sdkman.io  # script from URL
pkgman install @pi name source                       # custom manager
pkgman install -a                                    # replay: reinstall ALL from the database
pkgman remove git                                    # @auto: finds package by name
pkgman remove @pi name                               # explicit manager
pkgman list                                          # list registered packages
pkgman list --json                                   # list as JSON
pkgman configure                                     # detect known managers, add interactively
pkgman configure -y                                  # non-interactive: add all detected
pkgman -f ~/my_database.json list                    # use an alternative database
```

## Architecture

```
pkgman.py          → entry point + argparse
commands.py        → orchestrator (install/remove/list/configure)
database.py        → CRUD for ~/.config/.pkgman_database.json (v2 schema with managers)
managers.py        → Manager (detection + execution of apt/yum/brew) and
                     ManagerRegistry + CustomManager (unified custom managers)
constants.py       → enums (ManagerType, SudoSetting), DB_VERSION, DEFAULT_MANAGERS,
                     KNOWN_MANAGERS, RESERVED_MANAGERS
cli.py             → argparse setup + handler dispatch (COMMAND_DISPATCH)
output.py          → console formatting (Report, format_package_list, _snippet)
ui.py              → interactive UI helpers (prompt_checkbox, print_manager_summary)
runner.py          → ProcessRunner protocol + SubprocessRunner (subprocess.run wrapper)
tests/             → pytest test suite (89 tests)
pyproject.toml     → build config + entry point (pkgman = "pkgman:main")
```

---

## API cheat sheet – symbols you can import

### constants.py
| Symbol | Description |
|---|---|
| `ManagerType.PACKAGE`, `.AUTO` | `"package"`, `"auto"` |
| `SudoSetting.YES`, `.NO` | `"yes"`, `"no"` |
| `DB_VERSION` | Current schema version (2) |
| `DEFAULT_MANAGERS` | `dict` — managers always present: (none by default) |
| `KNOWN_MANAGERS` | `dict` — `name → (exe, install_cmd, remove_cmd)`. Used by `configure`. |
| `RESERVED_MANAGERS` | `frozenset({"package", "auto"})` — forbidden as custom manager names |

### commands.py
```
Commands(db_path: str|Path = None, *, runner: ProcessRunner = None)

  # properties
  .store: PackageStore      # the loaded DB cache
  .registry: ManagerRegistry  # routes install/remove to correct manager

  # methods
  .install(manager: str, name_or_names: str|list[str], source: str|None = None) -> None
  .install_all() -> None
  .remove(manager: str, name: str) -> None
  .list(*, json_output: bool = False) -> None
  .configure(*, yes: bool = False) -> None

  # internal
  ._sudo -> bool            # True when store.sudo == "yes"
  ._sudo_for(manager) -> bool  # sudo only applies to @package
```

### database.py
```
Database(path: str|Path = None)
  .read() -> dict           # raw JSON from disk
  .write(data: dict) -> None

PackageStore(db: Database)
  .load() -> list[dict]     # populate cache
  .save() -> None           # persist to disk
  .add(package: dict) -> None     # ignore duplicates by name; auto-saves
  .remove(name: str) -> None      # auto-saves
  .find(name: str) -> dict|None
  .find_by_source(source: str) -> dict|None

  .sudo: str                # "yes" / "no" (setter persists)
  .managers: dict           # mutable ref to managers dict
  .packages: list[dict]     # copy of package list
```

**Important:** `store.managers[k] = v` mutates directly but does NOT auto-save — call `store.save()` after.

### managers.py
```
Manager(name: str, *, runner: ProcessRunner = None)
  .install(package_name: str, *, sudo: bool = False) -> None
  .remove(package_name: str, *, sudo: bool = False) -> None

CustomManager(name: str, install_cmd: list|str|None, remove_cmd: list|str|None)

ManagerRegistry(store, runner: ProcessRunner = SubprocessRunner())
  .get(manager_name: str) -> CustomManager|None
  .install(manager_name, name, source, *, sudo=False) -> None
  .remove(manager_name, name, source, *, sudo=False) -> None
  .resolve_auto(name_or_source: str) -> tuple[str, dict]|None

detect_os_manager() -> Manager|None   # brew > apt > yum
_substitute(cmd, name, source)        # replaces {name}/{source} placeholders
```

### runner.py
```
ProcessRunner (Protocol)
  .run(cmd: list[str]|str, *, shell: bool = False) -> None

SubprocessRunner()           # real impl; raises CalledProcessError on failure
```

### output.py
```
Report()
  .add_ok(ptype: str, name: str, detail: str = "") -> None
  .add_fail(ptype: str, name: str, detail: str = "", snippet: str = "") -> None
  .print() -> None

format_package_list(packages: list[dict], *, json_output: bool = False) -> str
```

### ui.py
```
prompt_checkbox(candidates: list[tuple[str, str, list|str, list|str|None]]) -> list
print_manager_summary(managers: dict) -> None
```

- `prompt_checkbox` — interactive numbered selection prompt for configure
- `print_manager_summary` — prints registered custom managers with install/remove icons

### cli.py
```
build_parser() -> ArgumentParser
COMMAND_DISPATCH: dict[str, callable]   # {"install": ..., "remove": ..., "list": ..., "configure": ...}
parse_install_args(args: list[str]) -> (manager, names|name, source|None)
parse_remove_args(args: list[str]) -> (manager, name)
```

---

## Adding a new subcommand

1. **`cli.py`**: add subparser in `build_parser()`, create `_handle_xxx(cmds, args)`, register in `COMMAND_DISPATCH`
2. **`commands.py`**: add method on `Commands`
3. If adding a new `.py` file: include its module name in `[tool.setuptools] py-modules` in `pyproject.toml`

## Adding a new known manager (for `configure`)

Add entry to `KNOWN_MANAGERS` in `constants.py`:
```python
"name": (
    "executable",                              # checked via shutil.which()
    ["cmd", "install", "{source}"],            # install template
    ["cmd", "remove", "{source}"],             # remove template (or None)
),
```

## Testing conventions
| Convention | Detail |
|---|---|
| Fixture `db_path` | Temp JSON file, auto-cleaned (`tests/conftest.py`) |
| Fixture `empty_db` | Returns a ready-to-use `PackageStore` |
| Mock install/remove | `patch.object(cmds.registry, "install")` / `"remove"` |
| Mock PATH detection | `patch("commands.shutil.which", return_value=...)` |
| Mock user input | `patch("builtins.input", return_value=...)` or `side_effect=[...]` |
| Capture output | `capsys.readouterr()` (pytest built-in) |
| CLI integration tests | `subprocess.run(["python3", "pkgman.py", ...])` via `run()` in `tests/test_cli.py` |
| Real OS tests | Decorated `@integration`, gated by `PKGMAN_TEST_INTEGRATION=1` |

## Running tests

```bash
uv sync              # install dev dependencies (pytest)
uv run pytest        # run all tests
uv run pytest -v     # verbose
uv run pytest tests/test_cli.py  # single file
PKGMAN_TEST_INTEGRATION=1 uv run pytest  # include integration tests
```

## Database

File: `~/.config/.pkgman_database.json` (default) or custom via `-f`/`--file`

```json
{
  "version": 2,
  "sudo": "no",
  "managers": {
    "uv": {"install": ["uv", "tool", "install", "{source}"], "remove": ["uv", "tool", "uninstall", "{source}"]},
    "bash": {"install": "curl -fsSL {source} | bash", "remove": null}
  },
  "packages": [
    {"type": "package", "name": "git"},
    {"type": "bash",  "name": "uv", "source": "https://..."},
    {"type": "uv",      "name": "ruff", "source": "github:astral-sh/ruff"}
  ]
}
```

- Auto-migrates v1 → v2 on first load
- `managers` dict keys are **never overwritten** once they exist (user customizations preserved)
- Duplicate packages ignored by name (case-sensitive)
- Empty or malformed file → treated as empty
- `"sudo"` field controls `@package` commands only; custom managers are unaffected

## Keeping this file up to date

If you make changes that affect the architecture, API surface, or conventions
documented here, update the relevant sections — use judgment or ask the user.

## Release

When asked "make release": bump version in `pyproject.toml` using SemVer, commit all changes, push.

- **patch** (1.0.0 → 1.0.1): bugfixes, refactors, docs, tests — no new user-facing behavior
- **minor** (1.0.0 → 1.1.0): new feature, new subcommand, public API addition
- **major** (1.0.0 → 2.0.0): breaking changes

Commit messages concise and in English.

## License

MIT