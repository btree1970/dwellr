"""Basic Celery application setup"""

from celery import Celery

from src.config import settings


def create_celery_app() -> Celery:
    """Create and configure Celery app"""
    app = Celery("dwell_workers")

    # Basic configuration
    app.conf.update(
        broker_url=settings.effective_celery_broker_url,
        result_backend=settings.effective_celery_result_backend,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
    )

    return app


# Global celery app instance
celery_app = create_celery_app()
