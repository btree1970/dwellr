from datetime import timedelta

from celery import Celery

from src.config import settings


def create_celery_app() -> Celery:
    app = Celery("dwell_workers")

    app.conf.update(
        broker_url=settings.effective_celery_broker_url,
        result_backend=settings.effective_celery_result_backend,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        beat_schedule={
            "sync-listings": {
                "task": "src.workers.tasks.scheduled_sync_task",
                "schedule": timedelta(hours=6),
            },
            "evaluate-listings": {
                "task": "src.workers.tasks.scheduled_evaluation_task",
                "schedule": timedelta(hours=6),
            },
        },
        timezone="UTC",
    )

    return app
