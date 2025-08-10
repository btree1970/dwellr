# Repository Guidelines

## Project Structure & Modules
- `src/`: Application code
  - `api/` (FastAPI app, routes, schemas, utils)
  - `agents/` (chat/decision agents, tools, formatting)
  - `core/` (config, DB, Supabase clients)
  - `workers/` (Celery app and tasks), `jobs/` (scheduler, job types)
  - `services/`, `models/`, `ingestors/`
- `tests/`: Pytest suites (`tests/integration/`, fixtures)
- `cli/` and `dwell_cli.py`: Local CLI utilities
- Top-level configs: `.env.example`, `ingestors.yaml`, `supervisord.conf`, `docker-compose-local.yml`

## Build, Test, and Development
- Start full stack: `./dev.sh` (Supabase + API + workers + Flower)
- Manual run: `docker-compose -f docker-compose-local.yml up --build`
- Run tests: `uv run pytest -v`
- Lint/format: `uv run ruff check src/ && uv run black src/`
- Type check: `uv run pyright src/`
- Pre-commit: `uv run pre-commit install` then `uv run pre-commit run -a`

## Coding Style & Naming
- Python ≥ 3.11; 4-space indent; line length 88 (Black/Ruff)
- Imports sorted (Ruff). Keep functions small and typed.
- Type hints required (strict Pyright). `src/core/config.py` is excluded.
- Naming: modules/files `snake_case.py`; classes `PascalCase`; functions/vars `snake_case`.

## Testing Guidelines
- Framework: Pytest. Naming from `pytest.ini`:
  - Files `test_*.py`, classes `Test*`, functions `test_*`
- Quick run: `uv run pytest tests/ -v --tb=short`
- Coverage (optional): `uv run pytest --cov=src --cov-report=term-missing`
- Add tests for new logic in the closest package (e.g., `tests/integration/` for cross-component flows).

## Commit & Pull Request Guidelines
- Commits: short, imperative summaries (present tense). Example: `refactor agent events`, `set up chat api`.
- PRs must include: clear description, linked issues, steps to reproduce/verify, screenshots or logs for API/worker changes, and pass lint/type/tests.

## Security & Configuration Tips
- Never commit secrets. Copy `.env.example` to `.env.local` and set `OPENAI_API_KEY`, `SUPABASE_URL`, `DATABASE_URL`, `REDIS_URL`.
- Health checks: `curl http://localhost:8000/health`; Flower: `http://localhost:5555`.
