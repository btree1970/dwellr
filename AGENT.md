# Dwell - AI Assistant Documentation

## Project Overview

**Dwell** is an AI-powered rental property search and recommendation system that helps users find ideal housing through conversational AI. The system evaluates listings against user preferences using OpenAI GPT-4, providing personalized recommendations with intelligent filtering and scoring.

### Core Architecture

- **Backend**: FastAPI with async Python 3.11+, SQLAlchemy ORM, Pydantic validation
- **AI Framework**: Pydantic AI for structured LLM interactions with streaming responses
- **Task Queue**: Celery with Redis for background processing (evaluation, sync)
- **Database**: PostgreSQL (production) / SQLite (development)
- **Authentication**: Supabase JWT with automatic user creation
- **Real-time**: Server-Sent Events for streaming chat responses

### Service Components

1. **API Server** (`src/api/`) - FastAPI on port 8000
2. **Celery Worker** (`src/workers/`) - Background task processing
3. **Celery Beat** - Scheduled tasks (6-hour sync/evaluation cycles)
4. **Flower** - Task monitoring UI on port 5555
5. **Redis** - Message broker and cache
6. **PostgreSQL/SQLite** - Primary data storage

### Data Flow

1. **Ingestion**: External sources → Ingestors → Database
2. **Evaluation**: New listings → Hard filters → AI scoring → Recommendations
3. **Chat**: User input → Agent → Tools → Services → Streaming response

## Build & Commands

### Development Setup

```bash
# Install UV package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Copy environment configuration
cp .env.example .env.local
# Edit .env.local with your API keys (OPENAI_API_KEY, SUPABASE_URL, etc.)

# Start full development stack (recommended)
./dev.sh  # Starts Supabase + API + Workers + Flower with live logs
```

### Core Commands

#### Development
```bash
# Start services individually
uv run uvicorn src.api.main:app --reload --port 8000  # API server
uv run celery -A src.workers.celery_app worker --loglevel=info  # Worker
uv run celery -A src.workers.celery_app beat --loglevel=info  # Scheduler
uv run celery -A src.workers.celery_app flower  # Monitoring UI

# Docker alternative
docker-compose -f docker-compose-local.yml up --build
```

#### Testing
```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/unit/ -v  # Unit tests only
uv run pytest tests/integration/ -v  # Integration tests
uv run pytest tests/workflows/ -v  # Workflow tests

# With coverage
uv run pytest --cov=src --cov-report=term-missing

# Quick test run
uv run pytest tests/ -v --tb=short
```

#### Code Quality
```bash
# Linting
uv run ruff check src/  # Check for issues
uv run ruff check src/ --fix  # Auto-fix issues

# Formatting
uv run black src/  # Format code
uv run black src/ --check  # Check formatting without changes

# Type checking
uv run pyright src/  # Full type check
uv run pyright src/agents/  # Check specific module

# Pre-commit hooks
uv run pre-commit install  # Set up hooks
uv run pre-commit run -a  # Run all hooks manually
```

#### CLI Tools
```bash
# Task management
python dwell_cli.py task sync --verbose  # Run sync task
python dwell_cli.py task evaluate --verbose  # Run evaluation
python dwell_cli.py task status <task_id>  # Check task status
python dwell_cli.py task list --type=sync  # List tasks

# User agent testing
python dwell_cli.py user_agent --user-id <id>  # Test chat interface

# Database operations
python dwell_cli.py db init  # Initialize database
python dwell_cli.py db reset  # Reset database (careful!)
```

#### Deployment
```bash
# Build Docker image
docker build -t dwell:latest .

# Deploy to Fly.io
fly deploy  # Uses fly.toml configuration

# Check deployment
fly status
fly logs
```

## Code Style

### Python Standards

- **Python Version**: 3.11+ (use modern features like type hints, async/await)
- **Line Length**: 88 characters (Black/Ruff standard)
- **Indentation**: 4 spaces (no tabs)
- **Import Order**: Sorted by Ruff (stdlib → third-party → local)

