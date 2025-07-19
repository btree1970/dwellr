import logging
import time
from datetime import datetime
from typing import Optional

from src.database.db import get_db_session
from src.jobs.job_types import JobType
from src.jobs.scheduler import JobScheduler
from src.models.task import Task

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self):
        self.scheduler = JobScheduler()

    def submit_task(self, job_type: JobType, context: dict = None) -> str:
        logger.info(f"Submitting new {job_type.value} task")
        task_id = self.scheduler.schedule_job(job_type=job_type, context=context or {})
        logger.info(f"Task submitted with ID: {task_id}")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Task]:
        with get_db_session() as db:
            task = db.query(Task).filter_by(id=task_id).first()
            db.expunge_all()
            return task

    def monitor_task(
        self, task_id: str, verbose: bool = False, timeout: int = 300
    ) -> bool:
        print(f"📋 Task {task_id} submitted to Celery queue")
        print("⏳ Monitoring task progress...")

        start_time = time.time()
        last_status = None

        while True:
            if time.time() - start_time > timeout:
                print(f"⚠️  Task monitoring timed out after {timeout} seconds")
                print(f"   Task {task_id} may still be running in the background")
                return False

            task = self.get_task_status(task_id)
            if not task:
                print(f"❌ Task {task_id} not found in database")
                return False

            if task.status != last_status:
                timestamp = datetime.now().strftime("%H:%M:%S")
                if task.status == "pending":
                    print(f"[{timestamp}] 📋 Task is pending...")
                elif task.status == "in_progress":
                    print(f"[{timestamp}] 🔄 Task is running...")
                elif task.status == "completed":
                    print(f"[{timestamp}] ✅ Task completed successfully!")
                    return True
                elif task.status == "failed":
                    print(f"[{timestamp}] ❌ Task failed!")
                    return False

                last_status = task.status

            time.sleep(2)

    def list_tasks(self, task_type: str = None, status: str = None, limit: int = 10):
        with get_db_session() as db:
            query = db.query(Task)

            if task_type:
                if task_type == "sync":
                    query = query.filter(Task.task_type == JobType.SYNC_LISTINGS.value)
                elif task_type == "evaluate":
                    query = query.filter(
                        Task.task_type == JobType.EVALUATE_LISTINGS.value
                    )

            if status:
                query = query.filter(Task.status == status)

            tasks = query.order_by(Task.created_at.desc()).limit(limit).all()
            db.expunge_all()
            return tasks
