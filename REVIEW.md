# Code Review — pkgman v2.0.1 → v2.1.0

## Resumo

76 testes totais: 71 unit tests + 5 de integração (skipados por padrão, rodam com `PKGMAN_TEST_INTEGRATION=1`).
Todas as 25 recomendações implementadas + `ProcessRunner` injetável para resolver o problema do sudo.

## Bugs corrigidos

| # | Arquivo | Problema | Solução |
|---|---------|----------|---------|
| 1 | `constants.py` / `pyproject.toml` | `StrEnum` é Python 3.11+, mas `pyproject.toml` dizia `>=3.10` | Bump `requires-python = ">=3.11"` |
| 13 | `output.py:_Colors` | `sys.stdout.isatty()` avaliado no import — quebra com pipe/redirecionamento | Métodos estáticos que checam `isatty()` em cada chamada |
| 26 | `tests/test_cli.py` | Testes de CLI executavam comandos reais (`apt install git`) pedindo sudo | Marcados `@integration`, skipados por padrão. `ProcessRunner` injetável adicionado. |

## Melhorias de design implementadas

| # | Arquivo | Mudança |
|---|---------|---------|
| 2 | `commands.py` | Construtor aceita `runner: ProcessRunner` opcional; validação dupla removida |
| 3 | `commands.py` | `install()` → `_install_single()` helper elimina dispatch por `isinstance` |
| 4 | `commands.py` | `except Exception` re-levanta `KeyboardInterrupt` |
| 5 | `pkgman.py` / `cli.py` | `main()` ficou ~20 linhas; handlers + parser extraídos para `cli.py` |
| 6 | `cli.py` | Parsing usa `ValueError` em vez de `sys.exit`; erros capturados nos handlers |
| 7 | `database.py` | `# type: ignore` eliminados — flag `_loaded: bool` + defaults no lugar de `None` |
| 8 | `database.py` | `_migrate()` retorna bool; `_db.write()` só no `_ensure_loaded` |
| 9 | `managers.py` | `detect_os_manager()` como função module-level (antes `Manager.detect()`) |
| 10 | `managers.py` | `ManagerStore` Protocol substitui `store: object` |
| 11 | `managers.py` / `runner.py` | `_run_command` substituído por `ProcessRunner` (Protocol) + `SubprocessRunner` — injetável, mockável nos testes |
| 12 | `commands.py` | `_install_packages` + `_install_custom` → `_install_single()` |
| 14 | `pkgman.py` | `from __future__ import annotations` removido |
| 15 | `constants.py` | `auto` removido do import de enum |
| 16 | `constants.py` | `DEFAULT_MANAGERS` tipado como `dict[str, dict[str, list[str] \| str \| None]]` |
| 17 | `database.py` | `find()` / `find_by_source()` mantidos separados (simplicidade) |
| 18 | `commands.py` | `validate_managers()` removido do Commands (já roda no PackageStore) |
| 19 | `managers.py` | `RuntimeError` → `ValueError` em `Manager._build_cmd` |
| 20 | `managers.py` | `CustomManager.from_dict()` classmethod |
| 21 | `runner.py` | `shell=True` documentado no docstring de `SubprocessRunner.run` |
| 22 | `output.py` | `ReportEntry` agora é `NamedTuple` (antes dataclass) |
| 23 | `output.py` | `_snippet` movido para função module-level |
| 24 | `commands.py` / `output.py` | `list()` delega para `format_package_list()` em output.py |
| 25 | `cli.py` | CLI não importa mais `ManagerType` — usa strings literais |

## Novos arquivos

- `cli.py` — argument parsing + handlers + dispatch
- `runner.py` — `ProcessRunner` (Protocol) + `SubprocessRunner` (implementação real)
- `REVIEW.md` — este documento

## Testes

- **71 unit tests** — sempre rodam, sem sudo, sem subprocess real
- **5 integration tests** — skipados por padrão. Rodar com: `PKGMAN_TEST_INTEGRATION=1 uv run pytest tests/`
- `test_managers.py` atualizado: usa `MagicMock(spec=ProcessRunner)` em vez de `@patch("_run_command")`
- `test_cli.py`: testes de `install git`/`remove git`/etc marcados `@integration`