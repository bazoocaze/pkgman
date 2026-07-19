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
pkgman install @script sdkman https://get.sdkman.io  # script from URL
pkgman install @pi name source                       # custom manager
pkgman install -a                                    # replay: reinstall ALL from the database
pkgman remove git                                    # @auto: finds package by name
pkgman remove @pi name                               # explicit manager
pkgman list                                          # list registered packages
pkgman list --json                                   # list as JSON
pkgman -f ~/my_database.json list                    # use an alternative database
```

## Architecture

```
pkgman.py          → entry point + argparse
commands.py        → orchestrator (install/remove/list)
database.py        → CRUD for ~/.config/.pkgman_database.json (v2 schema with managers)
managers.py        → Manager (detection + execution of apt/yum/brew) and
                     ManagerRegistry + CustomManager (unified custom managers)
tests/             → pytest test suite (69+ checks)
pyproject.toml     → build config + entry point (pkgman = "pkgman:main")
README.md          → install & usage docs
```

### database.py

Reads/writes `~/.config/.pkgman_database.json` in the following format (v2):

```json
{
  "version": 2,
  "sudo": "no",
  "managers": {
    "uv": {
      "install": ["uv", "tool", "install", "{source}"],
      "remove": ["uv", "tool", "uninstall", "{name}"]
    },
    "script": {
      "install": "curl -fsSL {source} | bash",
      "remove": null
    }
  },
  "packages": [
    {"type": "package", "name": "git"},
    {"type": "script",  "name": "uv", "source": "https://..."},
    {"type": "uv",      "name": "ruff", "source": "github:astral-sh/ruff"}
  ]
}
```

Automatically migrates v1 → v2 on first load. The `managers` dict is
**never overwritten** once a key exists.

Instance methods: `load()`, `save()`, `add()`, `remove()`, `find()`.

The file path can be customized via the `path` parameter in the constructor
or via the `-f`/`--file` CLI flag.

### managers.py

- `Manager.detect()` → detects the available manager (brew > apt > yum)
- `manager.install(name, sudo=False)` → runs `apt install -y name` (or equivalent)
- `manager.remove(name, sudo=False)` → runs `apt remove -y name` (or equivalent)
- When `sudo=True`, prefixes the command with `sudo`
  (e.g. `["sudo", "apt", "install", "-y", "git"])`
- `ManagerRegistry(db)` → unifies built-in `@package` with custom managers from JSON.
  Methods: `get()`, `install()`, `remove()`, `resolve_auto()`.
- `CustomManager(name, install_cmd, remove_cmd)` → dataclass representing a
  custom manager entry from the JSON database. Placeholders `{name}`, `{source}`
  are substituted at runtime.

_(Removed in v2.0.0 — `uv` and `script` are now custom managers defined in the JSON database._
_See `managers` in the database schema.)_

### commands.py

Orchestrates the operations. The order is always:
1. Execute the command on the system
2. If it fails → **does not change the database** (exception propagates)
3. If OK → updates `~/.config/.pkgman_database.json` (or the one specified with `-f`)

### pkgman.py

CLI with `argparse`. Subcommands: `install`, `remove`, `list`.

- `list --json` → outputs the package list as JSON instead of the default text format
- `-V`/`--version` → shows the installed version via `importlib.metadata`

### pyproject.toml

Build config with setuptools. Defines the entry point (`pkgman = "pkgman:main"`)
so tools like `uv tool install` and `pipx` create a `pkgman` command in PATH.

**Tip:** When adding a new `.py` file at the project root, include its module name in
`[tool.setuptools] py-modules`, otherwise `uv tool install` / `pipx` will not ship it.

## Database

File: `~/.config/.pkgman_database.json` (default) or custom via `-f`/`--file`

- Versioned to allow future schema evolution
- Empty or malformed file → treated as an empty list
- Duplicates ignored by name (case-sensitive)

## Sudo

The `"sudo"` field in the JSON controls whether `@package` commands are
run with `sudo`. Default value is `"no"`; can be manually changed to `"yes"`.
Every write to the file persists the value explicitly.

```json
{
  "version": 2,
  "sudo": "yes",
  "managers": {...},
  "packages": [...]
}
```

When `"sudo": "yes"`, commands executed by `Manager` (the built-in OS manager)
are prefixed with `sudo` on both `install` and `remove`. Custom managers are
**not** affected by the sudo setting.

## Supported managers

| Manager | Detected by | Install | Remove |
|---|---|---|---|
| brew | `which brew` | `brew install` | `brew uninstall` |
| apt  | `which apt`  | `apt install -y` | `apt remove -y` |
| yum  | `which yum`  | `yum install -y` | `yum remove -y` |

Automatic detection at startup. The manager used is independent of how the
package was originally installed — it always uses whatever is available on
the current system (making the database portable between Linux and macOS).

## Tests

Run the full test suite with:

```
uv run pytest tests/
# or
./test.sh
```

Covers database CRUD, manager command building, Commands orchestration, CLI
argument parsing, and custom manager execution (69+ checks).

## Release

When user asks "make release", you should bump version, savel all files, commit and push. Use SemVer.

## License

MIT
