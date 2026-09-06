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
pkgman install @zsh oh-my-zsh https://...           # zsh script from URL
pkgman install @pi name source                       # custom manager
pkgman install -a                                    # replay: reinstall ALL from the database
pkgman remove git                                    # @auto: finds package by name
pkgman remove @pi name                               # explicit manager
pkgman list                                          # list registered packages
pkgman list --json                                   # list as JSON
pkgman configure                                     # detect known managers, add interactively
pkgman configure -y                                  # non-interactive: add all detected
pkgman update                                         # update pkgman (default when no args)
pkgman update git                                    # update package by name
pkgman update git jq                                 # update multiple packages
pkgman update -a                                     # update ALL packages from the database
pkgman update @pi -a                                 # update ALL packages from @pi manager only
pkgman update @pi nome                               # update package under @pi manager
pkgman doctor                                        # run diagnostic checks
pkgman -n install git jq                             # dry run: update DB only, no external commands
pkgman -n remove git                                 # dry run: remove from DB, skip external commands
pkgman -n install -a                                 # dry run: replay DB without executing
pkgman -f ~/my_database.json list                    # use an alternative database
```

## Architecture

```
pkgman.py          → entry point + argparse (root)
src/               → package with all modules
  cli.py           → argparse setup + handler dispatch (COMMAND_DISPATCH)
  command_doctor.py→ diagnostic checks (DoctorReport, run_doctor)
  commands.py      → orchestrator (install/remove/update/list/configure/doctor)
  constants.py     → enums (ManagerType, SudoSetting), DB_VERSION,
                      KNOWN_MANAGERS, RESERVED_MANAGERS
  database.py      → CRUD for ~/.config/.pkgman_database.json (v2 schema)
  managers.py      → Manager (detection + execution of apt/yum/brew) and
                      ManagerRegistry + CustomManager (unified custom managers)
  output.py        → console formatting (Report, format_package_list, _snippet)
  runner.py        → ProcessRunner protocol + SubprocessRunner + DryRunRunner
  sys_check.py     → SysCheck abstraction (which checks)
  ui.py            → interactive UI helpers (prompt_checkbox, print_manager_summary)
tests/             → pytest test suite
run-tests.sh       → shortcut: `uv run pytest tests/`
run-integration-tests.sh  → shortcut: `PKGMAN_TEST_INTEGRATION=1 uv run pytest tests/`
run-app.sh         → shortcut: `uv run python pkgman.py "$@"`
pyproject.toml     → build config + entry point (pkgman = "pkgman:main")
```

**Imports**: all internal modules are accessed via the `src` package, e.g.
`from src.cli import ...`, `from src.constants import ...`, etc.

---

## API cheat sheet – symbols you can import

### src.constants
| Symbol | Description |
|---|---|
| `ManagerType.PACKAGE`, `.AUTO` | `"package"`, `"auto"` |
| `SudoSetting.YES`, `.NO` | `"yes"`, `"no"` |
| `DB_VERSION` | Current schema version (2) |
| `KNOWN_MANAGERS` | `dict` — `name → {exe, install, remove, update}`. Used by `configure`. |
| `RESERVED_MANAGERS` | `frozenset({"package", "auto"})` — forbidden as custom manager names |

### src.commands
```
Commands(db_path: str|Path = None, *, runner: ProcessRunner = None, dry_run: bool = False)

  # properties
  .store: PackageStore      # the loaded DB cache
  .registry: ManagerRegistry  # routes install/remove to correct manager

  # methods
  .install(manager: str, name_or_names: str|list[str], source: str|None = None) -> None
  .install_all() -> None
  .remove(manager: str, name: str) -> None
  .update(names: list[str], *, manager: str|None = None) -> None
  .update_all(*, manager: str|None = None) -> None
  .list(*, json_output: bool = False) -> None
  .configure(*, yes: bool = False) -> None
  .doctor() -> bool   # True if no errors

  # internal
  ._sudo -> bool            # True when store.sudo == "yes"
  ._sudo_for(manager) -> bool  # sudo only applies to @package
```

### src.database
```
Database(path: str|Path = None)
  .read() -> dict           # raw JSON from disk
  .write(data: dict) -> None

PackageStore(db: Database)
  .load() -> list[dict]     # populate cache
  .save() -> None           # persist to disk
  .add(package: dict) -> None     # ignore duplicates by name; auto-saves
  .update(db_name: str, package: dict) -> None  # replace entry by *db_name* (handles rename); auto-saves
  .remove(name: str) -> None      # auto-saves
  .find(name: str) -> dict|None
  .find_by_source(source: str) -> dict|None

  .sudo: str                # "yes" / "no" (setter persists)
  .managers: dict           # mutable ref to managers dict
  .packages: list[dict]     # copy of package list
