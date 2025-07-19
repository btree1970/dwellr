# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Commands
- **Install dependencies**: `uv sync` (uses uv package manager)
- **Run tests**: `pytest tests/` or `python -m pytest tests/`
- **Run single test**: `pytest tests/test_workers_basic.py`
- **Lint code**: `ruff check src/`
- **Format code**: `black src/`
- **Type check**: `mypy src/`

### Worker/Celery Commands
- **Start Redis**: `docker-compose -f docker-compose.dev.yml up -d redis`
- **Start worker**: `celery -A src.workers.celery_app worker --loglevel=info`
- **Start scheduler**: `celery -A src.workers.tasks beat --loglevel=info`
- **Monitor with Flower**: `celery -A src.workers.celery_app flower`
- **Check Redis**: `redis-cli ping`

### Application Commands
- **Run rental app**: `python dwell_app.py`
- **Task management CLI**: `python dwell_cli.py task <command>`
- **Initialize database**: Use `DatabaseManager.init_db()` in code
- **Reset database**: Use `DatabaseManager.reset_db()` in code

### Task Management CLI
- **Run sync task**: `python dwell_cli.py task sync [--verbose] [--no-wait]`
- **Run evaluation task**: `python dwell_cli.py task evaluate [--verbose] [--no-wait]`
- **Check task status**: `python dwell_cli.py task status <task_id> [--verbose]`
- **List tasks**: `python dwell_cli.py task list [--type=sync|evaluate] [--status=failed]`

## Architecture Overview

### Core Components
1. **Data Models** (`src/models/`): SQLAlchemy models for listings, users, tasks, and evaluations
2. **Database Layer** (`src/database/`): Database connection, session management, and schema
3. **Ingestors** (`src/ingestors/`): Data ingestion from listing sources (configured via `ingestors.yaml`)
4. **Workers** (`src/workers/`): Celery-based background task processing
5. **Services** (`src/services/`): Business logic for listing evaluation and agent operations
6. **Jobs** (`src/jobs/`): Job scheduling and task management system

### Key Architecture Patterns
- **Configuration**: Pydantic-based settings in `src/config.py` with environment variable support
- **Database**: SQLAlchemy with PostgreSQL (prod) or SQLite (dev), session management via context managers
- **Background Tasks**: Celery with Redis broker for async processing
- **Ingestor Pattern**: Abstract base class `BaseIngestor` for pluggable data sources
- **Agent Pattern**: `ListingAgent` orchestrates finding, evaluating, and recommending listings

### Data Flow
1. **Ingestion**: Ingestors fetch listings from external sources → Database
2. **Processing**: Workers process tasks (evaluation, sync) via Celery queues
3. **Evaluation**: `ListingEvaluator` uses OpenAI to score listings against user preferences
4. **Recommendation**: `ListingAgent` filters and ranks listings for users

### Key Files
- `src/config.py`: Application configuration and environment variables
- `src/database/db.py`: Database connection and session management
- `src/ingestors/base_ingestor.py`: Abstract ingestor interface
- `src/workers/celery_app.py`: Celery application configuration
- `src/services/listing_agent.py`: Main business logic for listing operations
- `ingestors.yaml`: Configuration for data ingestion sources
- `dwell.py`: Main CLI application entry point

### Testing
- Uses pytest with fixtures in `tests/conftest.py`
- Test data helpers in `tests/fixtures/test_data.py`
- Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- Configuration in `pytest.ini`

### Environment Setup
- Uses `.env` files for configuration (`.env`, `.env.local`, `.env.test`)
- Python 3.11+ required
- Development dependencies managed via `uv` with `pyproject.toml`
- Pre-commit hooks configured for code quality

### Docker Support
- `Dockerfile` for containerization
- `docker-compose-local.yml` for local development
- `fly.toml` for Fly.io deployment
