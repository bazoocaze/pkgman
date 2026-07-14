# pkgman

Layer declarativo sobre gerenciadores de pacotes do SO. Gerencia a lista de
pacotes instalados **manualmente** (separando-os de dependências do sistema)
e permite **replay** completo em estações novas.

## Comandos

```
pkgman install git jq                      # instala pacotes do SO
pkgman install --url uv <url>              # instala script via curl | bash
pkgman install -a                          # replay: reinstala TUDO do banco
pkgman remove git                          # desinstala + remove do banco
pkgman remove uv                           # só remove do banco (script)
pkgman list                                # lista pacotes registrados
pkgman -f ~/meu_banco.json list            # usa banco alternativo
```

## Arquitetura

```
pkgman.py          → entry point + argparse
commands.py        → orquestrador (install/remove/list)
database.py        → CRUD do ~/.installed_packages.json
managers.py        → detecção + execução de apt/yum/brew
scripts.py         → execução de curl | bash
```

### database.py

Lê/escreve `~/.installed_packages.json` no formato:

```json
{
  "version": 1,
  "sudo": "no",
  "packages": [
    {"type": "package", "name": "git"},
    {"type": "script",  "name": "uv", "url": "https://..."}
  ]
}
```

Métodos (instância): `load()`, `save()`, `add()`, `remove()`, `find()`.

O caminho do arquivo pode ser personalizado com o parâmetro `path` no
construtor ou via flag `-f`/`--file` na CLI.

### managers.py

- `Manager.detect()` → detecta o gerenciador disponível (brew > apt > yum)
- `manager.install(name, sudo=False)` → executa `apt install -y name` (ou equivalente)
- `manager.remove(name, sudo=False)` → executa `apt remove -y name` (ou equivalente)
- Quando `sudo=True`, prefixa o comando com `sudo`
  (ex: `["sudo", "apt", "install", "-y", "git"]`)

### scripts.py

- `ScriptRunner.run(url)` → executa `curl -fsSL <url> | bash`

### commands.py

Orquestra as operações. A ordem sempre é:
1. Executa o comando no sistema
2. Se falhar → **não altera o banco** (exceção propaga)
3. Se OK → atualiza `~/.installed_packages.json` (ou o especificado com `-f`)

### pkgman.py

CLI com `argparse`. Subcomandos: `install`, `remove`, `list`.

## Banco de dados

Arquivo: `~/.installed_packages.json` (padrão) ou personalizado via `-f`/`--file`

- Versionado para permitir evolução futura do schema
- Arquivo vazio ou malformado → tratado como lista vazia
- Duplicatas ignoradas por nome (case-sensitive)

## Sudo

O campo `"sudo"` no JSON controla se os comandos do gerenciador de pacotes
são executados com `sudo`. Valor padrão é `"no"`; pode ser alterado
manualmente para `"yes"`. Toda gravação no arquivo persiste o valor
explicitamente.

```json
{
  "version": 1,
  "sudo": "yes",
  "packages": [...]
}
```

Quando `"sudo": "yes"`, os comandos executados pelo `Manager` são prefixados
com `sudo`, tanto em `install` quanto em `remove`. Scripts instalados via
`--url` não são afetados (executam como `curl | bash` sem sudo).

## Gerenciadores suportados

| Gerenciador | Detectado por | Install | Remove |
|---|---|---|---|
| brew | `which brew` | `brew install` | `brew uninstall` |
| apt  | `which apt`  | `apt install -y` | `apt remove -y` |
| yum  | `which yum`  | `yum install -y` | `yum remove -y` |

Detecção automática na inicialização. O gerenciador usado independe de como o
pacote foi originalmente instalado — usa-se sempre o disponível no sistema
atual (torna o banco portátil entre Linux e macOS).

## Licença

MIT