```

**Important:** `store.managers[k] = v` mutates directly but does NOT auto-save — call `store.save()` after.

### src.managers
```
Manager(name: str, *, runner: ProcessRunner = None)
  .install(package_name: str, *, sudo: bool = False) -> None
  .remove(package_name: str, *, sudo: bool = False) -> None
  .update(package_name: str, *, sudo: bool = False) -> None

CustomManager(name: str, install_cmd: list|str|None, remove_cmd: list|str|None, update_cmd: list|str|None, name_regex: str|None = None)
  .extract_name(arg: str) -> str|None   # first non-empty group, else full match; None if no regex/no match

ManagerRegistry(store, runner: ProcessRunner = SubprocessRunner())
  .get(manager_name: str) -> CustomManager|None
  .install(manager_name, name, source, *, sudo=False) -> None
  .remove(manager_name, name, source, *, sudo=False) -> None
  .update(manager_name, name, source, *, sudo=False) -> None
  .resolve_auto(name_or_source: str) -> tuple[str, dict]|None

detect_os_manager() -> Manager|None   # brew > apt > yum
_substitute(cmd, name, source)        # replaces {name}/{source} placeholders
```

### src.runner
```
ProcessRunner (Protocol)
  .run(cmd: list[str]|str, *, shell: bool = False) -> None

SubprocessRunner()           # real impl; raises CalledProcessError on failure
DryRunRunner()               # no-op runner for --no-run; prints commands instead of executing
```

### src.output
```
Report()
  .add_ok(ptype: str, name: str, detail: str = "") -> None
  .add_fail(ptype: str, name: str, detail: str = "", snippet: str = "") -> None
  .print() -> None

format_package_list(packages: list[dict], *, json_output: bool = False) -> str
```

### src.ui
```
prompt_checkbox(labels: list[str], *, header: str|None = None, prompt: str|None = None) -> list[int]
print_manager_summary(managers: dict) -> None
```

- `prompt_checkbox` — interactive numbered selection prompt for configure
- `print_manager_summary` — prints registered custom managers with install/remove/update/name_regex icons

### src.command_doctor
```
DoctorReport()
  .ok(detail: str) -> None
  .warn(detail: str) -> None
  .error(detail: str) -> None
  .has_errors -> bool
  .print() -> None

run_doctor(store: PackageStore, sys_check: SysCheck) -> DoctorReport

Checks included:
- Database file exists, valid JSON, correct schema version
- OS package manager detection (apt/yum/brew)
- Registered manager executables on PATH
- Valid `name_regex` per registered manager (warns on un-compilable regex)
- Duplicate package names (global)
- **Duplicate name/source identifiers per manager** — warns when
  the same value appears as `name` or `source` in more than one
  package of the same manager type
