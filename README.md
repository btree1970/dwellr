# Dwell - AI-Powered Real Estate Listing Agent

AI-powered rental listing recommendation system with FastAPI, Celery workers, and Supabase authentication.

## Quick Start

### Local Development (Single Command)

```bash
# Start everything (Supabase + App services)
./dev.sh

```

**Alternative (manual steps):**
```bash
# Start Supabase services
supabase start

# Start app services
docker-compose -f docker-compose-local.yml up --build

```

**Services:**
- FastAPI API: http://localhost:8000 (docs: /docs)
- Flower (Celery monitoring): http://localhost:5555
- Supabase Studio: http://localhost:54323

## Architecture

- **FastAPI API**: Authentication, user management, listing queries
- **Celery Workers**: Background listing evaluation and sync tasks
- **Supabase**: Authentication and JWT validation
- **PostgreSQL**: Data storage (local: port 54322, via Supabase)
- **Redis**: Task queue broker

## Key Features

- **AI-Powered Evaluation**: OpenAI-based listing scoring against user preferences
- **Multi-Source Ingestion**: Configurable data sources via `ingestors.yaml`
- **Background Processing**: Async task processing with Celery
- **JWT Authentication**: Supabase-based user auth with automatic user creation
- **Real-time Monitoring**: Flower UI for task monitoring
- **Chat API**: Real-time conversational interface with streaming responses

## Development

### Environment Setup

```bash
# Copy environment template
cp .env.example .env.local

# Configure required variables
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
REDIS_URL=redis://localhost:6379/0
SUPABASE_URL=http://127.0.0.1:54321
OPENAI_API_KEY=your_key_here
```

### Core Commands

```bash
# Run tests
uv run pytest tests/

# Lint/format
uv run ruff check src/
uv run black src/

# Type check (excludes config.py)
uv run pyright src/
```

### Task Management

```python
from src.jobs.scheduler import JobScheduler
from src.jobs.job_types import JobType

scheduler = JobScheduler()
task_id = scheduler.schedule_job(
    JobType.EVALUATE_LISTINGS,
    context={"listing_ids": ["123", "456"]}
)
```

### CLI Usage

```bash
# Task management
python dwell_cli.py task sync --verbose
python dwell_cli.py task evaluate --no-wait
python dwell_cli.py task status <task_id>
python dwell_cli.py task list --type=sync --status=failed
```

## Deployment

### Fly.io (Single Machine)

```bash
# Deploy
fly deploy

# Monitor
fly logs
fly proxy 5555:5555  # Access Flower monitoring
```

Configuration: Single machine running all services via Supervisor with health checks on `/health`.

### Process Management

The application uses Supervisor for multi-process management:
- **fastapi**: Main API server
- **celery-worker**: Background task processor
- **celery-beat**: Scheduled task runner
- **flower**: Monitoring interface

## Configuration

### Database

- **Local**: Supabase PostgreSQL (auto-initialized)
- **Production**: Fly managed PostgreSQL

### Ingestors

Configuration for data sources in `ingestors.yaml`:

```yaml
ingestors:
  - name: "listings_project"
    class: "ListingProjectIngestor"
    enabled: true
    config:
      base_url: "https://api.example.com"
```

### User Preferences

Users can set preferences for:
- Price ranges and periods (daily/weekly/monthly)
- Date flexibility and preferred dates
- Listing types and natural language preferences
- Automatic evaluation based on OpenAI scoring

## Monitoring

- **Health**: `curl http://localhost:8000/health`
- **Flower**: http://localhost:5555
- **Logs**: `docker-compose logs -f` or `fly logs`
- **Redis**: `redis-cli ping`

## Security

- JWT validation via Supabase
- Environment-based configuration
- Production secrets managed via deployment platform
