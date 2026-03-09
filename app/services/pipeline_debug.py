#!/usr/bin/env python3
"""
PIPELINE DEBUG SERVICE
======================
Provides detailed metrics and logging for pipeline debugging.
Set DEBUG_PIPELINE=true to enable.
"""

import os
import logging
import time
from typing import Dict, Any, List
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# Debug mode flag
DEBUG_MODE = os.getenv("DEBUG_PIPELINE", "false").lower() == "true"


class PipelineMetrics:
    """Collect metrics about pipeline execution."""
    
    def __init__(self):
        self.start_time = None
        self.stage_timings = {}
        self.stage_counts = {}
        self.errors = []
        
    def start(self):
        """Start timing the pipeline."""
        self.start_time = time.time()
        
    def record_stage(self, stage: str, count: int = 0, timing: float = None):
        """Record a pipeline stage."""
        if timing is None and stage in self.stage_timings:
            timing = time.time() - self.stage_timings[stage].get("start", time.time())
        
        self.stage_counts[stage] = count
        if stage not in self.stage_timings:
            self.stage_timings[stage] = {}
        self.stage_timings[stage]["end"] = time.time()
        self.stage_timings[stage]["count"] = count
        
    def start_stage(self, stage: str):
        """Start timing a stage."""
        if stage not in self.stage_timings:
            self.stage_timings[stage] = {}
        self.stage_timings[stage]["start"] = time.time()
        
    def record_error(self, stage: str, error: Exception):
        """Record an error."""
        self.errors.append({
            "stage": stage,
            "error": str(error),
            "type": type(error).__name__,
            "time": datetime.now().isoformat()
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of pipeline execution."""
        total_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            "total_time_seconds": round(total_time, 2),
            "stage_counts": self.stage_counts,
            "stage_timings": {
                stage: {
                    "duration": round(data.get("end", time.time()) - data.get("start", time.time()), 2)
                    if "end" in data else None,
                    "count": data.get("count", 0)
                }
                for stage, data in self.stage_timings.items()
            },
            "error_count": len(self.errors),
            "errors": self.errors[:5]  # First 5 errors
        }
        
    def log_summary(self):
        """Log the summary."""
        summary = self.get_summary()
        
        logger.warning("=" * 60)
        logger.warning("PIPELINE METRICS SUMMARY")
        logger.warning("=" * 60)
        logger.warning(f"Total time: {summary['total_time_seconds']}s")
        logger.warning(f"Errors: {summary['error_count']}")
        
        for stage, data in summary['stage_timings'].items():
            count = data.get('count', 0)
            duration = data.get('duration', 'N/A')
            logger.warning(f"  {stage}: {count} items ({duration}s)")
            
        if summary['errors']:
            logger.warning("\nErrors:")
            for err in summary['errors']:
                logger.warning(f"  [{err['stage']}] {err['type']}: {err['error']}")
        
        logger.warning("=" * 60)


# Global metrics instance
_pipeline_metrics = None


def start_pipeline_debug() -> PipelineMetrics:
    """Start pipeline debugging."""
    global _pipeline_metrics
    _pipeline_metrics = PipelineMetrics()
    _pipeline_metrics.start()
    
    if DEBUG_MODE:
        logger.warning("[DEBUG MODE] Pipeline debugging enabled")
        
    return _pipeline_metrics


def get_pipeline_metrics() -> PipelineMetrics:
    """Get current pipeline metrics."""
    return _pipeline_metrics


def debug_log(message: str, level: str = "warning"):
    """Log a debug message if debug mode is enabled."""
    if DEBUG_MODE:
        log_func = getattr(logger, level, logger.warning)
        log_func(f"[DEBUG] {message}")


def trace_stage(stage_name: str):
    """Decorator to trace a pipeline stage."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not DEBUG_MODE:
                return await func(*args, **kwargs)
                
            metrics = get_pipeline_metrics()
            if metrics:
                metrics.start_stage(stage_name)
                
            logger.warning(f"[STAGE START] {stage_name}")
            start = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                count = len(result) if isinstance(result, list) else 0
                
                if metrics:
                    metrics.record_stage(stage_name, count=count)
                    
                logger.warning(f"[STAGE END] {stage_name}: {count} items in {duration:.2f}s")
                return result
                
            except Exception as e:
                if metrics:
                    metrics.record_error(stage_name, e)
                logger.error(f"[STAGE ERROR] {stage_name}: {e}")
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not DEBUG_MODE:
                return func(*args, **kwargs)
                
            metrics = get_pipeline_metrics()
            if metrics:
                metrics.start_stage(stage_name)
                
            logger.warning(f"[STAGE START] {stage_name}")
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                count = len(result) if isinstance(result, list) else 0
                
                if metrics:
                    metrics.record_stage(stage_name, count=count)
                    
                logger.warning(f"[STAGE END] {stage_name}: {count} items in {duration:.2f}s")
                return result
                
            except Exception as e:
                if metrics:
                    metrics.record_error(stage_name, e)
                logger.error(f"[STAGE ERROR] {stage_name}: {e}")
                raise
                
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Need to import here to avoid circular import
import asyncio
