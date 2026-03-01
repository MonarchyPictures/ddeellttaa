# app/api/routes/core.py
# ============================================================
# CORE API ROUTES — CACHE MANAGEMENT ONLY
# ============================================================
# Search endpoints moved to search.py (single source of truth)
# This file retains cache management utilities
# ============================================================

from fastapi import APIRouter
import logging

from app.services.search_cache import get_cache_stats, clear_cache

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    return get_cache_stats()


@router.post("/cache/clear")
async def cache_clear():
    """Clear the search cache."""
    clear_cache()
    return {"status": "ok", "message": "Cache cleared"}
