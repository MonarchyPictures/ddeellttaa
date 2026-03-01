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

from app.scrapers.registry import get_active_scrapers_sorted
from app.services.kenya_high_recall_pipeline import (
    generate_high_recall_queries,
    process_high_recall_results
)
from app.services.parallel_scraper_runner import run_scrapers_parallel
from app.core.cache import get_cached, set_cached

logger = logging.getLogger(__name__)


async def search(query: str, location: str = "Kenya") -> Dict[str, Any]:
    print(f"[SEARCH START] query='{query}', location='{location}'")
    logger.info(f"🔍 Search: '{query}' in '{location}'")

    # Check cache (wrapped for safety - cache failures shouldn't break search)
    try:
        cached = get_cached(query, location)
        if cached:
            return {
                "results": cached,
                "leads": cached,
                "count": len(cached),
                "status": "success",
                "mode": "cache",
            }
    except Exception as e:
        logger.error(f"Cache read failed (proceeding without cache): {e}")
        cached = None

    try:
        queries = generate_high_recall_queries(query, location)
        logger.warning(f"[SEARCH DEBUG] Generated {len(queries)} queries: {queries}")

        if not queries:
            logger.error("[ERROR] No queries generated")
            return {
                "results": [],
                "leads": [],
                "count": 0,
                "status": "error",
                "message": "No queries generated"
            }

        scraper_instances = get_active_scrapers_sorted()
        print(f"[SEARCH DEBUG] Got {len(scraper_instances)} scrapers: {[type(s).__name__ for s in scraper_instances]}")

        if not scraper_instances:
            logger.error("[ERROR] No active scrapers found")
            return {
                "results": [],
                "leads": [],
                "count": 0,
                "status": "error",
                "message": "No scrapers active"
            }

        logger.info(f"[DEBUG] Using {len(scraper_instances)} scrapers, {len(queries)} queries")

        # Run all queries in parallel (individual scrapers have 8s timeout)
        query_tasks = [
            run_scrapers_parallel(scraper_instances, q, location, 24)
            for q in queries[:2]  # LIMIT: max 2 queries
        ]
        
        # Gather all results (no overall timeout - let individual scrapers timeout)
        query_results = await asyncio.gather(*query_tasks, return_exceptions=True)

        # Flatten results (skip exceptions)
        all_raw_results = []
        logger.warning(f"[SEARCH DEBUG] query_results count: {len(query_results)}")
        for i, r in enumerate(query_results):
            logger.warning(f"[SEARCH DEBUG] query_result[{i}]: type={type(r)}, is_list={isinstance(r, list)}")
            if isinstance(r, list):
                logger.warning(f"[SEARCH DEBUG] query_result[{i}] length: {len(r)}")
                all_raw_results.extend(r)
            elif isinstance(r, Exception):
                logger.warning(f"[DEBUG] Query failed: {r}")

        logger.warning(f"[SEARCH DEBUG] Total raw results: {len(all_raw_results)}")
        if all_raw_results:
            logger.warning(f"[SEARCH DEBUG] Sample raw: {str(all_raw_results[0])[:200]}")

        try:
            print(f"[DEBUG] Calling process_high_recall_results with {len(all_raw_results)} raw results")
            leads = process_high_recall_results(all_raw_results)
            print(f"[DEBUG] process_high_recall_results returned {len(leads)} leads")
            logger.warning(f"[SEARCH DEBUG] process_high_recall_results returned {len(leads)} leads")
        except Exception as e:
            print(f"[DEBUG] process_high_recall_results FAILED: {e}")
            logger.error(f"[SEARCH DEBUG] process_high_recall_results FAILED: {e}")
            leads = []

        # Ensure minimum display count
        DISPLAY_MIN = 4
        if len(leads) > DISPLAY_MIN:
            leads = leads[:DISPLAY_MIN]

        logger.warning(f"[SEARCH DEBUG] Leads after scoring: {len(leads)}, type: {type(leads)}")
        if leads:
            logger.warning(f"[SEARCH DEBUG] First lead: {leads[0] if isinstance(leads, list) else 'not list'}")

        # Cache results (wrapped for safety)
        if leads:
            try:
                set_cached(query, leads, location)
            except Exception as e:
                logger.error(f"Cache write failed (results still returned): {e}")

        result = {
            "results": leads,
            "leads": leads,
            "count": len(leads),
            "status": "success" if leads else "no_results",
            "mode": "high_recall_pipeline"
        }
        logger.warning(f"[SEARCH DEBUG] Returning result with count: {result['count']}")
        return result

    except Exception as e:
        logger.exception("Search crashed")
        return {
            "results": [],
            "leads": [],
            "count": 0,
            "status": "error",
            "message": str(e)
        }


# Backward compatible alias
async def run_search(query: str, location: str = "Kenya") -> List[Dict[str, Any]]:
    """Backward compatible search function."""
    result = await search(query, location)
    return result.get("leads", [])
