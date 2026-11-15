# Архитектура проекта

Диаграмма показывает основные потоки обработки документов: аудит, копирование форматирования и генерацию отчёта.

```mermaid
flowchart LR
    Input[Входной DOCX или данные отчёта]
    Rules[Правила ГОСТ\nreferences/gost-rules.md]
    Audit[Аудит документа\nscripts/audit_docx.py]
    AuditReport[Отчёт об ошибках\nи предупреждениях]

    Source[Исходный DOCX]
    FormatCopy[Копирование форматирования\nscripts/apply_gost.py]
    Styled[DOCX с оформлением\nпо ГОСТ]

    Data[Данные отчёта\nJSON / fixture]
    Generate[Генерация документа\nscripts/build_gost.js]
    Document[Итоговый DOCX]

    Input --> Audit
    Rules --> Audit
    Audit --> AuditReport

    Source --> FormatCopy
    Rules --> FormatCopy
    FormatCopy --> Styled

    Data --> Generate
    Rules --> Generate
    Generate --> Document

    classDef input fill:#e3f2fd,stroke:#1976d2,color:#0d47a1
    classDef process fill:#fff3e0,stroke:#ef6c00,color:#e65100
    classDef output fill:#e8f5e9,stroke:#388e3c,color:#1b5e20
    classDef rules fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c

    class Input,Source,Data input
    class Audit,FormatCopy,Generate process
    class AuditReport,Styled,Document output
    class Rules rules
```

## Потоки

- **Аудит:** входной DOCX проверяется скриптом `audit_docx.py` по правилам ГОСТ; результатом становится отчёт об ошибках и предупреждениях.
- **Копирование форматирования:** исходный DOCX и правила ГОСТ передаются в `apply_gost.py`, который возвращает оформленный документ.
- **Генерация:** данные отчёта и правила ГОСТ используются `build_gost.js` для создания итогового DOCX.
