from datetime import datetime, timezone
from typing import Any, Dict

from celery.exceptions import Retry
from celery.utils.log import get_task_logger
from sqlalchemy.exc import SQLAlchemyError

from src.database.db import get_db_session
from src.jobs.job_types import JobType
from src.models.task import Task
from src.models.user import User
from src.services.listing_agent import ListingAgent
from src.workers.celery_app import create_celery_app

logger = get_task_logger(__name__)

app = create_celery_app()

MIN_CREDIT_THRESHOLD = 0.10


@app.task(name="src.workers.tasks.scheduled_sync_task")
def scheduled_sync_task():
    from src.jobs.scheduler import JobScheduler

    scheduler = JobScheduler()
    task_id = scheduler.schedule_job(
        job_type=JobType.SYNC_LISTINGS, context={"scheduled": True}
    )

    logger.info(f"Created scheduled sync task {task_id}")
    return {"scheduled_task_id": task_id}


@app.task(name="src.workers.tasks.scheduled_evaluation_task")
def scheduled_evaluation_task():
    from src.jobs.scheduler import JobScheduler

    scheduler = JobScheduler()
    task_id = scheduler.schedule_job(
        job_type=JobType.EVALUATE_LISTINGS, context={"scheduled": True}
    )

    logger.info(f"Created scheduled evaluation task {task_id}")
    return {"scheduled_task_id": task_id}


@app.task(name="src.workers.tasks.process_task")
def process_task(task_id: str) -> Dict[str, Any]:
    logger.info(f"Starting task {task_id}")

    with get_db_session() as db:
        task = db.query(Task).filter_by(id=task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found in database")
            return {"error": "Task not found"}

        logger.info(f"Processing task {task_id} of type {task.task_type}")

        task.status = "in_progress"
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            if task.task_type == JobType.EVALUATE_LISTINGS.value:
                logger.info(f"Handling evaluate_listings for task {task_id}")
                result = handle_evaluate_listings(task)
            elif task.task_type == JobType.SYNC_LISTINGS.value:
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
    """Handle listing evaluation task - creates individual tasks for each eligible user"""

    with get_db_session() as db:
        users_query = db.query(User).filter(
            User.preference_profile.isnot(None),
            User.evaluation_credits >= MIN_CREDIT_THRESHOLD,
        )

        user_count = users_query.count()

        if user_count == 0:
            logger.info("No users found with sufficient credits for evaluation")
            return {
                "success": True,
                "users_found": 0,
                "tasks_created": 0,
                "message": "No users with sufficient credits found",
            }

        logger.info(f"Found {user_count} users with sufficient credits for evaluation")

        tasks_created = 0
        for user in users_query:
            try:
                app.send_task(
                    "src.workers.tasks.evaluate_user_listings", args=[user.id]
                )
                tasks_created += 1
                logger.info(
                    f"Created evaluation task for user {user.id} (credits: {user.evaluation_credits:.2f})"
                )
            except Exception as e:
                logger.error(f"Failed to create task for user {user.id}: {str(e)}")

        logger.info(f"Created {tasks_created} user evaluation tasks")

        return {
            "success": True,
            "users_found": user_count,
            "tasks_created": tasks_created,
            "message": f"Created {tasks_created} evaluation tasks for users with sufficient credits",
        }


@app.task(
    name="src.workers.tasks.evaluate_user_listings",
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, SQLAlchemyError, Retry),
    retry_kwargs={"max_retries": 2, "countdown": 60},
    retry_backoff=True,
)
def evaluate_user_listings(self: Any, user_id: str) -> Dict[str, Any]:
    """Evaluate listings for a single user - Celery handles retries automatically"""

    with get_db_session() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return {"success": False, "error": "User not found"}

        if user.evaluation_credits < MIN_CREDIT_THRESHOLD:
            logger.warning(
                f"User {user_id} has insufficient credits: {user.evaluation_credits:.2f}"
            )
            return {"success": False, "error": "Insufficient credits"}

        logger.info(
            f"Evaluating listings for user {user_id} with {user.evaluation_credits:.2f} credits (attempt {self.request.retries + 1})"
        )

        try:
            agent = ListingAgent(db)

            max_cost = user.evaluation_credits

            # TODO: Failures midway can still incur costs
            stats = agent.find_and_evaluate_listings(user, max_cost=max_cost)

            actual_cost = stats.get("total_cost", 0.0)
            if actual_cost > 0:
                user.evaluation_credits -= actual_cost
                db.commit()
                logger.info(
                    f"User {user_id}: {stats.get('evaluations_completed', 0)} evaluations, deducted ${actual_cost:.4f}, remaining: {user.evaluation_credits:.2f}"
                )
            else:
                logger.info(
                    f"User {user_id}: {stats.get('evaluations_completed', 0)} evaluations, no cost incurred"
                )

            return {
                "success": True,
                "user_id": user_id,
                "evaluations_completed": stats.get("evaluations_completed", 0),
                "total_cost": actual_cost,
                "remaining_credits": user.evaluation_credits,
                "candidate_listings_found": stats.get("candidate_listings_found", 0),
                "budget_exceeded": stats.get("budget_exceeded", False),
                "error_count": stats.get("error_count", 0),
            }

        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"User {user_id} permanent error: {str(e)}")
            return {
                "success": False,
                "user_id": user_id,
                "error": f"Permanent error: {str(e)}",
            }

        except Exception as e:
            logger.warning(
                f"User {user_id} transient error (attempt {self.request.retries + 1}): {str(e)}"
            )
            raise


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
