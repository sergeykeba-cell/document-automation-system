# Contributing to document-automation-system

Thanks for considering a contribution! Whether it's a bug fix, a new feature, or a documentation improvement, contributions are welcome.

## Ways to contribute

- 🐛 Report bugs via [Issues](https://github.com/sergeykeba-cell/document-automation-system/issues) using the bug report template.
- 💡 Suggest features (new document templates, additional export formats, etc.).
- 🧪 Add tests — the project currently has limited test coverage, especially around Excel import and PDF generation edge cases.
- 📚 Improve documentation.

## Local development setup

1. Fork and clone the repo.
2. Copy `.env.example` to `.env` and fill in local values.
3. Start the app with Docker:
   ```bash
   docker-compose up
   ```
   or manually:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
4. Open `http://localhost:8000`.

## ⚠️ Handling personal data

This project processes personnel/HR-style data. When contributing:

- **Never** commit real personal data (names, IDs, contact info) in test fixtures, screenshots, or sample files.
- Use synthetic/fake data for any example Excel files or screenshots (e.g. via [Faker](https://faker.readthedocs.io/)).
- Double-check `.env`, database files, and uploaded files are excluded via `.gitignore` before pushing.

## Code style

- Format Python code with [`black`](https://github.com/psf/black) and lint with [`ruff`](https://github.com/astral-sh/ruff).
- Public functions should have docstrings and type hints, especially in the Excel import and PDF generation services where edge cases (empty cells, malformed dates, missing columns) matter most.

## Submitting a pull request

1. Create a branch from `main`: `git checkout -b feat/short-description`.
2. Make your changes and add/update tests where relevant.
3. Fill in the PR template — describe *what* changed and *why*.
4. Link any related issue.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).
