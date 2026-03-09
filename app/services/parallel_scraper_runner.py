# app/services/parallel_scraper_runner.py
# ============================================================
# PARALLEL SCRAPER RUNNER — Production-Grade Concurrency
# ============================================================
# RAILWAY PRODUCTION SETTINGS:
# - TOTAL MAX: 4 concurrent scrapers (never exceed on Railway)
# - Light scrapers: max 4 concurrency (API-based, fast)
#   Includes: serpapi, yahoo, yandex, brave, telegram, google_cse, duckduckgo
# - Heavy scrapers: max 2 concurrency (Playwright, memory-heavy)
#   Includes: facebook, twitter, jiji, pigiame, google_maps, whatsapp, forums
#
# PROTECTIONS:
# - Prevents Railway memory crash
# - Prevents 429 storms with jitter + exponential backoff
# - Domain cooldown: 10s between same domain requests
# - User-Agent rotation on all requests
# ============================================================

import asyncio
import random
import os
import time
import logging
from typing import List, Dict, Any
from functools import wraps
from urllib.parse import urlparse

# Import rate limiter
from .rate_limiter import check_rate_limit, worker_limiter

# Import scraper registry
from app.scrapers.registry import get_scraper_name

logger = logging.getLogger(__name__)


# ============================================================
# DOMAIN COOLDOWN — Prevent rapid-fire blocks
# ============================================================
# Tracks last request time per domain to avoid hitting same
# domain too frequently. Minimum 10s between requests to same domain.
# ============================================================

LAST_DOMAIN_HIT: Dict[str, float] = {}
DOMAIN_COOLDOWN_SECONDS = int(os.getenv("DOMAIN_COOLDOWN_SECONDS", 10))


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().replace("www.", "")
    except Exception:
        return ""


def domain_allowed(domain: str) -> bool:
    """
    Check if domain can be hit (cooldown expired).
    Returns True if allowed, False if on cooldown.
    """
    if not domain:
        return True
    
    now = time.time()
    last_hit = LAST_DOMAIN_HIT.get(domain, 0)
    
    if now - last_hit < DOMAIN_COOLDOWN_SECONDS:
        return False
    
    LAST_DOMAIN_HIT[domain] = now
    return True


def record_domain_hit(domain: str):
    """Record that we hit a domain."""
    if domain:
        LAST_DOMAIN_HIT[domain] = time.time()


def get_domain_cooldown_remaining(domain: str) -> float:
    """Get remaining cooldown time for a domain."""
    if not domain:
        return 0.0
    
    now = time.time()
    last_hit = LAST_DOMAIN_HIT.get(domain, 0)
    remaining = DOMAIN_COOLDOWN_SECONDS - (now - last_hit)
    
    return max(0.0, remaining)


# ============================================================
# RETRY UTILITIES — Exponential Backoff
# ============================================================

def retry_with_backoff(max_retries=3, base_delay=2.0, max_delay=60.0, exceptions=(Exception,)):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exception types to catch
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        raise last_exception
                    
                    # Exponential backoff with jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.5)  # Add up to 50% jitter
                    total_delay = delay + jitter
                    
                    await asyncio.sleep(total_delay)
            return None
        return wrapper
    return decorator


class RateLimitError(Exception):
    """Raised when rate limit (429) is hit."""
    pass

# Concurrency limits by scraper weight
# RAILWAY PRODUCTION LIMIT: Never exceed 4 total concurrent scrapers
MAX_LIGHT_CONCURRENCY = int(os.getenv("LIGHT_SCRAPER_CONCURRENCY", 4))  # API-based
MAX_HEAVY_CONCURRENCY = int(os.getenv("HEAVY_SCRAPER_CONCURRENCY", 2))  # Playwright


async def jitter():
    """Randomized delay to prevent 429 storms."""
    await asyncio.sleep(random.uniform(0.1, 0.3))


