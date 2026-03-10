"""
Celery Configuration
Distributed Task Queue for Delta-9 Scraper Workers
"""
import os
from celery import Celery
from kombu import Queue, Exchange


def get_redis_url():
    """Get Redis URL from environment or default"""
    # Railway provides REDIS_URL
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis_url
    
    # Default local Redis
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_password = os.getenv("REDIS_PASSWORD", "")
    
    if redis_password:
        return f"redis://:{redis_password}@{redis_host}:{redis_port}/0"
    return f"redis://{redis_host}:{redis_port}/0"


# Create Celery app
celery_app = Celery(
    "delta9",
    broker=get_redis_url(),
    backend=get_redis_url(),
    include=[
        "app.tasks.scraper_tasks",
        "app.tasks.lead_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Soft limit at 4 minutes
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    
    # Worker settings
    worker_prefetch_multiplier=4,  # Prefetch 4 tasks per worker
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    
    # Queue configuration
    task_default_queue="default",
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("scrapers", Exchange("scrapers"), routing_key="scraper.#"),
        Queue("high_priority", Exchange("high_priority"), routing_key="high.#"),
        Queue("low_priority", Exchange("low_priority"), routing_key="low.#"),
    ),
    
    # Routing
    task_routes={
        "app.tasks.scraper_tasks.scrape_reddit": {"queue": "scrapers"},
        "app.tasks.scraper_tasks.scrape_twitter": {"queue": "scrapers"},
        "app.tasks.scraper_tasks.scrape_forum": {"queue": "scrapers"},
        "app.tasks.scraper_tasks.scrape_all_sources": {"queue": "high_priority"},
    },
    
    # Rate limiting
    task_annotations={
        "app.tasks.scraper_tasks.scrape_reddit": {
            "rate_limit": "10/m",  # 10 requests per minute
        },
        "app.tasks.scraper_tasks.scrape_twitter": {
            "rate_limit": "10/m",
        },
    },
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_heartbeat=30,
    
    # Visibility timeout (tasks must complete within this time)
    broker_transport_options={
        "visibility_timeout": 43200,  # 12 hours
    },
)


def get_celery_app():
    """Get the configured Celery app"""
    return celery_app


# Health check for Celery/Redis
def check_celery_health():
    """Check if Celery and Redis are connected"""
    try:
        # Try to ping Redis through Celery's connection
        with celery_app.connection() as conn:
            conn.ensure_connection(max_retries=1)
        return {"status": "ok", "redis": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
