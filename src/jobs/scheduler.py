from typing import Any, Dict, Optional

from src.database.db import get_db_session
from src.jobs.job_types import JobType
from src.models.task import Task
from src.workers.celery_app import celery_app


class JobScheduler:
    """Basic job scheduling functionality"""

    def schedule_job(
        self, job_type: JobType, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Schedule a job to run immediately"""

        # Create task in database
        task = Task(task_type=job_type.value, context=context or {}, status="pending")

        with get_db_session() as db:
            db.add(task)
            db.commit()
            task_id = task.id

        # Send to Celery
        celery_app.send_task("src.workers.tasks.process_task", args=[task_id])

        return task_id
