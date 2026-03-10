"""
Worker Manager
Monitor and manage Celery workers
"""
from typing import Dict, List, Optional
from datetime import datetime

from celery import Celery
from celery.result import AsyncResult

from app.core.celery_config import get_celery_app


class WorkerManager:
    """
    Manages Celery workers and task monitoring
    """
    
    def __init__(self):
        self.celery: Celery = get_celery_app()
    
    def get_task_status(self, task_id: str) -> Dict:
        """Get the status of a specific task"""
        result = AsyncResult(task_id, app=self.celery)
        
        return {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "result": result.result if result.ready() and result.successful() else None,
            "traceback": result.traceback if result.ready() and not result.successful() else None,
        }
    
    def get_worker_stats(self) -> Dict:
        """Get worker statistics from Celery"""
        try:
            # Get inspect instance
            inspect = self.celery.control.inspect()
            
            # Get stats
            stats = inspect.stats()
            active = inspect.active()
            scheduled = inspect.scheduled()
            reserved = inspect.reserved()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "workers": list(stats.keys()) if stats else [],
                "worker_count": len(stats) if stats else 0,
                "active_tasks": self._count_tasks(active),
                "scheduled_tasks": self._count_tasks(scheduled),
                "reserved_tasks": self._count_tasks(reserved),
                "details": {
                    "stats": stats,
                    "active": active,
                    "scheduled": scheduled,
                    "reserved": reserved,
                } if stats else None,
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "workers": [],
                "worker_count": 0,
            }
    
    def _count_tasks(self, inspect_result) -> int:
        """Count total tasks from inspect result"""
        if not inspect_result:
            return 0
        return sum(len(tasks) for tasks in inspect_result.values())
    
    def revoke_task(self, task_id: str, terminate: bool = False) -> Dict:
        """Revoke/cancel a running task"""
        try:
            self.celery.control.revoke(task_id, terminate=terminate)
            return {
                "task_id": task_id,
                "action": "revoked",
                "terminated": terminate,
            }
        except Exception as e:
            return {
                "task_id": task_id,
                "error": str(e),
            }
    
    def purge_tasks(self) -> Dict:
        """Purge all pending tasks from queues"""
        try:
            # This only works for AMQP backends
            self.celery.control.purge()
            return {"status": "purged"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_queue_lengths(self) -> Dict:
        """Get the number of tasks in each queue"""
        try:
            inspect = self.celery.control.inspect()
            active_queues = inspect.active_queues()
            
            if not active_queues:
                return {"queues": {}, "total": 0}
            
            # Try to get queue lengths using redis
            from app.core.celery_config import get_redis_url
            import redis
            
            r = redis.from_url(get_redis_url())
            
            queues = {
                "default": r.llen("celery"),
                "scrapers": r.llen("celery:scrapers"),
                "high_priority": r.llen("celery:high_priority"),
                "low_priority": r.llen("celery:low_priority"),
            }
            
            return {
                "queues": queues,
                "total": sum(queues.values()),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def broadcast_ping(self) -> Dict:
        """Ping all workers to check connectivity"""
        try:
            inspect = self.celery.control.inspect()
            ping = inspect.ping()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "workers_online": list(ping.keys()) if ping else [],
                "worker_count": len(ping) if ping else 0,
            }
        except Exception as e:
            return {"error": str(e)}


# Singleton
_worker_manager = None


def get_worker_manager():
    """Get or create the worker manager"""
    global _worker_manager
    if _worker_manager is None:
        _worker_manager = WorkerManager()
    return _worker_manager
