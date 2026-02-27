"""
Celery App Configuration with Fallback Support

This module provides Celery configuration AND fallback logic to ensure
tasks run even when Celery workers are not available.
"""
from celery import Celery
import os
import sys
import logging
from typing import Callable, Any
from functools import wraps

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add project root to sys.path for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CELERY CONFIGURATION
# =============================================================================

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./intent_radar_v3.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
FALLBACK_BROKER_URL = f"sqla+{DATABASE_URL}"
RESULT_BACKEND = os.getenv("REDIS_URL", f"db+{DATABASE_URL}")

celery_app = Celery(
    "delta9",
    broker=REDIS_URL,
    backend=RESULT_BACKEND
)

# Test Redis connection and fallback if needed
try:
    import redis
    r = redis.from_url(REDIS_URL)
    r.ping()
    logger.info(f"✅ Redis connected at {REDIS_URL}")
except Exception as e:
    logger.warning(f"⚠️ Redis not available ({e}). Falling back to SQLite broker.")
    celery_app.conf.broker_url = FALLBACK_BROKER_URL

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Nairobi",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # Soft limit 25 minutes
    worker_prefetch_multiplier=1,  # Don't prefetch tasks
    task_acks_late=True,  # Acknowledge after task completes
    # Beat schedule for periodic tasks
    beat_schedule={
        "check-agents-every-minute": {
            "task": "run_all_agents",
            "schedule": 60.0,
        },
        "cleanup-every-12-hours": {
            "task": "cleanup_old_leads",
            "schedule": 43200.0,
        },
    },
)

# =============================================================================
# FALLBACK LOGIC - Critical for Production Reliability
# =============================================================================

class CeleryFallbackManager:
    """
    Manages task execution with automatic fallback to direct execution
    when Celery workers are not available.
    """
    
    def __init__(self):
        self.celery_available = None  # None = unknown, True/False = tested
        self.registered_tasks = {}
        
    def register_task(self, name: str, func: Callable) -> None:
        """Register a task function for fallback execution."""
        self.registered_tasks[name] = func
        logger.debug(f"Registered fallback task: {name}")
        
    def check_celery_available(self) -> bool:
        """Check if Celery workers are actually running."""
        if self.celery_available is not None:
            return self.celery_available
            
        try:
            # Try to ping Celery workers
            import socket
            # Check if we can connect to the broker
            if REDIS_URL.startswith("redis://"):
                import redis
                r = redis.from_url(REDIS_URL, socket_connect_timeout=2)
                r.ping()
            
            # If broker is up, assume workers might be available
            # We can't easily check workers without inspecting, so we'll
            # try to send a task and catch errors
            self.celery_available = True
            return True
            
        except Exception as e:
            logger.warning(f"Celery appears unavailable: {e}")
            self.celery_available = False
            return False
    
    def send_task(self, task_name: str, *args, **kwargs) -> Any:
        """
        Send a task to Celery with automatic fallback to direct execution.
        
        Usage:
            result = fallback_manager.send_task("run_agent_task", agent_id)
        """
        use_celery = kwargs.pop('_use_celery', True)
        
        # Try Celery first if requested
        if use_celery and self.check_celery_available():
            try:
                # Get the task from Celery
                task = celery_app.tasks.get(task_name)
                if task:
                    # Use delay() for async execution
                    result = task.delay(*args, **kwargs)
                    logger.debug(f"📨 Task '{task_name}' sent to Celery (ID: {result.id})")
                    return {"status": "queued", "task_id": result.id}
                else:
                    logger.warning(f"Task '{task_name}' not found in Celery registry")
            except Exception as e:
                logger.warning(f"Celery send failed for '{task_name}': {e}")
                self.celery_available = False
        
        # FALLBACK: Execute directly
        if task_name in self.registered_tasks:
            try:
                logger.info(f"🔄 Fallback: Executing '{task_name}' directly")
                func = self.registered_tasks[task_name]
                result = func(*args, **kwargs)
                return {"status": "completed_direct", "result": result}
            except Exception as e:
                logger.error(f"Direct execution failed for '{task_name}': {e}")
                return {"status": "error", "error": str(e)}
        else:
            logger.error(f"No fallback registered for task '{task_name}'")
            return {"status": "error", "error": f"Task {task_name} not registered"}

# Global fallback manager instance
fallback_manager = CeleryFallbackManager()


def register_task(name: str):
    """
    Decorator to register a function as both a Celery task AND a fallback task.
    
    Usage:
        @register_task("my_task")
        def my_task_function(arg1, arg2):
            # Do work
            return result
    """
    def decorator(func: Callable) -> Callable:
        # Register with fallback manager
        fallback_manager.register_task(name, func)
        
        # Also register as Celery task
        celery_task = celery_app.task(name=name)(func)
        
        # Attach fallback manager to the task for easy access
        celery_task.fallback = lambda *a, **kw: fallback_manager.send_task(name, *a, **kw)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # When called directly, try Celery first then fallback
            return fallback_manager.send_task(name, *args, **kwargs)
        
        # Store reference to celery task
        wrapper.celery_task = celery_task
        wrapper.delay = celery_task.delay
        wrapper.apply_async = celery_task.apply_async
        
        return wrapper
    return decorator


def send_task(task_name: str, *args, **kwargs) -> Any:
    """
    Send a task with automatic fallback.
    
    This is the MAIN entry point for task execution.
    It will try Celery first, and if that fails, execute directly.
    
    Usage:
        from app.core.celery_app import send_task
        
        # This will work even if Celery is down!
        result = send_task("run_agent_task", agent_id="123")
    """
    return fallback_manager.send_task(task_name, *args, **kwargs)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_agent_with_fallback(agent_id: str) -> dict:
    """
    Run an agent with automatic fallback to direct execution.
    
    Usage:
        result = run_agent_with_fallback("agent-uuid-here")
    """
    return send_task("run_agent_task", agent_id)


def ingest_leads_with_fallback(raw_results: list) -> dict:
    """
    Ingest leads with automatic fallback to direct execution.
    """
    return send_task("ingest_leads_task", raw_results)


def scrape_platform_with_fallback(platform: str, query: str, **kwargs) -> dict:
    """
    Scrape a platform with automatic fallback to direct execution.
    """
    return send_task("scrape_platform_task", platform, query, **kwargs)


# Export celery_app for backward compatibility
__all__ = [
    'celery_app',
    'fallback_manager',
    'register_task',
    'send_task',
    'run_agent_with_fallback',
    'ingest_leads_with_fallback',
    'scrape_platform_with_fallback',
]
