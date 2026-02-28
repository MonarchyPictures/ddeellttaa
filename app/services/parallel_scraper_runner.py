# app/services/parallel_scraper_runner.py
# ============================================================
# PARALLEL SCRAPER RUNNER — Clean Simple Implementation
# ============================================================

import asyncio
from typing import List, Dict, Any


async def run_scrapers_parallel(scrapers, query: str, location: str = "Kenya", hours: int = 24) -> List[Dict[str, Any]]:
    """
    Run all scrapers in parallel for a single query.
    
    Args:
        scrapers: List of scraper instances
        query: Search query string
        location: Location filter (default: Kenya)
        hours: Time window in hours (default: 24)
    
    Returns:
        Combined list of results from all scrapers
    """
    tasks = [
        scraper.search(query, location)
        for scraper in scrapers
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    clean = []

    for r in results:
        if isinstance(r, Exception):
            continue
        if isinstance(r, list):
            clean.extend(r)

    return clean
