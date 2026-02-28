# app/api/routes/core.py
# ============================================================
# CORE API ROUTES — Clean Single Pipeline
# ============================================================
# THE ONLY PIPELINE:
# generate_high_recall_queries() → run_scrapers_parallel() 
# → process_high_recall_results() → save_leads_to_db() → Return
# ============================================================

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

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


class SearchRequest(BaseModel):
    query: str
    location: Optional[str] = "Kenya"


def validate_location(location: str) -> str:
    """Strict Kenya-only validation."""
    if not location:
        return DEFAULT_LOCATION
    
    loc_lower = location.lower().strip()
    
    if any(allowed in loc_lower for allowed in ALLOWED_LOCATIONS):
        return location
    
    raise ValueError(f"Location '{location}' is not supported. Kenya only.")


@router.post("/search")
async def search_post(payload: SearchRequest, background_tasks: BackgroundTasks):
    """
    POST /api/search
    
    THE ONLY PIPELINE:
    1. generate_high_recall_queries() → 10 query variants
    2. run_scrapers_parallel() → 11 scrapers, max 3 concurrent
    3. process_high_recall_results() → Score ≥0.25, top 20
    4. save_leads_to_db() → Persist to database
    5. Return leads
    """
    query = payload.query.strip()
    
    # Validate location
    try:
        location = validate_location(payload.location)
    except ValueError as e:
        return {
            "results": [],
            "leads": [],
            "count": 0,
            "status": "error",
            "message": str(e)
        }
    
    logger.info(f"🔍 Search: '{query}' in '{location}'")
    
    # Step 1: Generate queries
    queries = generate_high_recall_queries(query, location)
    logger.info(f"Generated {len(queries)} queries")
    
    # Step 2: Run scrapers for each query
    all_results = []
    scraper_instances = list(SCRAPER_REGISTRY.values())
    logger.info(f"Using {len(scraper_instances)} scrapers")
    
    for q in queries:
        try:
            results = await run_scrapers_parallel(
                scrapers=scraper_instances,
                query=q,
                location=location,
                hours=24
            )
            all_results.extend(results)
            logger.info(f"Query '{q[:30]}...' returned {len(results)} results")
        except Exception as e:
            logger.error(f"Query failed: {e}")
            continue
    
    logger.info(f"Total raw results: {len(all_results)}")
    
    # Step 3: Score and filter
    leads = process_high_recall_results(all_results)
    logger.info(f"Processed {len(leads)} leads after scoring")
    
    # Step 4: Save to DB (background)
    if leads:
        background_tasks.add_task(save_leads_to_db, leads, query)
        logger.info(f"Queued {len(leads)} leads for DB save")
    
    # Step 5: Return
    return {
        "results": leads,
        "leads": leads,
        "count": len(leads),
        "status": "success" if leads else "no_results",
        "message": f"Found {len(leads)} leads" if leads else "No leads found",
        "query": query,
        "location": location
    }


@router.get("/search")
async def search_get(
    q: Optional[str] = None,
    query: Optional[str] = None,
    location: Optional[str] = "Kenya"
):
    """GET /api/search?q=pipes&location=Kenya"""
    search_query = q or query
    if not search_query:
        return {
            "results": [],
            "leads": [],
            "count": 0,
            "status": "error",
            "message": "No query provided"
        }
    
    # Reuse POST logic via SearchRequest
    from fastapi import Request
    return await search_post(
        SearchRequest(query=search_query, location=location),
        BackgroundTasks()
    )


@router.get("/categories")
async def get_categories():
    """Return supported categories."""
    return {
        "categories": {
            "general": {"keywords": ["buy", "looking for", "need"]},
            "vehicles": {"keywords": ["car", "toyota", "vehicle"]},
            "electronics": {"keywords": ["phone", "laptop", "iphone"]},
            "property": {"keywords": ["house", "apartment", "rent"]}
        }
    }


@router.get("/success/stats")
async def get_stats():
    """Dashboard statistics."""
    from app.db.database import SessionLocal
    from app.db import models
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        total = db.query(models.Lead).count()
        hot = db.query(models.Lead).filter(models.Lead.is_hot_lead == True).count()
        today = db.query(models.Lead).filter(
            models.Lead.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        return {
            "total_leads": total,
            "hot_leads": hot,
            "today_leads": today,
            "status": "ok"
        }
    except Exception as e:
        return {"total_leads": 0, "hot_leads": 0, "today_leads": 0, "status": "error"}
    finally:
        db.close()
