from datetime import datetime, timezone
from typing import Any, Dict

from celery.utils.log import get_task_logger

from src.database.db import get_db_session
from src.models.task import Task
from src.workers.celery_app import create_celery_app

logger = get_task_logger(__name__)

app = create_celery_app()


@app.task(name="src.workers.tasks.process_task")
def process_task(task_id: str) -> Dict[str, Any]:
    logger.info(f"Starting task {task_id}")

    with get_db_session() as db:
        task = db.query(Task).filter_by(id=task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found in database")
            return {"error": "Task not found"}

        logger.info(f"Processing task {task_id} of type {task.task_type}")

        # Mark as started
        task.status = "in_progress"
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            # Simple routing based on task type
            if task.task_type == "evaluate_listings":
                logger.info(f"Handling evaluate_listings for task {task_id}")
                result = handle_evaluate_listings(task)
            elif task.task_type == "sync_listings":
                logger.info(f"Handling sync_listings for task {task_id}")
                result = handle_sync_listings(task)
            else:
                logger.error(f"Unknown task type: {task.task_type} for task {task_id}")
                result = {"error": f"Unknown task type: {task.task_type}"}

            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.result = result
            db.commit()

            logger.info(f"Task {task_id} completed successfully")
            return result

        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}", exc_info=True)

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


def handle_sync_listings(task: Task) -> Dict[str, Any]:
    """Handle listing sync task - syncs all enabled sources"""
    from src.ingestors.ingestor import ingestor

    try:
        logger.info("Starting sync for all enabled sources")
        results = ingestor.sync_all_enabled()

        # Aggregate stats across all sources
        total_new_listings = sum(result.new_listings for result in results.values())
        total_processed = sum(result.total_processed for result in results.values())
        total_errors = sum(result.errors for result in results.values())

        logger.info(
            f"Sync completed: {len(results)} sources, {total_new_listings} new listings, {total_processed} total processed"
        )

        # Log per-source results
        for source, result in results.items():
            if result.success:
                logger.info(
                    f"Source {source}: {result.new_listings} new, {result.total_processed} processed"
                )
            else:
                logger.warning(f"Source {source} failed: {result.error_message}")

        # Check if any sources failed
        all_success = all(result.success for result in results.values())

        return {
            "success": all_success,
            "sources_synced": len(results),
            "stats": {
                "total_new_listings": total_new_listings,
                "total_processed": total_processed,
                "total_errors": total_errors,
                "sources": {
                    source: {
                        "new_listings": result.new_listings,
                        "total_processed": result.total_processed,
                        "errors": result.errors,
                        "success": result.success,
                    }
                    for source, result in results.items()
                },
            },
            "message": f"Synced {total_new_listings} new listings from {len(results)} sources",
        }

    except Exception as e:
        logger.error(f"Sync failed with exception: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to sync all sources: {str(e)}",
        }
