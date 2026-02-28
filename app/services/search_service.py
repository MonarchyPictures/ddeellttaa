# app/services/search_service.py
# ============================================================
# SEARCH SERVICE — Clean High Recall Pipeline
# ============================================================
# Uses only:
# 1. generate_high_recall_queries()
# 2. run_scrapers_parallel()
# 3. process_high_recall_results()
#
# NO SEARCH_ENGINE.
# NO BUYER_CLASSIFIER.
# NO legacy engine.
# ============================================================

import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.scrapers.registry import get_active_scrapers_sorted, SCRAPER_REGISTRY
from app.services.kenya_high_recall_pipeline import (
    generate_high_recall_queries,
    process_high_recall_results
)
from app.services.parallel_scraper_runner import run_scrapers_parallel
from app.core.cache import get_cached, set_cached

logger = logging.getLogger(__name__)


async def search(query: str, location: str = "Kenya") -> Dict[str, Any]:
    """
    Main search function using clean high-recall pipeline.
    
    Pipeline:
    1. Check cache
    2. Generate high-recall queries
    3. Run scrapers in parallel
    4. Score and filter results
    5. Return leads
    """
    logger.info(f"🔍 Search: '{query}' in '{location}'")
    
    # Check cache first
    cached = get_cached(query, location)
    if cached:
        logger.info(f"⚡ Cache hit for '{query}'")
        return {
            "results": cached,
            "leads": cached,
            "count": len(cached),
            "status": "success",
            "mode": "cache",
            "message": f"Found {len(cached)} leads (from cache)"
        }
    
    try:
        # Step 1: Generate high-recall queries
        queries = generate_high_recall_queries(query, location)
        logger.info(f"Generated {len(queries)} queries: {queries}")
        
        # Step 2: Get all scrapers
        scraper_instances = list(SCRAPER_REGISTRY.values())
        logger.info(f"Using {len(scraper_instances)} scrapers")
        
        # Step 3: Run scrapers for each query
        all_raw_results = []
        for q in queries:
            try:
                results = await run_scrapers_parallel(
                    scrapers=scraper_instances,
                    query=q,
                    location=location,
                    hours=24
                )
                all_raw_results.extend(results)
                logger.info(f"Query '{q}': {len(results)} results")
            except Exception as e:
                logger.error(f"Query '{q}' failed: {e}")
                continue
        
        logger.info(f"Total raw results: {len(all_raw_results)}")
        
        # Step 4: Score and filter
        leads = process_high_recall_results(all_raw_results)
        logger.info(f"Processed {len(leads)} leads after scoring")
        
        # Cache results
        if leads:
            set_cached(query, leads, location)
        
        return {
            "results": leads,
            "leads": leads,
            "count": len(leads),
            "status": "success" if leads else "no_results",
            "mode": "high_recall_pipeline",
            "message": f"Found {len(leads)} leads" if leads else "No leads found",
            "total_signals_captured": len(all_raw_results),
            "total_signals_scanned": len(all_raw_results),
            "buyers_found": len(leads)
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {
            "results": [],
            "leads": [],
            "count": 0,
            "status": "error",
            "mode": "error",
            "message": f"Search failed: {str(e)}"
        }


# Backward compatible alias
async def run_search(query: str, location: str = "Kenya") -> List[Dict[str, Any]]:
    """Backward compatible search function."""
    result = await search(query, location)
    return result.get("leads", [])