- Package type-to-manager alignment
```

### src.cli
```
build_parser() -> ArgumentParser
COMMAND_DISPATCH: dict[str, callable]   # {"install": ..., "remove": ..., "list": ..., "configure": ..., "update": ..., "doctor": ...}
parse_install_args(args: list[str]) -> (manager, names|name, source|None)
parse_remove_args(args: list[str]) -> (manager, name)
```

## Install conflict rules

When installing a package, `_install_single` checks for conflicts
against existing packages of the same manager type:

| # | Scenario | Action |
|---|---|---|
| 1 | Same `type`+`source` (both explicit), different `name` | **Update** — runs install, renames in DB to new name |
| 3/5 | Same `type`+`name`, source unchanged (missing or same) | **Reinstall** — runs install, DB untouched |
| 2/4 | Same `type`+`name`, new explicit source **different** from DB | **Update** — runs install with new source, updates DB |
| 6 | `existing_name == new_source` (no stored source), `name != existing_name` | **Update** — runs install, renames and adds source |
| — | No conflict | **Add** — runs install, registers in DB |

For reinstalls (cases 3 & 5), the stored `source` value (if any) is
used for `{source}` template substitution, not the implicit name.

---

## Adding a new subcommand

1. **`src/cli.py`**: add subparser in `build_parser()`, create `_handle_xxx(cmds, args)`, register in `COMMAND_DISPATCH`
2. **`src/commands.py`**: add method on `Commands`
3. If adding a new `.py` file: place it under `src/` — modules inside the `src` package are auto-discovered via `packages = ["src"]`

## Adding a new known manager (for `configure`)

Add entry to `KNOWN_MANAGERS` in `constants.py`:
```python
"name": {
    "exe": "executable",                              # checked via shutil.which()
    "install": ["cmd", "install", "{source}"],         # install template (list or string)
    "remove": ["cmd", "remove", "{source}"],           # remove template (or None)
    "update": ["cmd", "update", "{source}"],           # update template (or None)
    "name_regex": r"npm:(?:@[^/]+/)?(.+)",             # optional: extract name from single-arg source
},
```
When the manager is already registered but has empty fields (`install`/`remove`/
`update`/`name_regex` = missing, `null`, or `""`), `configure` offers an **update**
option that fills only those fields with the known values, preserving any
non-empty user customizations.
For shell-pipe managers (e.g. `bash`, `zsh`), use a string install command:
```python
"name": {
    "exe": "executable",
    "install": "curl -fsSL {source} | executable",    # string → shell=True
    "remove": None,                                     # None → database-only removal
    "update": None,                                     # None → no update command
},
```

## Testing conventions
| Convention | Detail |
|---|---|
| Fixture `db_path` | Temp JSON file, auto-cleaned (`tests/conftest.py`) |
| Fixture `empty_db` | Returns a ready-to-use `PackageStore` |
| Mock install/remove/update | `patch.object(cmds.registry, "install")` / `"remove"` / `"update"` |
| Mock PATH detection | `patch("src.commands.shutil.which", return_value=...)` |
| Mock user input | `patch("builtins.input", return_value=...)` or `side_effect=[...]` |
| Capture output | `capsys.readouterr()` (pytest built-in) |
| CLI integration tests | `subprocess.run(["python3", "pkgman.py", ...])` via `run()` in `tests/test_cli.py` |
| Real OS tests | Decorated `@integration`, gated by `PKGMAN_TEST_INTEGRATION=1` |

## Running tests

```bash
uv sync                          # install dev dependencies (pytest)
./run-tests.sh                   # run all tests (shortcut)
./run-integration-tests.sh       # include integration tests
uv run pytest -v                 # verbose
uv run pytest tests/test_cli.py  # single file
uv run pytest -k "test_name"     # single test
```

## Database

File: `~/.config/.pkgman_database.json` (default) or custom via `-f`/`--file`

```json
{
  "version": 2,
  "sudo": "no",
  "managers": {
    "uv": {"install": ["uv", "tool", "install", "{source}"], "remove": ["uv", "tool", "uninstall", "{name}"], "update": ["uv", "tool", "upgrade", "{name}"], "name_regex": "(?:git\\+https?://[^/]+/[^/]+/|github:[^/]+/)?([^@=<>/]+)"},
    "bash": {"install": "curl -fsSL {source} | bash", "remove": null, "update": null},
    "zsh": {"install": "curl -fsSL {source} | zsh", "remove": null, "update": null},
    "pi": {"install": ["pi", "install", "{source}"], "remove": ["pi", "remove", "{source}"], "update": ["pi", "update", "{source}"], "name_regex": "npm:(?:@[^/]+/)?(.+)"}
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

## Name extraction regex (`name_regex`)

Custom managers can declare an optional `name_regex`. When
`pkgman install @<manager> <source>` is called with a **single argument**
and the manager has a `name_regex`, the regex is matched against the
argument to extract the package `name`. On match, the extracted value is
used as `name` and the original argument is stored as `source`:

```
pkgman install @pi npm:pi-blackhole          # name_regex "npm:(?:@[^/]+/)?(.+)" → name=pi-blackhole, source=npm:pi-blackhole
pkgman install @pi npm:@ff-labs/pi-fff       # → name=pi-fff (scoped scope stripped), source=npm:@ff-labs/pi-fff
pkgman install @uv cptr@latest               # name_regex "(?:git\+https?://[^/]+/[^/]+/|github:[^/]+/)?([^@=<>/]+)" → name=cptr, source=cptr@latest
pkgman install @uv git+https://github.com/bazoocaze/pkgman   # → name=pkgman
```

- Uses `re.match`; the **first non-empty capture group** is returned, else
  the full match. No match / no regex → standard behavior (argument is the name).
- Only applies to single-argument custom installs (implicit source).
  Explicit `install @mgr NAME SOURCE` and remove/update are unaffected.
- Use regex alternation (`npm:(.+)|gh:(.+)`) to support multiple source formats.
- `pkgman doctor` warns when a registered manager's `name_regex` is invalid.
- Built-in `uv` manager ships with a `name_regex` that handles git URLs
  (`git+https://host/owner/repo`), `github:owner/repo` shorthand, `name@version`
  and `name>=spec` specifiers; plain names pass through.

## Keeping this file up to date

If you make changes that affect the architecture, API surface, or conventions
documented here, update the relevant sections — use judgment or ask the user.

## Release

When asked "make release": bump version in `pyproject.toml` using SemVer, update CHANGELOG.md, commit all changes, push.

- **patch** (1.0.0 → 1.0.1): bugfixes, refactors, docs, tests, small new user-facing behavior.
- **minor** (1.0.0 → 1.1.0): new feature, new subcommand, public API addition, small breaking changes.
- **major** (1.0.0 → 2.0.0): new major versions. ask user before incrementing the major version.

Commit messages concise and in English.

## License

MIT
