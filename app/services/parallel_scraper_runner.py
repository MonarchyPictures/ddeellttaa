# app/services/parallel_scraper_runner.py
# ============================================================
# PARALLEL SCRAPER RUNNER — Production-Grade Concurrency
# ============================================================
# Rule #1: Limit concurrency with semaphore
# Prevents memory explosion, CPU starvation, 429 storms
# ============================================================

import asyncio
import os
from typing import List, Dict, Any

# Production tuning: 4 concurrent max (prevents Railway crash)
MAX_CONCURRENT_SCRAPERS = int(os.getenv("SCRAPER_CONCURRENCY", 4))


async def run_scrapers_parallel(scrapers, query: str, location: str = "Kenya", hours: int = 24) -> List[Dict[str, Any]]:
    """
    Run all scrapers in parallel with controlled concurrency.
    
    Without semaphore: 11 scrapers × 10 queries = 110 concurrent tasks → Railway crash
    With semaphore: Controlled 4 concurrent → Stable performance
    
    Args:
        scrapers: List of scraper instances
        query: Search query string
        location: Location filter (default: Kenya)
        hours: Time window in hours (default: 24)
    
    Returns:
        Combined list of results from all scrapers
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPERS)

    async def run_with_limit(scraper):
        """Run single scraper with semaphore control."""
        async with semaphore:
            try:
                return await scraper.search(query, location)
            except Exception:
                # Silent fail - one scraper error doesn't kill others
                return []

    # Create tasks for all scrapers
    tasks = [run_with_limit(scraper) for scraper in scrapers]

    # Run with controlled concurrency
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Combine results
    combined = []
    for r in results:
        if isinstance(r, list):
            combined.extend(r)

    return combined