### Naming Conventions

- **Files/Modules**: `snake_case.py`
- **Classes**: `PascalCase` (e.g., `UserAgent`, `ListingService`)
- **Functions/Variables**: `snake_case` (e.g., `get_user_preferences`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- **Private**: Leading underscore (e.g., `_internal_method`)

### Type Hints

```python
# Always use type hints for function signatures
from typing import List, Optional, Dict, Any

async def process_listings(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None
) -> List[Listing]:
    ...

# Use modern union syntax (Python 3.10+)
def get_price(period: str | None = None) -> float | None:
    ...
```

### Async/Await Patterns

```python
# Prefer async for I/O operations
async def fetch_data() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Use asyncio.gather for parallel operations
results = await asyncio.gather(
    fetch_user(user_id),
    fetch_listings(),
    fetch_preferences()
)
```

### Error Handling

```python
# Use specific exceptions
from src.api.exceptions import ChatSessionException

try:
    result = await process_request()
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise ChatSessionException(f"Invalid input: {str(e)}")
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed debug info")
logger.info(f"Processing user {user_id}")
logger.warning("Rate limit approaching")
logger.error(f"Failed to fetch listing: {e}")
logger.exception("Critical error with traceback")
```

## Testing

### Framework & Structure

- **Framework**: Pytest with async support
- **Structure**: `tests/` directory with subdirectories for unit/integration/workflow
- **Fixtures**: Shared in `tests/conftest.py` and `tests/fixtures/`
- **Naming**: Files `test_*.py`, classes `Test*`, functions `test_*`

### Testing Patterns

```python
# Basic test structure
import pytest
from unittest.mock import Mock, patch

@pytest.mark.asyncio
async def test_user_agent_chat():
    """Test that user agent handles chat correctly."""
    # Arrange
    user = create_test_user()
    agent = UserAgent(user=user)

    # Act
    response = await agent.chat("Find me a place in Brooklyn")

    # Assert
    assert response is not None
    assert "Brooklyn" in response.content
```

### Database Testing

```python
# Use test database fixture
@pytest.fixture
def test_db():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()

def test_listing_creation(test_db):
    listing = Listing(url="https://example.com", title="Test")
    test_db.add(listing)
    test_db.commit()
    assert listing.id is not None
```

### Mocking External Services

```python
# Mock OpenAI calls
@patch("openai.ChatCompletion.create")
def test_ai_evaluation(mock_openai):
    mock_openai.return_value = {
        "choices": [{"message": {"content": "8/10"}}]
    }
    score = evaluate_listing(listing, preferences)
    assert score == 8
```

### Test Categories

1. **Unit Tests** (`tests/unit/`) - Individual functions/methods
2. **Integration Tests** (`tests/integration/`) - Component interactions
3. **Workflow Tests** (`tests/workflows/`) - End-to-end scenarios
4. **Performance Tests** - Response times, memory usage

### Running Tests

```bash
# Quick validation
uv run pytest tests/ -v --tb=short

# Full test suite with coverage
uv run pytest --cov=src --cov-report=html

# Specific test file
uv run pytest tests/unit/test_user_agent.py -v

# Run tests matching pattern
uv run pytest -k "chat" -v
```

## Security

### API Keys & Secrets

```bash
# NEVER commit secrets to git
# Use environment variables via .env files

# Development hierarchy
.env.example  # Template with dummy values (committed)
.env.local    # Local development values (gitignored)
.env.test     # Test environment values (gitignored)
.env          # Production values (gitignored)
```

### Required Environment Variables

```bash
# Core Services
OPENAI_API_KEY=sk-...  # OpenAI API key for GPT-4
SUPABASE_URL=https://...supabase.co  # Supabase project URL
SUPABASE_ANON_KEY=eyJ...  # Supabase anonymous key
DATABASE_URL=postgresql://...  # PostgreSQL connection
REDIS_URL=redis://localhost:6379/0  # Redis connection

# Optional Configuration
ENV=local|development|production  # Environment name
LOG_LEVEL=INFO|DEBUG|WARNING  # Logging verbosity
CORS_ORIGINS=http://localhost:3000  # Allowed CORS origins
```

### Authentication & Authorization

- **JWT Validation**: All API endpoints validate Supabase JWT tokens
- **User Isolation**: Users only access their own data
- **Automatic User Creation**: New users created on first authenticated request

### Data Protection

```python
# Sanitize user input
from pydantic import validator

class UserPreferences(BaseModel):
    budget_max: float

    @validator('budget_max')
    def validate_budget(cls, v):
        if v < 0 or v > 1000000:
            raise ValueError("Invalid budget range")
        return v

# Parameterized queries (prevent SQL injection)
query = select(Listing).where(
    Listing.price <= :max_price
).params(max_price=user_budget)
```

### Rate Limiting

```python
# Implement rate limiting for expensive operations
from functools import wraps
from time import time

def rate_limit(max_calls=10, period=60):
    def decorator(func):
        calls = []

        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time()
            calls[:] = [c for c in calls if c > now - period]
            if len(calls) >= max_calls:
                raise Exception("Rate limit exceeded")
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

### Security Best Practices

1. **Input Validation**: Use Pydantic models for all user input
2. **SQL Injection**: Always use parameterized queries with SQLAlchemy
3. **XSS Prevention**: Sanitize all user-generated content
4. **CORS**: Configure allowed origins explicitly
5. **Secrets Management**: Use environment variables, never hardcode
6. **Logging**: Never log sensitive data (passwords, API keys)
7. **Dependencies**: Keep packages updated with `uv lock --upgrade`

## Configuration

### Environment Setup

```bash
# 1. Install system dependencies
brew install postgresql redis  # macOS
sudo apt-get install postgresql redis-server  # Ubuntu

# 2. Install Supabase CLI
brew install supabase/tap/supabase  # macOS
# Or see: https://supabase.com/docs/guides/cli

# 3. Clone and setup repository
git clone <repository>
cd dwell
uv sync  # Install Python dependencies

# 4. Configure environment
cp .env.example .env.local
# Edit .env.local with your configuration

# 5. Initialize database
uv run python -c "from src.core.database import init_db; init_db()"
```

### Configuration Files

#### `.env.local` Structure
```bash
# API Keys (Required)
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...  # Optional, for Claude

# Supabase (Required for auth)
SUPABASE_URL=https://xyz.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # Admin operations

# Database (Default: SQLite for local)
DATABASE_URL=sqlite:///./dwell.db  # Local development
# DATABASE_URL=postgresql://user:pass@localhost/dwell  # Production

# Redis (Required for Celery)
REDIS_URL=redis://localhost:6379/0

# Application Settings
ENV=local
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# AI Configuration
AI_MODEL=gpt-4-turbo-preview
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=1000
MAX_EVALUATION_COST=10.0  # Max $ to spend on evaluations per user

# Ingestor Configuration (if using external sources)
LISTING_PROJECT_EMAIL=user@example.com
LISTING_PROJECT_PASSWORD=password
```

#### `ingestors.yaml` Configuration
```yaml
default:
  listing_project:
    email: ${LISTING_PROJECT_EMAIL}
    password: ${LISTING_PROJECT_PASSWORD}
    cities:
      - new-york-city
    max_pages: 5
    rate_limit_seconds: 2

production:
  listing_project:
    cities:
      - new-york-city
      - san-francisco
      - los-angeles
    max_pages: 20
```

#### `supervisord.conf` (Production)
```ini
[program:fastapi]
command=uvicorn src.api.main:app --host 0.0.0.0 --port 8000
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/fastapi.err.log
stdout_logfile=/var/log/supervisor/fastapi.out.log

[program:celery_worker]
command=celery -A src.workers.celery_app worker --loglevel=info
directory=/app
autostart=true
autorestart=true

[program:celery_beat]
command=celery -A src.workers.celery_app beat --loglevel=info
directory=/app
autostart=true
autorestart=true

[program:flower]
command=celery -A src.workers.celery_app flower --port=5555
directory=/app
autostart=true
autorestart=true
```

### Database Management

```python
# Initialize database
from src.core.database import DatabaseManager

# Development
DatabaseManager.init_db()  # Create all tables
DatabaseManager.reset_db()  # Drop and recreate (careful!)

# Migrations (if using Alembic)
alembic init migrations
alembic revision --autogenerate -m "Add user preferences"
alembic upgrade head
```

### Monitoring & Debugging

```bash
# Health checks
curl http://localhost:8000/health  # API health
curl http://localhost:5555  # Flower UI

# View logs
docker-compose logs -f dwell-app  # Docker logs
tail -f logs/celery_worker.log  # Celery logs

# Debug database
uv run python -c "
from src.core.database import get_db
from src.models import User
db = next(get_db())
users = db.query(User).all()
print(f'Total users: {len(users)}')
"

# Monitor Redis
redis-cli
> PING
> INFO stats
> MONITOR  # Watch commands in real-time
```

### Performance Tuning

```python
# Celery configuration (src/workers/celery_app.py)
app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    worker_max_tasks_per_child=100,  # Restart after 100 tasks
    task_time_limit=300,  # 5 minute timeout
    task_soft_time_limit=240,  # 4 minute soft timeout
)

