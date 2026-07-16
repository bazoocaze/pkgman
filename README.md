# pkgman

Declarative layer over OS package managers. Manages the list of **manually**
installed packages (separating them from system dependencies) and allows
full **replay** on fresh machines.

## Installation

```bash
# with uv (recommended)
uv tool install git+https://github.com/bazoocaze/pkgman

# with pipx
pipx install git+https://github.com/bazoocaze/pkgman
```

## Commands

```
pkgman install git jq                      # install OS packages
pkgman install --url uv <url>              # install script via curl | bash
pkgman install -a                          # replay: reinstall ALL from the database
pkgman remove git                          # uninstall + remove from database
pkgman remove uv                           # only remove from database (script)
pkgman list                                # list registered packages
pkgman list --json                         # list as JSON
pkgman -f ~/my_database.json list          # use an alternative database
```

## How it works

```
pkgman.py          entry point + argparse
commands.py        orchestrator (install/remove/list)
database.py        CRUD for ~/.installed_packages.json
managers.py        detection + execution of apt/yum/brew
scripts.py         execution of curl | bash
tests.py           test suite (20 checks)
```

The order of operations is always:
1. Execute the command on the system
2. If it fails → database is **not** modified
3. If OK → update `~/.installed_packages.json`

The database file is portable between Linux and macOS — the manager is
detected automatically at runtime based on what's available (brew > apt > yum).

## Sudo

Set `"sudo": "yes"` in `~/.installed_packages.json` to prefix manager
commands with `sudo`. Scripts installed via `--url` are not affected.

## Supported managers

| Manager | Detect | Install | Remove |
|---|---|---|---|
| brew | `which brew` | `brew install` | `brew uninstall` |
| apt  | `which apt`  | `apt install -y` | `apt remove -y` |
| yum  | `which yum`  | `yum install -y` | `yum remove -y` |

## Tests

```bash
python3 tests.py
```

## License

MIT