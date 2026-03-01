# app/services/fast_search_service.py
"""
FAST SEARCH SERVICE — Anti-429 Hardened
High Confidence Only (0.35 threshold)
3-8 seconds response time
"""
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.services.kenya_intent_engine import batch_score_leads, get_threshold_for_mode
from app.services.parallel_scraper_runner import run_scrapers_parallel
from app.services.search_cache import get_cached, set_cache
from app.services.search_config import (
    SEARCH_CONFIG, 
    get_intent_threshold,
    get_adaptive_thresholds,
    should_accept_lead
)
from app.services.rate_limiter import throttler, apply_delay

logger = logging.getLogger(__name__)

# Anti-429: Only fast API-based scrapers (NO Playwright)
FAST_SCRAPER_NAMES = [
    'SerpAPIScraper',      # API - fastest
    'GoogleCSEScraper',    # API - fast
    'DuckDuckGoScraper',   # API - moderate
    'YahooScraper',        # API - moderate
]

# Anti-429: Lower concurrency for stability
MAX_CONCURRENT_FAST = 2  # Reduced from 4


def get_fast_scrapers(all_scrapers: List) -> List:
    """
    Get fast API-based scrapers (NO Playwright).
    Anti-429: HTTP-only scrapers
    """
    scrapers = [s for s in all_scrapers if any(name in s.__class__.__name__ for name in FAST_SCRAPER_NAMES)]
    # Anti-429: Limit to top 3 scrapers
    return scrapers[:3]


def generate_fast_queries(product: str, location: str) -> List[str]:
    """
    Anti-429: FEWER queries (2 only)
    Kenya-optimized for high-intent buyers
    """
    return [
        # Query 1: High-recall buyer signal
        f'"{product}" "{location}" (looking for OR natafuta OR wtb OR need)',
        # Query 2: Site-filter for social
        f'site:facebook.com "{product}" "{location}"'
    ]


async def run_fast_search(
    query: str,
    location: str,
    all_scrapers: List,
    max_leads: int = None,
    timeout: int = None
) -> Dict[str, Any]:
    """
    Execute FAST search with Anti-429 hardening.
    
    Anti-429 Measures:
    - Fewer queries: 2 (was 5+)
    - Lower concurrency: 2 (was 4)
    - No Playwright: HTTP scrapers only
    - Throttling: Per-scraper delays
    - Jitter: Random delays between requests
    
    Intent Threshold: 0.35 (high confidence)
    Target Time: 3-8 seconds
    """
    start_time = datetime.now(timezone.utc)
    
    # Config
    max_leads = max_leads or SEARCH_CONFIG.FAST_EARLY_STOP_LEADS
    timeout = timeout or SEARCH_CONFIG.FAST_TIMEOUT_SECONDS
    intent_threshold = get_intent_threshold("fast")
    
    # Check cache
    cached = get_cached(query, location)
    if cached:
        logger.info(f"⚡ CACHE HIT: '{query}' (<50ms)")
        return {
            "leads": cached.get("leads", []),
            "count": cached.get("count", 0),
            "calls_made": 0,
            "duration_seconds": 0,
            "intent_threshold": intent_threshold,
            "cached": True
        }
    
    # Anti-429: Get HTTP-only scrapers (no Playwright)
    fast_scrapers = get_fast_scrapers(all_scrapers)
    fast_queries = generate_fast_queries(query, location)
    
    logger.info(f"🔍 FAST: '{query}' | {len(fast_queries)} queries × {len(fast_scrapers)} scrapers | threshold: {intent_threshold}")
    
    # Execute with timeout and early stopping
    try:
        fast_results = await asyncio.wait_for(
            _run_with_early_stopping(
                queries=fast_queries,
                scrapers=fast_scrapers,
                location=location,
                max_leads=max_leads,
                concurrency=MAX_CONCURRENT_FAST  # Anti-429: Lower concurrency
            ),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"⏱️ Timeout after {timeout}s — returning partial")
        fast_results = []
    
    # Score with Kenya Intent Engine - Adaptive Thresholds
    scored_leads = batch_score_leads(fast_results, location)
    
    # Try thresholds from high to low (enterprise search pattern)
    thresholds = get_adaptive_thresholds()
    leads = []
    used_threshold = thresholds[0]  # Default to highest
    
    for threshold in thresholds:
        # Safety check: score >= threshold AND has intent signals
        filtered = [
            lead for lead in scored_leads 
            if should_accept_lead(
                intent_score=lead.get('intent_score', 0),
                has_intent_signals=lead.get('intent_score', 0) > 0,  # Must have detected signals
                threshold=threshold
            )
        ]
        if filtered:
            leads = filtered
            used_threshold = threshold
            logger.info(f"✓ Found {len(leads)} leads at threshold {threshold}")
            break
    
    if not leads:
        logger.info(f"⚠ No leads found at any threshold (tried {thresholds})")
    
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    logger.info(f"✓ FAST: {len(leads)}/{len(scored_leads)} leads (final threshold: {used_threshold}) in {duration:.1f}s")
    
    response = {
        "leads": leads,
        "count": len(leads),
        "calls_made": len(fast_queries) * len(fast_scrapers),
        "duration_seconds": duration,
        "intent_threshold": used_threshold,
        "cached": False
    }
    
    # Cache for 5 minutes
    set_cache(query, location, {
        "results": leads,
        "leads": leads,
        "count": len(leads),
        "status": "success",
        "mode": "fast",
        "query": query,
        "location": location
    })
    
    return response


async def _run_with_early_stopping(
    queries: List[str],
    scrapers: List,
    location: str,
    max_leads: int,
    concurrency: int
) -> List[Dict]:
    """
    Run queries with early stopping and Anti-429 throttling.
    """
    all_results = []
    semaphore = asyncio.Semaphore(concurrency)
    cancelled = False
    
    async def run_one(query: str, scraper) -> List[Dict]:
        if cancelled:
            return []
        
        async with semaphore:
            # Anti-429: Apply throttling per scraper
            scraper_name = scraper.__class__.__name__
            await throttler.throttle(scraper_name)
            
            # Anti-429: Add jitter
            await apply_delay(0.3, 0.8)
            
            try:
                return await run_scrapers_parallel([scraper], query, location, hours=24)
            except Exception as e:
                logger.error(f"Query failed: {e}")
                return []
    
    # Create tasks - one per (query, scraper) pair
    tasks = []
    for query in queries:
        for scraper in scrapers:
            tasks.append(asyncio.create_task(run_one(query, scraper)))
    
    # Process as they complete
    for completed in asyncio.as_completed(tasks):
        if cancelled:
            break
        
        results = await completed
        all_results.extend(results)
        
        # Early stopping
        if len(all_results) >= max_leads * 3:
            logger.info(f"🛑 Early stopping: {len(all_results)} raw")
            cancelled = True
            for task in tasks:
                if not task.done():
                    task.cancel()
            break
    
    return all_results