async def run_scraper_group(scrapers, query: str, location: str, max_concurrent: int):
    """Run a group of scrapers with specific concurrency limit."""
    semaphore = asyncio.Semaphore(max_concurrent)

    @retry_with_backoff(max_retries=2, base_delay=3.0, exceptions=(RateLimitError,))
    async def safe_search(scraper, query, location):
        """Call scraper.search with retry logic, domain cooldown, and rate limiting."""
        scraper_name = type(scraper).__name__
        
        # Check circuit breaker state
        cb_state = getattr(scraper, 'circuit_breaker', None)
        if cb_state:
            logger.warning(f"[DEBUG] {scraper_name} circuit: {cb_state.state}")
        
        # Check global rate limit (30/min per worker)
        await check_rate_limit()
        
        # Check if scraper has a base_url/domain that needs cooldown
        scraper_domain = ""
        if hasattr(scraper, 'base_url'):
            scraper_domain = extract_domain(scraper.base_url)
        elif hasattr(scraper, 'source'):
            # Use source as domain identifier for cooldown
            scraper_domain = getattr(scraper, 'source', '')
        
        # Check domain cooldown
        if scraper_domain and not domain_allowed(scraper_domain):
            remaining = get_domain_cooldown_remaining(scraper_domain)
            logger.warning(f"[DEBUG] {scraper_name} domain cooldown: {remaining:.1f}s")
            await asyncio.sleep(remaining)
        
        logger.warning(f"[DEBUG] Calling {scraper_name}.search('{query[:30]}...')")
        
        try:
            # INCREASED timeout: 15 seconds per scraper (was 5s, too aggressive)
            if hasattr(scraper, "search"):
                result = await asyncio.wait_for(
                    scraper.search(query, location),
                    timeout=15
                )
            elif hasattr(scraper, "scrape"):
                result = await asyncio.wait_for(
                    asyncio.to_thread(scraper.scrape, query, location),
                    timeout=15
                )
            else:
                logger.warning(f"[SCRAPER ERROR] {type(scraper).__name__} has no method")
                return []

            scraper_name = type(scraper).__name__
            logger.warning(f"[SCRAPER DEBUG] {scraper_name} returned: {type(result)} length: {len(result) if isinstance(result, list) else 'NOT LIST'}")
            
            # Ensure we always return a list
            if result is None:
                logger.warning(f"[SCRAPER ERROR] {scraper_name} returned None, converting to []")
                return []
            
            result_count = len(result) if isinstance(result, list) else 0
            logger.warning(f"[DEBUG] Scraper {scraper_name} returned {result_count}")

            return result

        except asyncio.TimeoutError:
            logger.warning(f"[TIMEOUT] {type(scraper).__name__} exceeded 15s")
            return []

        except Exception as e:
            logger.warning(f"[SCRAPER ERROR] {type(scraper).__name__}: {e}")
            return []

    async def run_with_limit(scraper):
        async with semaphore:
            # Add jitter before each request (anti-429)
            await jitter()
            try:
                return await safe_search(scraper, query, location)
            except Exception as e:
                logger.warning(f"[SCRAPER ERROR] {type(scraper).__name__}: {e}")
                return []

    if not scrapers:
        return []

    tasks = [run_with_limit(scraper) for scraper in scrapers]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    combined = []
    for r in results:
        if isinstance(r, list):
            combined.extend(r)

    return combined


async def run_scrapers_parallel(scrapers, query: str, location: str = "Kenya", hours: int = 24) -> List[Dict[str, Any]]:
    """
    Run all scrapers in parallel with weight-based concurrency.
    
    Separates LIGHT (API-based) from HEAVY (Playwright) scrapers:
    - Light: 6 concurrent max (fast, low memory)
    - Heavy: 2 concurrent max (Playwright, high memory)
    
    Args:
        scrapers: List of scraper instances
        query: Search query string
        location: Location filter (default: Kenya)
        hours: Time window in hours (default: 24)
    
    Returns:
        Combined list of results from all scrapers
    """
    logger.warning(f"[RUNNER DEBUG] run_scrapers_parallel called with {len(scrapers)} scrapers for query: '{query[:40]}...'")
    
    if not scrapers:
        logger.warning("[RUNNER DEBUG] No scrapers provided!")
        return []
    
    # Separate scrapers by weight
    light_scrapers = []
    heavy_scrapers = []

    # Scraper weight classification
    heavy_scraper_names = {
        "facebook", "facebook_groups", "twitter", "jiji", "pigiame",
        "google_maps", "whatsapp_groups", "kenyan_forums"
    }
    
    for scraper in scrapers:
        name = get_scraper_name(scraper)
        if name:
            if name in heavy_scraper_names:
                heavy_scrapers.append(scraper)
            else:
                light_scrapers.append(scraper)
        else:
            # Unknown scraper, treat as light
            light_scrapers.append(scraper)

    # Run groups in parallel with different limits
    light_results = await run_scraper_group(light_scrapers, query, location, MAX_LIGHT_CONCURRENCY)
    heavy_results = await run_scraper_group(heavy_scrapers, query, location, MAX_HEAVY_CONCURRENCY)

    return light_results + heavy_results
