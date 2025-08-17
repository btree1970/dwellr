import logging
from typing import Any, Dict, Optional

from src.core.database import get_db_manager
from src.jobs.job_types import JobType
from src.models.task import Task
from src.workers.tasks import app

logger = logging.getLogger(__name__)


class JobScheduler:
    def schedule_job(
        self, job_type: JobType, context: Optional[Dict[str, Any]] = None
    ) -> str:
        logger.info(f"Creating new task of type {job_type.value}")

        task = Task(task_type=job_type.value, context=context or {}, status="pending")

        with get_db_manager().get_session() as db:
            db.add(task)
            db.commit()
            task_id = task.id

        logger.info(f"Task {task_id} created, submitting to Celery queue")

        app.send_task("src.workers.tasks.process_task", args=[task_id])

        logger.info(f"Task {task_id} submitted successfully")
        return task_id
