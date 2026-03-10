"""Core configuration"""
from .celery_config import celery_app, get_redis_url

__all__ = ["celery_app", "get_redis_url"]
