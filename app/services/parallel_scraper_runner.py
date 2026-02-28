"""
Production-Safe Parallel Scraper Runner

Features:
- Controlled concurrency (max 3 concurrent scrapers)
- Per-scraper timeout (25 seconds max)
- Exception isolation (one failure doesn't kill others)
- Deterministic logging
- Safe for Railway containers

Usage (ONLY from Celery worker - sync context):
    from app.services.parallel_scraper_runner import run_scrapers_parallel
    
    results = asyncio.run(
        run_scrapers_parallel(scraper_instances, agent.query, 24)
    )

⚠️ IMPORTANT:
    - Use ONLY from Celery worker (sync context)
    - NEVER use from FastAPI route (would conflict with existing event loop)
    - Celery worker = safe (can use asyncio.run())
    - FastAPI route = NOT safe (already has event loop)
"""
import os
import asyncio
import logging
import time
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Max concurrent scrapers - Safe for Railway containers
# Railway free tier: 3 (default)
# Railway paid tier: can increase to 4
# Never exceed 5 unless scaling container size
MAX_CONCURRENT_SCRAPERS = int(os.getenv("SCRAPER_CONCURRENCY", 3))

# Per-scraper timeout (seconds)
SCRAPER_TIMEOUT_SECONDS = 25

# Total scraping phase timeout (seconds)
TOTAL_PHASE_TIMEOUT_SECONDS = 60


async def run_scrapers_parallel(
    scrapers: List, 
    query: str, 
    location: str = "Kenya",
    hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Production-safe parallel execution of scrapers.
    
    Args:
        scrapers: List of scraper instances (must have .search() method)
        query: Search query string
        location: Location string (default: "Kenya")
        hours: Time window in hours (default: 24)
        
    Returns:
        Combined list of results from all scrapers
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPERS)
    
    logger.info(f"Running {len(scrapers)} scrapers in parallel (max concurrent: {MAX_CONCURRENT_SCRAPERS})")

    async def run_single(scraper):
        """Run a single scraper with controlled concurrency and timeout."""
        async with semaphore:
            scraper_name = scraper.__class__.__name__
            start_time = time.time()
            
            try:
                logger.info(f"🚀 START: {scraper_name}")
                
                # Hard timeout per scraper (prevents hanging)
                results = await asyncio.wait_for(
                    scraper.search(query, location),
                    timeout=SCRAPER_TIMEOUT_SECONDS
                )
                
                duration = round(time.time() - start_time, 2)
                logger.info(f"✅ DONE: {scraper_name} ({duration}s)")
                
                return results or []
                
            except asyncio.TimeoutError:
                logger.warning(f"⏱ TIMEOUT: {scraper_name}")
                return []
                
            except Exception as e:
                logger.error(f"❌ ERROR: {scraper_name} | {e}")
                return []

    # Create tasks for all scrapers
    tasks = [run_single(scraper) for scraper in scrapers]
    
    # Gather safely — exception isolation via run_single()
    try:
        # Optional: Add total phase timeout to prevent runaway jobs
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=False),
            timeout=TOTAL_PHASE_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        logger.error(f"⏱ TOTAL PHASE TIMEOUT: Entire scraping phase exceeded {TOTAL_PHASE_TIMEOUT_SECONDS}s")
        # Cancel pending tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        results = []

    # Combine results
    combined = []
    for r in results:
        if isinstance(r, list):
            combined.extend(r)
    
    logger.info(f"📊 TOTAL RESULTS: {len(combined)}")
    return combined


async def run_scrapers_safe(
    scraper_registry: Dict[str, Any],
    platforms: List[str],
    query: str,
    location: str = "Kenya",
    hours: int = 24
) -> List[Dict[str, Any]]:
    """
    High-level function to run scrapers from registry by platform names.
    
    Args:
        scraper_registry: Dict of platform_name -> scraper_instance
        platforms: List of platform names to run
        query: Search query
        location: Location string
        hours: Time window
        
    Returns:
        Combined list of results
    """
    scraper_instances = []
    for platform in platforms:
        if platform in scraper_registry:
            scraper_instances.append(scraper_registry[platform])
        else:
            logger.warning(f"Platform '{platform}' not found in registry")
    
    if not scraper_instances:
        logger.error("No scraper instances available")
        return []
    
    return await run_scrapers_parallel(
        scrapers=scraper_instances,
        query=query,
        location=location,
        hours=hours
    )
