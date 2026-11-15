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

`npx skills add` устанавливает инструкции и файлы скилла, но не устанавливает
системные Python- и Node-зависимости. Для аудита и форматирования из клона
репозитория выполните:

```bash
python3 -m pip install lxml
npm ci --prefix scripts
```

Единая точка входа для всех режимов:

```bash
python3 scripts/gost_docx.py audit input.docx --out audit.md
python3 scripts/gost_docx.py format input.docx
python3 scripts/gost_docx.py build examples/task-report.json output.docx
python3 scripts/gost_docx.py doctor
```

`doctor` показывает состояние Python, `lxml`, Node.js и локального пакета
`docx`. Код возврата `0` означает, что окружение готово ко всем режимам.

Команды разрешают пути к скриптам и Node-модулям относительно каталога
скилла, поэтому не зависят от `~/.claude`, `~/.agents` или рабочего каталога.
После глобальной установки скопируйте репозиторий в доступный для runtime
каталог либо запускайте команды из clone-проекта, где можно установить
зависимости. Для агентов, которые используют только инструкции, установка
через `npx skills` уже достаточна.

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