# Database connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Number of connections
    max_overflow=40,  # Maximum overflow connections
    pool_timeout=30,  # Timeout for getting connection
    pool_recycle=1800,  # Recycle connections after 30 minutes
)

# API rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/v1/chat/message")
@limiter.limit("10/minute")
async def chat_message(request: Request):
    ...
```

## Quick Reference

### Common Tasks

```bash
# Start development
./dev.sh

# Run tests
uv run pytest tests/ -v

# Format code
uv run black src/ && uv run ruff check src/ --fix

# Check types
uv run pyright src/

# View task queue
open http://localhost:5555  # Flower UI

# Test chat interface
python dwell_cli.py user_agent --user-id test-user

# Check API health
curl http://localhost:8000/health

# View database
uv run python -c "from src.core.database import get_db; ..."
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | `lsof -i :8000` then `kill -9 <PID>` |
| Redis connection refused | Start Redis: `redis-server` or `brew services start redis` |
| Database locked (SQLite) | Restart services, check for hanging connections |
| Celery tasks not running | Check Redis connection, restart worker |
| Type errors | Run `uv run pyright src/` to identify issues |
| Import errors | Ensure `uv sync` completed, check PYTHONPATH |
| Supabase auth fails | Verify SUPABASE_URL and SUPABASE_ANON_KEY |
| OpenAI rate limits | Implement exponential backoff, check API quotas |

