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
pkgman install git jq                      # install OS packages
pkgman install --url uv <url>              # install script via curl | bash
pkgman install --uv ruff github:astral-sh/ruff  # install Python tool via uv
pkgman install -a                          # replay: reinstall ALL from the database
pkgman remove git                          # uninstall + remove from database
pkgman remove uv                           # only remove from database (script)
pkgman remove ruff                         # uninstall uv tool + remove from database
pkgman list                                # list registered packages
pkgman list --json                         # list as JSON
pkgman -f ~/my_database.json list          # use an alternative database
```

## Architecture

```
pkgman.py          → entry point + argparse
commands.py        → orchestrator (install/remove/list)
database.py        → CRUD for ~/.installed_packages.json
managers.py        → detection + execution of apt/yum/brew
scripts.py         → execution of curl | bash
uv_tools.py        → execution of uv tool install/uninstall
tests.py           → reusable test suite (25+ checks)
pyproject.toml     → build config + entry point (pkgman = "pkgman:main")
README.md          → install & usage docs
```

### database.py

Reads/writes `~/.installed_packages.json` in the following format:

```json
{
  "version": 1,
  "sudo": "no",
  "packages": [
    {"type": "package", "name": "git"},
    {"type": "script",  "name": "uv", "url": "https://..."},
    {"type": "uv",      "name": "ruff", "source": "github:astral-sh/ruff"}
  ]
}
```

Instance methods: `load()`, `save()`, `add()`, `remove()`, `find()`.

The file path can be customized via the `path` parameter in the constructor
or via the `-f`/`--file` CLI flag.

### managers.py

- `Manager.detect()` → detects the available manager (brew > apt > yum)
- `manager.install(name, sudo=False)` → runs `apt install -y name` (or equivalent)
- `manager.remove(name, sudo=False)` → runs `apt remove -y name` (or equivalent)
- When `sudo=True`, prefixes the command with `sudo`
  (e.g. `["sudo", "apt", "install", "-y", "git"]`)

### scripts.py

- `ScriptRunner.run(url)` → runs `curl -fsSL <url> | bash`

### uv_tools.py

- `UvTool.install(source)` → runs `uv tool install <source>`
- `UvTool.remove(name)` → runs `uv tool uninstall <name>`

### commands.py

Orchestrates the operations. The order is always:
1. Execute the command on the system
2. If it fails → **does not change the database** (exception propagates)
3. If OK → updates `~/.installed_packages.json` (or the one specified with `-f`)

### pkgman.py

CLI with `argparse`. Subcommands: `install`, `remove`, `list`.

- `list --json` → outputs the package list as JSON instead of the default text format

### pyproject.toml

Build config with setuptools. Defines the entry point (`pkgman = "pkgman:main"`)
so tools like `uv tool install` and `pipx` create a `pkgman` command in PATH.

## Database

File: `~/.installed_packages.json` (default) or custom via `-f`/`--file`

- Versioned to allow future schema evolution
- Empty or malformed file → treated as an empty list
- Duplicates ignored by name (case-sensitive)

## Sudo

The `"sudo"` field in the JSON controls whether package manager commands are
run with `sudo`. Default value is `"no"`; can be manually changed to `"yes"`.
Every write to the file persists the value explicitly.

```json
{
  "version": 1,
  "sudo": "yes",
  "packages": [...]
}
```

When `"sudo": "yes"`, commands executed by `Manager` are prefixed with `sudo`
on both `install` and `remove`. Scripts installed via `--url` are not affected
(they run as `curl | bash` without sudo).

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
python3 tests.py
```

Covers database CRUD, manager command building, Commands orchestration, and
CLI argument parsing (20 checks).

## License

MIT