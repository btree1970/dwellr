from src.database.db import get_db_session
from src.jobs.job_types import JobType
from src.jobs.scheduler import JobScheduler
from src.models.task import Task


def test_job_scheduler_creates_task(clean_database):
    """Test that job scheduler creates a task in database"""
    scheduler = JobScheduler()

    task_id = scheduler.schedule_job(
        JobType.EVALUATE_LISTINGS, context={"listing_ids": ["listing_1", "listing_2"]}
    )

    assert task_id is not None

    with get_db_session() as db:
        task = db.query(Task).filter_by(id=task_id).first()
        assert task is not None
        assert task.task_type == "evaluate_listings"
        assert task.status == "pending"
        assert task.context["listing_ids"] == ["listing_1", "listing_2"]
