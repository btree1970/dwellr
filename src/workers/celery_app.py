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
            "sync-listings-hourly": {
                "task": "src.workers.tasks.scheduled_sync_task",
                "schedule": 3600.0,
            },
        },
        timezone="UTC",
    )

    return app
