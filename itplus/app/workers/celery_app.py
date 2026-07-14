"""Celery application for async document indexing."""

from celery import Celery

from itplus.app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "itplus",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    include=["itplus.app.workers.index_document"],
)

# Ensure task modules are imported so @celery_app.task decorators register.
import itplus.app.workers.index_document  # noqa: F401, E402
