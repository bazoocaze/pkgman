# pkgman

[![CI](https://github.com/bazoocaze/pkgman/actions/workflows/ci.yml/badge.svg)](https://github.com/bazoocaze/pkgman/actions/workflows/ci.yml)

Declarative layer over OS package managers. Manages the list of **manually**
installed packages (separating them from system dependencies) and allows
full **replay** on fresh machines.

## Installation

```bash
# with uv (recommended)
uv tool install git+https://github.com/bazoocaze/pkgman

# with pipx
pipx install git+https://github.com/bazoocaze/pkgman

# local development
python3 pkgman.py ...             # run directly, no install needed
uv tool install --reinstall .     # install from local checkout
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
pkgman -V, --version                                 # show version and exit
pkgman -f ~/my_database.json list                    # use an alternative database
```

## How it works

```
pkgman.py          entry point + argparse
commands.py        orchestrator (install/remove/list)
database.py        CRUD for ~/.config/.pkgman_database.json
managers.py        Manager (detection + execution of apt/yum/brew) and
                   ManagerRegistry + CustomManager (unified custom managers)
tests/             pytest test suite
pyproject.toml     build config + entry point
```

The order of operations is always:
1. Execute the command on the system
2. If it fails → database is **not** modified
3. If OK → update `~/.config/.pkgman_database.json`

The database file is portable between Linux and macOS — the OS manager is
detected automatically at runtime based on what's available (brew > apt > yum).
Custom managers (defined in JSON) work identically on any platform.

## Sudo

Set `"sudo": "yes"` in `~/.config/.pkgman_database.json` to prefix `@package`
commands with `sudo`. Custom managers are **not** affected by the sudo setting
(they run as logged in the JSON command definition).

## Supported managers

| Manager | Detect | Install | Remove |
|---|---|---|---|---|
| brew | `which brew` | `brew install` | `brew uninstall` |
| apt  | `which apt`  | `apt install -y` | `apt remove -y` |
| yum  | `which yum`  | `yum install -y` | `yum remove -y` |
| bash | `which bash` | `curl ... \| bash` | database-only |
| zsh  | `which zsh`  | `curl ... \| zsh`  | database-only |

## Database

The database is stored at `~/.config/.pkgman_database.json` (default) or a
custom path specified with `-f`/`--file`.

### Schema (v2)

```json
{
  "version": 2,
  "sudo": "no",
  "managers": {
    "uv": {
      "install": ["uv", "tool", "install", "{source}"],
      "remove": ["uv", "tool", "uninstall", "{source}"]
    },
    "bash": {
      "install": "curl -fsSL {source} | bash",
      "remove": null
    },
    "zsh": {
      "install": "curl -fsSL {source} | zsh",
      "remove": null
    },
    "pi": {
      "install": ["pi", "install", "{source}"],
      "remove": ["pi", "remote", "{name}"]
    }
  },
  "packages": [
    {"type": "package", "name": "git"},
    {"type": "pi", "name": "pi-subagents", "source": "npm:@tintinweb/pi-subagents"},
    {"type": "bash", "name": "sdkman", "source": "https://get.sdkman.io"},
    {"type": "uv", "name": "ruff", "source": "github:astral-sh/ruff"}
  ]
}
```

### Custom managers

Each entry in `managers` defines:

- `install`: a shell string (with `shell=True`) or a list of arguments for `subprocess`.
  Placeholders `{name}` and `{source}` are substituted at runtime.
- `remove`: a string, a list, or `null`. If `null`, removal is database-only.

Built-in default managers are injected automatically on first
load or v1 migration. Once a manager key exists in the JSON, it is **never
overwritten** by pkgman — the user can freely edit or extend them. Adding a new
custom manager is as simple as adding a new key to the `managers` dictionary.

### Behavior details

- Empty or malformed file → treated as an empty list with default managers.
- Duplicates are ignored by name (case-sensitive).
- For custom managers, if `source` matches `name`, the `source` field may be
  omitted from the JSON (it is inferred as `source = name`).
- Reserved names (`package`, `auto`) cannot be used as custom manager keys.

## Tests

```bash
uv run pytest tests/
# or
./test.sh
```

Covers database CRUD, manager command building, Commands orchestration, CLI
argument parsing, and custom manager execution (90+ checks).

## License

MIT