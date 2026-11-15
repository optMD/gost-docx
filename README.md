# gost-docx

`gost-docx` — skill для создания, проверки и форматирования документов `.docx` по требованиям ГОСТ и выбранной методички.

Проект рассчитан на разные виды работ:

- отчёты о НИР;
- курсовые работы;
- выпускные квалификационные работы;
- лабораторные и практические работы;
- техническая документация.

## Возможности

- аудит существующего документа без изменения исходного файла;
- форматирование копии документа;
- создание нового документа из пользовательских данных;
- страница-заглушка `ТИТУЛЬНЫЙ ЛИСТ`, если титульный лист не предоставлен;
- нумерация страниц с учётом титульной страницы без видимого номера на ней;
- настройка полей, шрифта, интервалов, абзацев и колонтитулов;
- проверка заголовков, ссылок, подписей, списков и структуры документа;
- выбор профиля документа и фиксация решений по конфликтам ГОСТ и методички.

Skill не придумывает содержание работы, выводы и библиографические записи без указания пользователя.

## Структура

```text
SKILL.md                         Основные инструкции skill
references/gost-rules.md         Правила ГОСТ 7.32 и проектные решения
references/niaspo-structure.md   Структура учебной работы НиАСПО
scripts/audit_docx.py            Аудит документа
scripts/apply_gost.py            Форматирование копии
scripts/build_gost.js            Создание нового DOCX
scripts/package.json             Node-зависимости генератора
```

## Использование

```bash
python3 scripts/audit_docx.py input.docx --out audit.md
python3 scripts/apply_gost.py input.docx
NODE_PATH=scripts/node_modules node scripts/build_gost.js task.json output.docx
```

Перед созданием документа skill выбирает профиль работы, собирает необходимые параметры и сообщает о конфликтах правил до генерации.

## Разработка

Проект развивается через feature-ветки и pull request. Все commit messages пишутся на английском языке. Перед отправкой изменений запускаются проверки из GitHub Actions.

Правила участия описаны в [CONTRIBUTING.md](CONTRIBUTING.md).

## English summary

`gost-docx` is a reusable skill for creating, auditing, and formatting DOCX documents according to GOST requirements and a selected institutional guideline. It supports research reports, coursework, theses, laboratory and practical assignments, and technical documentation.

The project is content-preserving: user-provided text remains authoritative, while layout, structure, validation, and document mechanics are handled by the skill.