### Project Structure

```
dwell/
├── src/
│   ├── api/           # FastAPI application
│   │   ├── routes/    # API endpoints
│   │   ├── schemas/   # Pydantic models for API
│   │   └── utils/     # SSE, auth utilities
│   ├── agents/        # AI agent system
│   │   ├── user_agent.py     # Conversational agent
│   │   ├── stream_events.py  # Event types
│   │   ├── message_formatter.py  # Message formatting
│   │   └── tools/     # Agent tool implementations
│   ├── core/          # Core configuration
│   │   ├── config.py  # Settings management
│   │   ├── database.py  # Database connection
│   │   └── supabase_client.py  # Auth client
│   ├── models/        # SQLAlchemy models
│   ├── services/      # Business logic
│   ├── workers/       # Celery tasks
│   └── ingestors/     # Data ingestion
├── tests/             # Test suites
├── cli/               # CLI commands
├── logs/              # Application logs
└── docker/            # Docker configurations
```

### Key Files

- `dev.sh` - Development environment launcher
- `docker-compose-local.yml` - Local services configuration
- `pyproject.toml` - Python dependencies and tools
- `.env.local` - Environment configuration
- `ingestors.yaml` - Data source configuration
- `supervisord.conf` - Production process management
- `fly.toml` - Fly.io deployment configuration
