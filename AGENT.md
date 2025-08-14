# Dwell - AI-Powered Rental Search System

## What is Dwell?

AI rental property search with conversational interface. Evaluates listings against user preferences using GPT-4, provides personalized recommendations with intelligent scoring.

## Architecture at a Glance

**Stack:** Remix (SSR) + FastAPI + Pydantic AI + Celery + Redis + PostgreSQL/SQLite + Supabase Auth

**Services & Ports:**

- Frontend: `localhost:5173` (Remix/Vite)
- API: `localhost:8000` (FastAPI)
- Flower: `localhost:5555` (Task monitoring)
- Redis: `localhost:6379`
- Supabase: `localhost:54321` (local)

**Key Data Flows:**

- Chat: Browser → Remix proxy → FastAPI → Pydantic AI Agent → SSE streaming
- Auth: Browser cookies → Remix → Supabase → FastAPI JWT validation (server-side only)
- Tasks: API → Redis → Celery Worker → Database
- Sync: Scheduled (6hr) → Ingestors → Database → AI Evaluation

## Quick Start

```bash
# First time setup
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install UV
uv sync                                           # Python deps
cd web && npm install && cd ..                   # Frontend deps
cp .env.example .env.local                       # Configure env

# Start everything
./local-dev.sh  # Recommended: Full stack with logs

# Or start individually
uv run uvicorn src.api.main:app --reload --port 8000
cd web && npm run dev
```

## Essential Commands

```bash
# Development
./local-dev.sh                # Full stack
cd web && npm run dev         # Frontend only
uv run pytest tests/ -v       # Run tests
uv run black src/ && uv run ruff check src/ --fix  # Format & lint
uv run pyright src/           # Type check

# Frontend
cd web && npm run build       # Production build
cd web && npm run lint        # Lint
cd web && npm run typecheck   # TypeScript check

# Testing
uv run pytest tests/unit/ -v  # Unit tests
uv run pytest --cov=src       # With coverage

# CLI Tools
./dwell_cli.py db init                  # Initialize database with migrations
./dwell_cli.py db migrate                # Run pending migrations
./dwell_cli.py db status                 # Check migration status
./dwell_cli.py db create-migration "description"  # Create new migration
./dwell_cli.py db rollback               # Rollback last migration
./dwell_cli.py db history                # View migration history
./dwell_cli.py db verify                 # Verify schema integrity
./dwell_cli.py task sync --verbose      # Manual sync
./dwell_cli.py user_agent --user-id test # Test chat

# Monitoring
open http://localhost:5555    # Flower UI
curl http://localhost:8000/health  # API health
```

## Code Patterns

### Python (3.11+)

```python
# Type hints always
async def process_listings(
    user_id: str,
    filters: dict[str, Any] | None = None
) -> list[Listing]:
    ...

# Async for I/O
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        return await response.json()

# Error handling
from src.api.exceptions import ChatSessionException
try:
    result = await process_request()
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise ChatSessionException(f"Invalid input: {str(e)}")
```

### Frontend (TypeScript/Remix)

```typescript
// Use loader for SSR data
export const loader = async ({ request }: LoaderFunctionArgs) => {
  const user = await requireAuth(request);
  return json({ user });
};

// Action for mutations
export const action = async ({ request }: ActionFunctionArgs) => {
  const formData = await request.formData();
  // Handle form submission
};

// Components with proper types
interface ChatMessageProps {
  message: string;
  timestamp: Date;
}
```

## Project Structure

```
dwell/
├── src/
│   ├── api/          # FastAPI app
│   │   ├── routes/   # Endpoints
│   │   └── utils/    # SSE, auth helpers
│   ├── agents/       # Pydantic AI agents
│   │   ├── user_agent.py       # Main chat agent
│   │   └── tools/              # Agent tools
│   ├── core/         # Config, database, auth
│   ├── models/       # SQLAlchemy models
│   ├── services/     # Business logic
│   ├── workers/      # Celery tasks
│   └── ingestors/    # Data ingestion
├── web/
│   ├── app/
│   │   ├── routes/   # Remix routes
│   │   └── services/ # API clients
│   └── package.json
├── tests/            # Pytest tests
├── .env.local        # Environment config
├── local-dev.sh      # Dev launcher
└── pyproject.toml    # Python deps
```

## Key Files & Their Purpose

**Backend Core:**

