# Установка gost-docx для AI-агентов

`gost-docx` использует открытый формат Agent Skills: каталог с `SKILL.md`, YAML frontmatter и необязательными `scripts/` и `references/`. Один и тот же репозиторий можно установить в Codex, Claude Code, Cursor и другие агенты через `npx skills`.

## Быстрая установка

Установить skill во все обнаруженные агенты глобально:

```bash
npx skills add https://github.com/optMD/gost-docx \
  --skill gost-docx \
  --agent '*' \
  --global \
  --yes
```

Установить только в Codex и Claude Code:

```bash
npx skills add https://github.com/optMD/gost-docx \
  --skill gost-docx \
  --agent codex \
  --agent claude-code \
  --global \
  --yes
```

Установка только для текущего проекта:

```bash
npx skills add https://github.com/optMD/gost-docx \
  --skill gost-docx \
  --agent '*' \
  --yes
```

## Проверка установки

Показать установленные skills:

```bash
npx skills list
```

Проверить, что репозиторий обнаруживается как skill:

```bash
npx skills add https://github.com/optMD/gost-docx --list
```

Обновить установленный skill:

```bash
npx skills update
```

## Где окажется skill

Путь зависит от агента и выбранного режима установки:

| Агент | Глобальный путь |
| --- | --- |
| Codex | `~/.agents/skills/gost-docx/` |
| Claude Code | `~/.claude/skills/gost-docx/` |
| Cursor | каталог skills, выбранный `npx skills` для Cursor |
| Другие агенты | каталог, соответствующий параметру `--agent` |

Для проектной установки CLI создаёт агентский каталог внутри текущего проекта. Это удобно, если skill должен быть частью reproducible development environment.

## Runtime-инструменты

`npx skills add` устанавливает инструкции и файлы скилла. Для запуска скриптов
нужны Python, Node.js и зависимости. Клонировать репозиторий повторно не требуется:
зависимости можно установить непосредственно в каталог установленного скилла.

| Режим | Что требуется |
| --- | --- |
| `--help`, `--version` | Python |
| `audit`, `format`, `format --dry-run` | Python и `lxml` |
| `validate` | Python и Node.js |
| `build` | Python, Node.js и npm-пакет `docx` |

Для разработки CI настроен на Python 3.12 и Node.js 20 на Linux, macOS и Windows.
Наличие задания в CI само по себе не означает успешный прогон: результат смотрите
в проверках конкретного PR.

В клоне проекта на macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install lxml
npm ci --prefix scripts
.venv/bin/python scripts/gost_docx.py doctor --json
```

В Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install lxml
npm ci --prefix scripts
.\.venv\Scripts\python.exe scripts/gost_docx.py doctor --json
```

Для проектной установки Codex из корня проекта на macOS/Linux:

```bash
SKILL_DIR="$PWD/.agents/skills/gost-docx"
python3 -m venv .venv
.venv/bin/python -m pip install lxml
npm ci --prefix "$SKILL_DIR/scripts"
.venv/bin/python "$SKILL_DIR/scripts/gost_docx.py" doctor --json
```

Для другого агента или глобальной установки замените `SKILL_DIR` фактическим
путём, который показала установка. Путь может содержать пробелы; сохраняйте кавычки.
В PowerShell путь к скрипту аналогично передаётся в кавычках.

Единая точка входа для всех режимов (пример для клона на macOS/Linux):

```bash
.venv/bin/python scripts/gost_docx.py validate examples/task-report.json --strict
.venv/bin/python scripts/gost_docx.py build examples/task-report.json output.docx --strict
.venv/bin/python scripts/gost_docx.py format output.docx --dry-run
.venv/bin/python scripts/gost_docx.py format output.docx --out formatted.docx
.venv/bin/python scripts/gost_docx.py audit formatted.docx --json --out audit.json
```

`validate` проверяет структуру задания без создания DOCX. Для этой команды
достаточно Python и Node.js. Код `0` означает, что проверка прошла, код `1`
сопровождается сообщением об ошибке.

`doctor` проверяет Python, `lxml`, Node.js и загрузку пакета `docx`.
Если зависимости не хватает, команда подскажет, как её установить.
Код возврата `0` означает, что окружение готово ко всем режимам.

Команды разрешают пути к скриптам и Node-модулям относительно каталога
скилла, поэтому не зависят от `~/.claude`, `~/.agents` или рабочего каталога.
Запускайте скрипты тем Python, в окружение которого установлен `lxml`.
При запуске из другой папки передавайте абсолютный путь к интерпретатору и скрипту;
пути входного задания и результата отсчитываются от текущей рабочей папки.
После обновления скилла повторите `npm ci --prefix <каталог-скилла>/scripts` и `doctor`.
Подробности параметров — в [описании CLI](cli-reports.md).

## Типичные проблемы

| Сообщение или симптом | Что проверить |
| --- | --- |
| `MISSING lxml` | Установить `lxml` через `путь-к-python -m pip install lxml` для того же интерпретатора |
| `MISSING node` | Установить Node.js, перезапустить терминал или агента и проверить `node --version` |
| `MISSING docx` | Выполнить `npm ci --prefix` для папки `scripts` именно установленной копии |
| `ERROR docx` | Проверка Node.js не запустилась или превысила 10 секунд; прочитать `hint` |
| Ошибка доступа к папке | Выбрать доступный для записи каталог установки или результата |
| `unknown field` в строгом режиме | Исправить имя поля по сообщению; ключевые слова находятся в `abstract.keywords` |

Установка зависимостей обычно требует сети. После установки аудит, форматирование,
проверка JSON и генерация работают локально. `doctor` не загружает недостающие пакеты.

## Как проверяется переносимость

Тесты копируют `SKILL.md`, `scripts/` и `references/` во временный каталог без `.git`
и `node_modules`, устанавливают Node-зависимости через `npm ci` и запускают команды
из другой папки с пробелами и кириллицей в пути. Переменные `NODE_PATH` и `PYTHONPATH`
исключаются из окружения. Python и `lxml` берутся из тестового окружения.

Сквозной тест проходит `validate → build → format --dry-run → format → audit`,
проверяет сохранность исходника и текста, валидность ZIP и JSON-отчёт аудита.
Он проверяет установленную копию runtime, но не поведение моделей агентов.
Сам CLI установки проверяется отдельно; его параметры описаны в
[документации Skills CLI](https://github.com/vercel-labs/skills/blob/main/docs/commands.md).

## Claude.ai и Claude Code

Claude Code использует CLI-установку, описанную выше. Claude.ai использует отдельный интерфейс загрузки custom skills: при ручной загрузке архив должен содержать каталог skill, внутри которого находится `SKILL.md`.

## Структура skill

```text
gost-docx/
├── SKILL.md
├── scripts/
│   └── gost_docx.py       # portable CLI
├── references/
└── README.md
```

`SKILL.md` содержит обязательные поля `name` и `description` в YAML frontmatter. При установке CLI обнаруживает skill по этому файлу и не требует отдельного manifest-файла.

## Обновление из исходников

Для разработки самого skill используйте обычный clone:

```bash
git clone https://github.com/optMD/gost-docx.git
cd gost-docx
npm ci --prefix scripts
```

После изменений запускайте проверки из [README.md](../README.md) и создавайте pull request.
