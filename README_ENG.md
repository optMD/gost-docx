# gost-docx

**Audit. Format. Build DOCX documents to GOST.**

<p align="center">
  <img src="docs/assets/readme-hero.jpg" alt="DOCX document with margin guides and measurement tools" width="860">
</p>

<p align="center">
  A local Agent Skill for Codex, Claude Code, and other compatible agents.
</p>

<p align="center">
  <a href="https://github.com/optMD/gost-docx/actions/workflows/validate.yml"><img src="https://github.com/optMD/gost-docx/actions/workflows/validate.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/optMD/gost-docx/releases"><img src="https://img.shields.io/github/v/release/optMD/gost-docx?display_name=tag" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/optMD/gost-docx" alt="License"></a>
</p>

`gost-docx` helps work with Word documents according to GOST 7.32-2017,
GOST R 7.0.100-2018, and user-provided institutional guidelines.

## Features

| Mode | Result |
| --- | --- |
| Audit | Markdown report with findings |
| Formatting | `*_gost.docx` copy; the source file is preserved |
| Generation | New DOCX from a structured JSON specification |

Checks cover page size, margins, fonts, spacing, paragraphs, footers, page
numbers, headings, captions, citations, and core document structure.

## Installation

Install the skill for all detected agents:

```bash
npx skills add https://github.com/optMD/gost-docx \
  --skill gost-docx --agent '*' --global --yes
```

Install only for Codex and Claude Code:

```bash
npx skills add https://github.com/optMD/gost-docx \
  --skill gost-docx --agent codex --agent claude-code --global --yes
```

See the [installation guide](docs/installation.md) for project-local setup,
agent paths, and Claude.ai upload notes.

## Quick start

Install runtime dependencies from a clone:

```bash
git clone https://github.com/optMD/gost-docx.git
cd gost-docx
python3 -m pip install lxml
npm ci --prefix scripts
```

Check the environment:

```bash
python3 scripts/gost_docx.py doctor
python3 scripts/gost_docx.py --version
```

Audit an existing document:

```bash
python3 scripts/gost_docx.py audit report.docx --out audit.md
```

Format a copy:

```bash
python3 scripts/gost_docx.py format report.docx
```

Build a document from JSON:

```bash
python3 scripts/gost_docx.py build examples/task-report.json report.docx
```

The complete reproducible example is available in [`examples/`](examples/).

## Principles

- formatting never overwrites the source DOCX;
- content, conclusions, sources, and personal data are never invented;
- conflicts between GOST and a guideline are shown to the user;
- final visual review after rendering remains a human responsibility.

## Architecture

```text
DOCX / JSON → gost-docx → audit / format / build → DOCX / report
```

See [docs/architecture.md](docs/architecture.md) for the detailed data flow.

## Limitations

- formulas and rendered visual output require manual review;
- the Word table of contents must be updated after generation;
- complex tables and non-standard title pages may need manual refinement.

## Development

```bash
python3 -m compileall -q scripts tests
node --check scripts/build_gost.js
python3 -m unittest discover -s tests -v
git diff --check
```

Use focused branches and pull requests. See [CONTRIBUTING.md](CONTRIBUTING.md),
[CHANGELOG.md](CHANGELOG.md), and [SECURITY.md](SECURITY.md).

## License

[MIT License](LICENSE) · [Русская версия README](README.md)
