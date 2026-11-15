# Contributing to gost-docx

## Development workflow

1. Start from an up-to-date `main` branch.
2. Create a focused branch, for example `feature/title-placeholder` or `fix/audit-a3`.
3. Keep each logical change in a separate commit.
4. Write commit messages in English using an imperative subject, such as `Add automatic table of contents`.
5. Open a pull request with a clear description and verification steps.
6. Wait for GitHub Actions to pass before merging.

## Scope of changes

- Keep user content authoritative; do not invent report text or sources.
- Keep GOST requirements separate from institution-specific rules.
- Ask for an explicit choice when two applicable rule sets conflict.
- Preserve the original DOCX when a workflow promises a formatted copy.
- Add or update a meaningful regression check for behavior changes.

## Pull requests

Pull requests should explain:

- what behavior changed;
- which document profiles are affected;
- how the result was tested;
- whether a visual DOCX inspection is required.

Do not include personal student data or real private documents in the repository.
