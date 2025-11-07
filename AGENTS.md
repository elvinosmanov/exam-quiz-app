# Repository Guidelines

## Project Structure & Module Organization
The Flet client and business logic live in `quiz_app/`. Configuration defaults are in `quiz_app/config.py`, reusable helpers under `utils/`, and SQLite integration in `database/` (see `database.py` for `Database` and `init_database`). UI components are grouped by role in `views/admin`, `views/auth`, and `views/examinee`. Top-level scripts (`run.py`, `main.py`, `test_db.py`) handle startup flows, while automation scripts such as `create_azerbaijani_questions.py` reside in the repository root. Generated data (`quiz_app.db`, exports, logs) should be git-ignored or routed to `exam_exports/` and `logs/`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create and activate a local virtual environment.
- `pip install -r requirements.txt`: install Flet, bcrypt, and reporting dependencies required for the desktop UI.
- `python run.py`: launch the Quiz Examination System with automatic DB provisioning and asset loading.
- `python test_db.py`: smoke-test schema creation, seed credentials, and sample exam fixtures.
- `python main.py`: run the app when the database is already provisioned (used by the Flet runtime).

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation, single quotes for lightweight strings, and descriptive snake_case for functions, modules, and filenames. Keep class names in PascalCase (`AuthManager`, `SessionManager`) and constants in UPPER_SNAKE_CASE. Before committing UI-facing code, verify imports remain relative to `quiz_app` and avoid hard-coded absolute paths; resolve assets through `assets_dir="quiz_app/assets"` when wiring Flet controls.

## Testing Guidelines
`test_db.py` doubles as a regression check for database migrations—run it whenever schema or auth logic changes. Prefer extending it with additional assertions rather than adding ad-hoc print statements. When modifying Flet views, manually validate interaction flows (login, admin dashboards, examinee dashboards) after running the script. Tie any automated tests into `pytest`-style functions so they can later be collected by a test runner.

## Commit & Pull Request Guidelines
Existing history follows conventional commits (`feat:`, `fix:`, `chore:`); use imperative present tense and keep subjects under ~72 characters. Reference related issues in the commit body when available. For pull requests, include: 1) a concise summary of the change and affected screens, 2) reproduction or verification steps (`python run.py`, `python test_db.py`), and 3) screenshots or screen recordings for UI updates. Confirm default credentials (`admin/admin123`, `testuser/testpass123`) still log in before requesting review.

## Security & Configuration Notes
Store SQLite artifacts and exports locally; do not commit `quiz_app.db` or generated XLSX/PDF files. Rotate default credentials before production deployment and document any new seed data under `quiz_app/database/seed_data`. Keep environment-specific settings in `.env` or secure config overrides rather than editing `config.py` directly.
