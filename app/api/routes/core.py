# app/api/routes/core.py
# ============================================================
# CORE API ROUTES — Kenya High Recall Pipeline
# VERSION: 2026-02-27-HIGH-RECALL-V2
# CACHE_BUSTER: FORCE_REBUILD_20260227_001
# ============================================================

import logging
import asyncio
from fastapi import APIRouter, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.kenya_high_recall_pipeline import (
    generate_high_recall_queries,
    process_high_recall_results
)
from app.services.parallel_scraper_runner import run_scrapers_parallel
from app.scrapers.registry import SCRAPER_REGISTRY
from app.services.lead_storage import save_leads_to_db
from app.config.runtime import DEFAULT_LOCATION, ALLOWED_LOCATIONS

logger = logging.getLogger(__name__)
router = APIRouter()

# Startup verification log
logger.info("✅ CORE ROUTES LOADED - HIGH RECALL PIPELINE V2")


class SearchRequest(BaseModel):
    query: str
    location: Optional[str] = "Kenya"
    include_all: Optional[bool] = False
    include_telegram: Optional[bool] = True
    telegram_hours_back: Optional[int] = 24
    min_score: Optional[float] = 0.0


def validate_location(location: str) -> str:
    """
    STRICT KENYA-ONLY VALIDATION.
    Rejects any location that is not explicitly Kenya or a Kenyan city/region.
    """
    if not location:
        return DEFAULT_LOCATION
    
    loc_lower = location.lower().strip()
    
    # Strict check: location MUST contain an allowed Kenya location
    if any(allowed in loc_lower for allowed in ALLOWED_LOCATIONS):
        return location
    
    # If location is not Kenya-related, reject it
    raise ValueError(f"Location '{location}' is not supported. This system only supports Kenya locations: {', '.join(ALLOWED_LOCATIONS[:10])}...")


async def run_high_recall_search(query: str, location: str) -> List[Dict[str, Any]]:
    """
    High recall search pipeline:
    1. Generate multiple broad queries (product + location variants)
    2. Run all scrapers in parallel for each query
    3. Deduplicate by URL
    4. Score and filter results
    
    This replaces the strict 'site:t.me + exact buyer phrase' approach
    with broad queries scored by intent classification.
    """
    logger.info(f"🔍 High Recall Search: '{query}' in '{location}'")
    
    # Step 1: Generate high recall queries
    queries = generate_high_recall_queries(query, location)
    logger.info(f"Generated {len(queries)} high-recall queries: {queries}")
    
    # Step 2: Get all available scrapers
    scraper_instances = list(SCRAPER_REGISTRY.values())
    logger.info(f"Using {len(scraper_instances)} scrapers: {list(SCRAPER_REGISTRY.keys())}")
    
    all_raw_results = []
    
    # Step 3: Run each query through parallel scrapers
    for q in queries:
        logger.info(f"Running query: '{q}'")
        try:
            results = await run_scrapers_parallel(
                scrapers=scraper_instances,
                query=q,
                location=location,
                hours=24
            )
            logger.info(f"Query '{q}' returned {len(results)} results")
            all_raw_results.extend(results)
        except Exception as e:
            logger.error(f"Query '{q}' failed: {e}")
            continue
    
    logger.info(f"Total raw results before dedup: {len(all_raw_results)}")
    
    # Step 4: Deduplicate by URL
    seen = set()
    deduped = []
    for r in all_raw_results:
        url = r.get("url") or r.get("link") or r.get("source_url")
        if url:
            if url not in seen:
                seen.add(url)
                deduped.append(r)
        else:
            # Keep items without URL (might be valid)
            deduped.append(r)
    
    logger.info(f"Results after dedup: {len(deduped)}")
    
    # Step 5: Process through high recall pipeline (score & filter)
    leads = process_high_recall_results(deduped)
    logger.info(f"Final leads after scoring: {len(leads)}")
    
    return leads


