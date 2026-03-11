"""
DELTA-9 GUARDIAN API
Endpoints for system health monitoring and management
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

from app.core.system_guardian import get_guardian
from app.core.logging_system import get_recent_errors
from app.pipeline.lead_pipeline import get_pipeline

router = APIRouter(prefix="/api/guardian", tags=["System Guardian"])


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    services: Dict
    scrapers: List[Dict]
    stats: Dict


class ScraperStatus(BaseModel):
    """Scraper status"""
    id: str
    platform: str
    running: bool
    leads_collected: int
    errors: int
    health: str


class PipelineStats(BaseModel):
    """Pipeline statistics"""
    processed: int
    accepted: int
    rejected: int
    acceptance_rate: float
    by_reason: Dict[str, int]


@router.get("/health", response_model=HealthResponse)
async def get_system_health():
    """
    Get complete system health status
    
    Returns:
        Overall health status, service statuses, and statistics
    """
    guardian = get_guardian()
    pipeline = get_pipeline()
    
    health_summary = guardian.get_health_summary()
    scraper_status = guardian.get_scraper_status()
    pipeline_stats = pipeline.get_stats()
    
    return HealthResponse(
        status=health_summary['overall_status'],
        timestamp=datetime.utcnow().isoformat(),
        services={
            'guardian': health_summary,
            'pipeline': pipeline_stats
        },
        scrapers=scraper_status,
        stats={
            'checks_performed': health_summary.get('checks_performed', 0),
            'auto_recovers': health_summary.get('auto_recovers', 0),
            'alerts_sent': health_summary.get('alerts_sent', 0)
        }
    )


@router.get("/scrapers", response_model=List[ScraperStatus])
async def get_scraper_status():
    """
    Get status of all scrapers
    
    Returns:
        List of scraper statuses
    """
    guardian = get_guardian()
    return guardian.get_scraper_status()


@router.post("/scrapers/{scraper_id}/restart")
async def restart_scraper(scraper_id: str):
    """
    Manually restart a scraper
    
    Args:
        scraper_id: ID of the scraper to restart
        
    Returns:
        Success message
    """
    guardian = get_guardian()
    
    # Check if scraper exists
    health = guardian.get_service_health(scraper_id)
    if not health:
        raise HTTPException(status_code=404, detail=f"Scraper {scraper_id} not found")
    
    # Trigger restart
    guardian._restart_service(f"scraper:{scraper_id}")
    
    return {
        "success": True,
        "message": f"Scraper {scraper_id} restart initiated",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/pipeline/stats", response_model=PipelineStats)
async def get_pipeline_statistics():
    """
    Get pipeline processing statistics
    
    Returns:
        Pipeline stats including acceptance/rejection rates
    """
    pipeline = get_pipeline()
    stats = pipeline.get_stats()
    
    return PipelineStats(
        processed=stats['processed'],
        accepted=stats['accepted'],
        rejected=stats['rejected'],
        acceptance_rate=round(stats['acceptance_rate'], 2),
        by_reason={k.value: v for k, v in stats['by_reason'].items()}
    )


@router.get("/errors")
async def get_recent_errors_endpoint(minutes: int = 60):
    """
    Get recent errors from logs
    
    Args:
        minutes: Time window in minutes
        
    Returns:
        List of recent error log entries
    """
    errors = get_recent_errors(minutes)
    return {
        "count": len(errors),
        "errors": errors,
        "time_window_minutes": minutes
    }


@router.post("/cache/clear")
async def clear_system_cache():
    """
    Clear all system caches
    
    Returns:
        Success message
    """
    from app.services.deduplication_service import get_dedupe_service
    
    dedupe = get_dedupe_service()
    dedupe.clear_cache()
    
    return {
        "success": True,
        "message": "System caches cleared",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/logs/search")
async def search_logs_endpoint(query: str, limit: int = 100):
    """
    Search logs for specific query
    
    Args:
        query: Search string
        limit: Maximum results
        
    Returns:
        List of matching log entries
    """
    from app.core.logging_system import search_logs
    
    results = search_logs(query, limit=limit)
    
    return {
        "query": query,
        "results_count": len(results),
        "results": results
    }


# Health check endpoint for Railway/Docker
@router.get("/ping")
async def ping():
    """Simple ping for health checks"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