- `src/api/main.py:45` - FastAPI app setup & middleware
- `src/agents/user_agent.py:120` - Main AI conversation handler
- `src/core/config.py:30` - Settings management
- `src/workers/celery_app.py:15` - Task queue configuration

**Frontend Core:**

- `web/app/root.tsx:25` - Root layout & providers
- `web/app/routes/chat.tsx:85` - Chat interface
- `web/app/services/api.ts:40` - API client
- `web/app/services/auth.server.ts:60` - Auth utilities

**Configuration:**

- `.env.local` - API keys, database URLs
- `ingestors.yaml` - Data source config
- `docker-compose-local.yml` - Local services

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xyz.supabase.co
SUPABASE_ANON_KEY=eyJ...
DATABASE_URL=sqlite:///./dwell.db  # or postgresql://...
REDIS_URL=redis://localhost:6379/0

# Optional
AI_MODEL=gpt-4-turbo-preview
LOG_LEVEL=INFO
API_BASE_URL=http://localhost:8000
```

## Testing Strategy

```python
# Unit test example
@pytest.mark.asyncio
async def test_user_agent_chat():
    user = create_test_user()
    agent = UserAgent(user=user)
    response = await agent.chat("Find me a place in Brooklyn")
    assert "Brooklyn" in response.content

# Mock external services
@patch("openai.ChatCompletion.create")
def test_ai_evaluation(mock_openai):
    mock_openai.return_value = {"choices": [{"message": {"content": "8/10"}}]}
    score = evaluate_listing(listing, preferences)
    assert score == 8
```

## Common Issues & Solutions

| Issue                | Fix                                           |
| -------------------- | --------------------------------------------- |
| Port in use          | `lsof -i :8000 && kill -9 <PID>`              |
| Redis refused        | `redis-server` or `brew services start redis` |
| Type errors          | `uv run pyright src/`                         |
| Import errors        | `uv sync`                                     |
| Frontend build fails | Check Node 20+, `cd web && npm install`       |
| Auth fails           | Verify SUPABASE_URL and SUPABASE_ANON_KEY     |
| CORS errors          | Update CORS_ORIGINS to include frontend URL   |

## Code Style Rules

- **Python:** Black formatter, Ruff linter, type hints required
- **TypeScript:** ESLint, Prettier, strict mode
- **Naming:** snake_case (Python), camelCase (TS), PascalCase (classes/components)
- **Async:** Prefer async/await over callbacks
- **Errors:** Specific exceptions, proper logging levels
- **Security:** No hardcoded secrets, parameterized queries, input validation

## Deployment

```bash
# Docker
docker build -t dwell:latest .
docker-compose up

# Fly.io
fly deploy  # Uses fly.toml
fly status
fly logs
```

## Database Migrations

The project uses Alembic for database schema management. Migrations run automatically on startup via `./local-dev.sh`, but you can manage them manually:

```bash
# After modifying models, create a new migration
./dwell_cli.py db create-migration "add new field to user"

# Apply pending migrations
./dwell_cli.py db migrate

# Check migration status
./dwell_cli.py db status

# Rollback if needed
./dwell_cli.py db rollback

# View history
./dwell_cli.py db history
```

## Workflow Tips

1. **Always run after code changes:**
   - Backend: `uv run black src/ && uv run ruff check src/ --fix && uv run pyright src/`
   - Frontend: `cd web && npm run lint && npm run typecheck`

2. **Before commits:**
   - Run tests: `uv run pytest tests/ -v`
   - Check types: `uv run pyright src/`

3. **Debugging:**
   - Check Flower UI for task status
   - Use `logger.debug()` liberally
   - Monitor Redis: `redis-cli MONITOR`

4. **Performance:**
   - Use `asyncio.gather()` for parallel operations
   - Implement caching for expensive queries
   - Profile with `cProfile` for bottlenecks

## Security Checklist

- [ ] Environment variables for all secrets
- [ ] Pydantic models for input validation
- [ ] Parameterized database queries
- [ ] JWT validation on all API endpoints
- [ ] Rate limiting on expensive operations
- [ ] CORS properly configured
- [ ] Dependencies regularly updated (`uv lock --upgrade`)

## Need Help?

- API Docs: http://localhost:8000/docs
- Task Monitor: http://localhost:5555
- Logs: `tail -f logs/*.log`
- Database: `uv run python -c "from src.core.database import get_db; ..."`

- use linear mcp to create and manage tasks
- use uv add <packagae> to add dependiences. Do not add directly to pyproject.toml