@router.post("/search")
async def search_post(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    POST /api/search
    Kenya High Recall Pipeline:
    - Generates multiple broad queries (e.g., "tires Kenya", "tires Kenya price")
    - Runs all scrapers in parallel
    - Scores intent with 0.25 threshold (catches informal buyer language)
    - Returns deduplicated, ranked leads
    """
    import os
    import traceback
    
    logger.info("="*60)
    logger.info("[BACKEND ROUTE] /api/search POST HIT")
    logger.info(f"[BACKEND ROUTE] Request: {request.model_dump()}")
    
    query = request.query.strip()
    
    # Validate location - Kenya only
    try:
        location = validate_location(request.location)
    except ValueError as e:
        logger.warning(f"🚫 Kenya-Only Policy: {e}")
        return {
            "results": [], "leads": [],
            "metrics": {"error": str(e), "kenya_only": True},
            "message": str(e), "count": 0,
            "status": "kenya_only_policy"
        }

    logger.info(f"🔍 Search: '{query}' in '{location}'")
    
    # ENV CHECK
    logger.info(f"HIGH_RECALL_MODE: {os.getenv('HIGH_RECALL_MODE', 'NOT SET')}")
    logger.info(f"SCRAPER_CONCURRENCY: {os.getenv('SCRAPER_CONCURRENCY', '3')}")

    try:
        # Use Kenya High Recall Pipeline
        leads = await run_high_recall_search(query, location)
        
        logger.info(f"[BACKEND ROUTE] Result: {len(leads)} leads")
        logger.info("="*60)

        # Background Save
        if leads:
            background_tasks.add_task(save_leads_to_db, leads, query)

        # DEBUG: Log final response size
        print(f"[API RESPONSE DEBUG] Returning {len(leads)} leads to frontend for query '{query}'")
        logger.info(f"[API RESPONSE DEBUG] Response payload size: {len(leads)} leads")
        
        return {
            "results": leads,
            "leads": leads,
            "count": len(leads),
            "status": "success" if leads else "no_results",
            "message": f"Found {len(leads)} leads" if leads else "No leads found. Try different keywords.",
            "query": query,
            "location": location,
            "mode": "high_recall_pipeline",
            "debug_info": {
                "scraper_count": len(SCRAPER_REGISTRY),
                "scraper_names": list(SCRAPER_REGISTRY.keys())
            }
        }
        
    except Exception as e:
        logger.error(f"[BACKEND ROUTE] ❌ ERROR: {e}")
        logger.error(f"[BACKEND ROUTE] TRACEBACK: {traceback.format_exc()}")
        return {
            "results": [], "leads": [],
            "metrics": {"error": str(e)},
            "message": f"Search failed: {str(e)}",
            "count": 0,
            "status": "error"
        }


@router.get("/search")
async def search_get(
    background_tasks: BackgroundTasks,
    q: str = Query(None),
    query: str = Query(None),
    location: str = Query("Kenya"),
    include_all: bool = Query(False),
    include_telegram: bool = Query(True),
    telegram_hours_back: int = Query(24),
    min_score: float = Query(0.0)
):
    """
    GET /api/search?q=concrete+mixer&location=Nairobi
    
    Same as POST but via URL parameters.
    Uses Kenya High Recall Pipeline.
    """
    search_query = q or query
    if not search_query:
        return {
            "results": [], "leads": [],
            "message": "No query provided", "count": 0,
            "status": "no_query"
        }

    # Validate location - Kenya only
    try:
        location = validate_location(location)
    except ValueError as e:
        logger.warning(f"🚫 Kenya-Only Policy: {e}")
        return {
            "results": [], "leads": [],
            "metrics": {"error": str(e), "kenya_only": True},
            "message": str(e), "count": 0,
            "status": "kenya_only_policy"
        }

    try:
        # Use Kenya High Recall Pipeline
        leads = await run_high_recall_search(search_query.strip(), location)

        # Background Save
        if leads:
            background_tasks.add_task(save_leads_to_db, leads, search_query)

        return {
            "results": leads,
            "leads": leads,
            "count": len(leads),
            "status": "success" if leads else "no_results",
            "message": f"Found {len(leads)} leads" if leads else "No leads found. Try different keywords.",
            "query": search_query,
            "location": location,
            "mode": "high_recall_pipeline"
        }
        
    except Exception as e:
        logger.error(f"[BACKEND ROUTE] ❌ ERROR: {e}")
        return {
            "results": [], "leads": [],
            "metrics": {"error": str(e)},
            "message": f"Search failed: {str(e)}",
            "count": 0,
            "status": "error"
        }


@router.get("/categories")
async def get_categories():
    """
    GET /api/categories
    Returns supported product categories and their keywords.
    """
    from app.engine.query_intelligence import CATEGORY_PATTERNS
    
    categories = {}
    for name, config in CATEGORY_PATTERNS.items():
        categories[name] = {
            "keywords": config["keywords"][:10],
            "platforms": config.get("platforms", []),
            "example_phrases": config["buyer_phrases"][:3]
        }
    
    return {"categories": categories}


@router.get("/success/stats")
async def get_stats():
    """Dashboard statistics."""
    from app.db.database import SessionLocal
    
    try:
        from app.db import models
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        try:
            total = db.query(models.Lead).count()
            hot = db.query(models.Lead).filter(models.Lead.is_hot_lead == 1).count()
            today = db.query(models.Lead).filter(
                models.Lead.created_at >= datetime.now() - timedelta(hours=24)
            ).count()
            return {
                "total_leads": total,
                "hot_leads": hot,
                "today_leads": today,
                "status": "ok"
            }
        finally:
            db.close()
    except Exception as e:
        return {"total_leads": 0, "hot_leads": 0, "today_leads": 0, "status": "error"}
