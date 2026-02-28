# app/core/agent_scraper_resolver.py
# ============================================================
# PRODUCTION-SAFE DYNAMIC SCRAPER RESOLVER
# ============================================================
# Returns valid scraper names from registry.
# Prevents "No scraper found" errors.
# ============================================================

import logging
from typing import List, Optional
from app.scrapers.registry import SCRAPER_REGISTRY

logger = logging.getLogger(__name__)

# Default priority order for stable execution
DEFAULT_PRIORITY = [
    "duckduckgo",
    "google_cse", 
    "serpapi",
    "facebook",
    "facebook_groups",
    "twitter",
    "telegram",
    "kenyan_forums",
    "jiji",
    "pigiame",
]


def get_available_scrapers(requested_platforms: Optional[List[str]] = None) -> List[str]:
    """
    Returns valid scraper names that exist in registry.
    If requested_platforms is None, returns priority-ordered active scrapers.
    
    Args:
        requested_platforms: List of platform names agent wants to use
        
    Returns:
        List of valid scraper names from registry
    """
    available = list(SCRAPER_REGISTRY.keys())
    
    if not available:
        logger.error("No scrapers available in registry!")
        return []
    
    # If no specific platforms requested, use priority order
    if not requested_platforms:
        valid = [p for p in DEFAULT_PRIORITY if p in available]
        # Add any remaining scrapers not in priority list
        for scraper in available:
            if scraper not in valid:
                valid.append(scraper)
        logger.info(f"Using default priority scrapers: {valid[:5]}...")
        return valid
    
    # Validate requested platforms
    valid = []
    for platform in requested_platforms:
        if platform in available:
            valid.append(platform)
        else:
            logger.warning(f"⚠️ Skipping unknown scraper: {platform}")
    
    if not valid:
        logger.warning(f"None of requested platforms {requested_platforms} available. Using defaults.")
        return get_available_scrapers(None)  # Fall back to defaults
    
    logger.info(f"✅ Using requested platforms: {valid}")
    return valid


def get_scraper_instance(platform: str):
    """
    Get scraper class from registry and instantiate it.
    
    Args:
        platform: Scraper name from registry
        
    Returns:
        Scraper instance or None if not found
    """
    scraper_class = SCRAPER_REGISTRY.get(platform)
    
    if not scraper_class:
        logger.error(f"⚠️ Scraper not found in registry: {platform}")
        return None
    
    try:
        scraper = scraper_class()
        logger.debug(f"✅ Instantiated scraper: {platform}")
        return scraper
    except Exception as e:
        logger.error(f"❌ Failed to instantiate scraper {platform}: {e}")
        return None


def run_scraper_safe(platform: str, query: str, location: str = "Kenya", time_window_hours: int = 24):
    """
    Run a single scraper with full error handling.
    
    Args:
        platform: Scraper name
        query: Search query
        location: Location filter
        time_window_hours: Time window for results
        
    Returns:
        List of results or empty list on failure
    """
    scraper = get_scraper_instance(platform)
    
    if not scraper:
        return []
    
    try:
        logger.info(f"🚀 Running scraper: {platform} | Query: '{query}'")
        results = scraper.scrape(query, time_window_hours)
        count = len(results) if results else 0
        logger.info(f"✅ Scraper {platform} returned {count} results")
        return results or []
    except Exception as e:
        logger.error(f"❌ Scraper failed: {platform} | Error: {e}")
        return []


def run_multi_scraper(
    query: str,
    location: str = "Kenya",
    platforms: Optional[List[str]] = None,
    time_window_hours: int = 24
) -> List[dict]:
    """
    Run multiple scrapers and aggregate results.
    
    Args:
        query: Search query
        location: Location filter
        platforms: List of platforms to use (None for defaults)
        time_window_hours: Time window for results
        
    Returns:
        Aggregated list of results from all scrapers
    """
    platforms = get_available_scrapers(platforms)
    all_results = []
    seen_urls = set()
    
    logger.info(f"Starting multi-scraper run for '{query}' on {len(platforms)} platforms")
    
    for platform in platforms:
        results = run_scraper_safe(platform, query, location, time_window_hours)
        
        # Deduplicate by URL
        for r in results:
            url = r.get("url") or r.get("link") or ""
            if url and url not in seen_urls:
                seen_urls.add(url)
                r["source"] = platform  # Ensure source is set
                all_results.append(r)
    
    logger.info(f"Multi-scraper complete: {len(all_results)} unique results from {len(platforms)} platforms")
    return all_results
