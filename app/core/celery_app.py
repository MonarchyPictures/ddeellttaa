"""
Celery App Configuration - Production Only

Redis is REQUIRED. No SQLite fallback. No localhost fallback.
Production must fail loudly if Redis is missing.
"""
from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise RuntimeError(
        "REDIS_URL is not set. "
        "Redis is required in production. "
        "Add Redis plugin in Railway and set REDIS_URL environment variable."
    )

# Main Celery app - named 'celery' for Railway commands:
#   celery -A app.core.celery_app.celery worker --loglevel=info
#   celery -A app.core.celery_app.celery beat --loglevel=info
celery = Celery(
    "delta9",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # Soft limit 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        "check-agents-every-minute": {
            "task": "app.core.celery_worker.run_all_agents",
            "schedule": 60.0,
        },
        "cleanup-every-12-hours": {
            "task": "app.core.celery_worker.cleanup_old_leads",
            "schedule": 43200.0,
        },
    },
)

# Backward compatibility alias
celery_app = celery

__all__ = ['celery', 'celery_app']
