# gost-docx

**Проверяй. Форматируй. Собирай DOCX по ГОСТ.**

<p align="center">
  <img src="docs/assets/readme-hero.jpg" alt="Документ DOCX с разметкой полей и инструментами измерения" width="860">
</p>

<p align="center">
  Локальный Agent Skill для Codex, Claude Code и других совместимых агентов.
</p>

<p align="center">
  <a href="https://github.com/optMD/gost-docx/actions/workflows/validate.yml"><img src="https://github.com/optMD/gost-docx/actions/workflows/validate.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/optMD/gost-docx/releases"><img src="https://img.shields.io/github/v/release/optMD/gost-docx?display_name=tag" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/optMD/gost-docx" alt="License"></a>
</p>

`gost-docx` помогает работать с Word-документами по ГОСТ 7.32-2017,
ГОСТ Р 7.0.100-2018 и пользовательским методичкам.

## Возможности

| Режим | Результат |
| --- | --- |
| Аудит | Markdown-отчёт о найденных нарушениях |
| Форматирование | Копия `*_gost.docx`, исходный файл не изменяется |
| Генерация | Новый DOCX из структурированной JSON-спецификации |

Проверяются поля, формат страницы, шрифт, интервалы, абзацы, колонтитулы,
нумерация, заголовки, подписи, ссылки и основные структурные элементы.

## Установка

Установить skill во все обнаруженные агенты:

```bash
npx skills add https://github.com/optMD/gost-docx \
  --skill gost-docx --agent '*' --global --yes
```

Только в Codex и Claude Code:

```bash
npx skills add https://github.com/optMD/gost-docx \
  --skill gost-docx --agent codex --agent claude-code --global --yes
```

Подробности для разных агентов и проектной установки — в [руководстве по установке](docs/installation.md).

## Быстрый старт

Для запуска инструментов из клона установите зависимости:

```bash
git clone https://github.com/optMD/gost-docx.git
cd gost-docx
python3 -m pip install lxml
npm ci --prefix scripts
```

Проверить окружение:

```bash
python3 scripts/gost_docx.py doctor
```

Проверить существующий документ:

```bash
python3 scripts/gost_docx.py audit report.docx --out audit.md
```

Отформатировать копию:

```bash
python3 scripts/gost_docx.py format report.docx
```

Создать документ из JSON:

```bash
python3 scripts/gost_docx.py build examples/task-report.json report.docx
```

Полный воспроизводимый пример находится в [`examples/`](examples/).

## Принципы

- исходный DOCX не перезаписывается при форматировании;
- содержание, выводы, источники и персональные данные не выдумываются;
- при конфликте ГОСТ и методички skill показывает оба варианта;
- финальная визуальная проверка после рендера остаётся за пользователем.

## Архитектура

```text
DOCX / JSON → gost-docx → аудит / форматирование / генерация → DOCX / отчёт
```

Подробная схема потоков данных описана в [docs/architecture.md](docs/architecture.md).

## Ограничения

- формулы и визуальный результат требуют ручной проверки;
- содержание Word нужно обновить в Microsoft Word после генерации;
- сложные таблицы и нестандартные титульные листы могут потребовать доработки.

## Структура

```text
SKILL.md                  инструкции Agent Skill
references/               правила ГОСТ
scripts/                  аудит, форматирование, генерация и CLI
examples/                 воспроизводимые примеры
tests/                    регрессионные тесты
docs/                     установка и архитектура
```

## Разработка

```bash
python3 -m compileall -q scripts tests
node --check scripts/build_gost.js
python3 -m unittest discover -s tests -v
git diff --check
```

Изменения проходят через сфокусированные ветки и pull request. Подробнее:
[CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md) и [SECURITY.md](SECURITY.md).

## Лицензия

[MIT License](LICENSE) · [English README](README_ENG.md)
