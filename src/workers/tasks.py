"""Basic task definitions"""

from datetime import datetime, timezone
from typing import Any, Dict

from src.database.db import get_db_session
from src.models.task import Task
from src.workers.celery_app import celery_app


@celery_app.task
def process_task(task_id: str) -> Dict[str, Any]:
    """Process a single task"""
    with get_db_session() as db:
        task = db.query(Task).filter_by(id=task_id).first()
        if not task:
            return {"error": "Task not found"}

        # Mark as started
        task.status = "in_progress"
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            # Simple routing based on task type
            if task.task_type == "evaluate_listings":
                result = handle_evaluate_listings(task)
            else:
                result = {"error": f"Unknown task type: {task.task_type}"}

            # Mark as completed
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.result = result
            db.commit()

            return result

        except Exception as e:
            # Mark as failed
            task.status = "failed"
            task.completed_at = datetime.now(timezone.utc)
            task.error_message = str(e)
            db.commit()
            raise


def handle_evaluate_listings(task: Task) -> Dict[str, Any]:
    """Handle listing evaluation task"""
    # Placeholder implementation
    context = task.context or {}
    listing_ids = context.get("listing_ids", [])

    return {
        "processed_listings": len(listing_ids),
        "message": f"Evaluated {len(listing_ids)} listings",
    }
