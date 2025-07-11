# Workers Setup

## Quick Start

1. **Start Redis:**
```bash
docker-compose -f docker-compose.dev.yml up -d redis
```

2. **Start Worker:**
```bash
celery -A src.workers.celery_app worker --loglevel=info
```

3. **Test the setup:**
```bash
pytest tests/test_workers_basic.py
```

## Basic Usage

```python
from src.jobs.scheduler import JobScheduler
from src.jobs.job_types import JobType

scheduler = JobScheduler()
task_id = scheduler.schedule_job(
    JobType.EVALUATE_LISTINGS,
    context={"listing_ids": ["123", "456"]}
)
```

## Development Commands

- **Monitor with Flower:** `celery -A src.workers.celery_app flower`
- **Check Redis:** `redis-cli ping`
