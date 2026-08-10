"""Celery app configuration."""
from __future__ import annotations
from celery import Celery

from app.config import settings

celery_app = Celery(
    "hackroot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.jobs.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    broker_connection_retry_on_startup=True,
)
