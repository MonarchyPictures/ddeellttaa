# app/api/routes/search.py
"""
Delta9 v3 — UNIFIED SEARCH ENDPOINT
ONLY ONE: POST /api/search
Fast (3-8s) + Deep (background 20-60s)
Anti-429 Hardened
"""
import asyncio
import logging
from typing import List
from datetime import datetime, timezone
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.services.search_config import SEARCH_CONFIG, get_intent_threshold
from app.services.search_cache import get_cached, set_cache
from app.services.rate_limiter import get_system_health

# Import search services - THE ONLY PIPELINE
from app.services.search_service import search as search_service
from app.services.deep_search_service import run_deep_search, get_deep_search_status

# Import scraper registry
from app.scrapers.registry import SCRAPER_REGISTRY, get_active_scrapers

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])


# ============ Schemas ============
class SearchRequest(BaseModel):
    query: str
    location: str = "Kenya"


class SearchResponse(BaseModel):
    mode: str
    results: list
    count: int
    duration_seconds: float
    intent_threshold: float
    cached: bool
    deep_search_status: dict = None
    poll_url: str = None
    system_health: dict = None


# ============ MAIN ENDPOINT ============
@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    UNIFIED SEARCH — Kenya High Recall Pipeline
    
    Call Chain:
    Frontend → POST /api/search → search_service.search() 
    → generate_high_recall_queries() → run_scrapers_parallel()
    → process_high_recall_results() → Return leads
    
    Anti-429 Hardened: Max 2 concurrent scrapers, 8s timeout
    """
    start_time = datetime.now(timezone.utc)
    job_id = str(uuid4())[:8]
    
    logger.info(f"🔍 [{job_id}] Search: '{request.query}' in {request.location}")
    
    # THE ONLY PIPELINE: search_service.search()
    # This calls:
    #   1. generate_high_recall_queries()
    #   2. run_scrapers_parallel()
    #   3. process_high_recall_results()
    result = await search_service(
        query=request.query,
        location=request.location
    )
    
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(f"✓ [{job_id}] Complete: {result['count']} leads in {duration:.1f}s")
    logger.warning(f"[API DEBUG] result['count']={result['count']}, result['leads'] length={len(result.get('leads', []))}")
    
    # DEEP MODE — Queue background (optional enhancement)
    if result['count'] < 5:
        asyncio.create_task(
            run_deep_search(
                query=request.query,
                location=request.location,
                all_scrapers=get_active_scrapers(),
                job_id=job_id
            )
        )
        logger.info(f"🔄 [{job_id}] Deep search queued (background)")
        deep_status = {
            "job_id": job_id,
            "status": "running",
            "poll_url": f"/api/search/deep-status?job_id={job_id}",
            "expected_duration_seconds": 30
        }
        poll_url = f"/api/search/deep-status?job_id={job_id}"
    else:
        deep_status = None
        poll_url = None
    
    return SearchResponse(
        mode="high_recall_pipeline",
        results=result["leads"],
        count=result["count"],
        duration_seconds=duration,
        intent_threshold=get_intent_threshold("fast"),
        cached=result.get("mode") == "cache",
        deep_search_status=deep_status,
        poll_url=poll_url,
        system_health=get_system_health()
    )


# ============ STATUS ENDPOINT ============
@router.get("/search/deep-status")
async def deep_search_status(job_id: str):
    """Check deep search status."""
    status = get_deep_search_status(job_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    return status


# ============ HEALTH ENDPOINT ============
@router.get("/search/health")
async def search_health():
    """System health check."""
    from app.services.rate_limiter import get_system_health
    return get_system_health()
