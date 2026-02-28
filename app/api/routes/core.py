# app/api/routes/core.py
# ============================================================
# CORE API ROUTES — Uses the new Search Engine
# ============================================================

import logging
from fastapi import APIRouter, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from app.engine.search_engine import SEARCH_ENGINE
from app.services.lead_storage import save_leads_to_db
from app.config.runtime import DEFAULT_LOCATION, ALLOWED_LOCATIONS

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.post("/search")
async def search_post(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    POST /api/search
    Finds buyers across web + Telegram.
    KENYA-ONLY: Only Kenyan locations are supported.
    """
    import os
    import traceback
    
    # BACKEND ROUTE TRACE
    print("="*60)
    print("[BACKEND ROUTE] /api/search HIT", flush=True)
    print("[BACKEND ROUTE] Request:", request.model_dump(), flush=True)
    
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
    print(f"[BACKEND ROUTE] Query: '{query}' | Location: '{location}'")
    
    # ENV CHECK
    print("[BACKEND ROUTE] ENV CHECK:")
    print(f"  SERPAPI_API_KEY: {bool(os.getenv('SERPAPI_API_KEY'))}")
    print(f"  GOOGLE_CSE_API_KEY: {bool(os.getenv('GOOGLE_CSE_API_KEY'))}")
    print(f"  REDIS_URL: {bool(os.getenv('REDIS_URL'))}")
    print(f"  HIGH_RECALL_MODE: {os.getenv('HIGH_RECALL_MODE', 'NOT SET')}")

    try:
        # Use enhanced search with Telegram
        print("[BACKEND ROUTE] Calling SEARCH_ENGINE.search_with_telegram...")
        result = await SEARCH_ENGINE.search_with_telegram(
            query=query,
            location=location,
            include_telegram=request.include_telegram,
            telegram_hours_back=request.telegram_hours_back,
            include_all=request.include_all,
            min_score=request.min_score
        )
        
        print(f"[BACKEND ROUTE] Result received: {len(result.get('leads', []))} leads")
        print(f"[BACKEND ROUTE] Result status: {result.get('status')}")
        print("="*60)

        # Background Save
        if result.get("leads"):
            background_tasks.add_task(save_leads_to_db, result["leads"], query)

        return result
    except Exception as e:
        print(f"[BACKEND ROUTE] ❌ ERROR: {e}")
        print(f"[BACKEND ROUTE] TRACEBACK: {traceback.format_exc()}")
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
    GET /api/search?q=2br+kileleshwa&location=Kenya
    
    Same as POST but via URL parameters.
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

    result = await SEARCH_ENGINE.search_with_telegram(
        query=search_query.strip(),
        location=location,
        include_all=include_all,
        include_telegram=include_telegram,
        telegram_hours_back=telegram_hours_back,
        min_score=min_score
    )

    # Background Save
    if result.get("leads"):
        background_tasks.add_task(save_leads_to_db, result["leads"], search_query)

    return result


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
