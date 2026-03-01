# app/scrapers/__init__.py
"""
Scrapers module for Delta9 lead generation.

Organized into:
- Light scrapers: API-based, high concurrency
- Heavy scrapers: Playwright-based, low concurrency
"""

import asyncio
import logging
from typing import List, Dict, Any

from .registry import get_active_scrapers, SCRAPER_REGISTRY
from .base_scraper import BaseScraper
from .light import LIGHT_SCRAPERS
from .heavy import HEAVY_SCRAPERS

# Import specific scrapers for convenience
from .facebook_marketplace import FacebookMarketplaceScraper
from .reddit import RedditScraper

logger = logging.getLogger(__name__)

# Combined registry
ALL_SCRAPERS = {**LIGHT_SCRAPERS, **HEAVY_SCRAPERS}


async def run_scrapers(query: str, location: str = "Kenya") -> List[Dict[str, Any]]:
    """
    Orchestrates all active scrapers to run in parallel.
    Returns aggregated results.
    """
    scrapers = get_active_scrapers()
    if not scrapers:
        logger.warning("No active scrapers found in registry.")
        return []

    tasks = []
    for scraper in scrapers:
        if hasattr(scraper, 'search'):
            tasks.append(scraper.search(query, location))
        else:
            logger.warning(f"Scraper {scraper.__class__.__name__} does not have a search method.")

    if not tasks:
        return []

    # Run all scrapers in parallel
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_leads = []
    for i, result in enumerate(results_list):
        scraper_name = scrapers[i].__class__.__name__
        if isinstance(result, Exception):
            logger.error(f"Scraper {scraper_name} failed: {result}")
        elif result:
            logger.info(f"Scraper {scraper_name} returned {len(result)} leads.")
            all_leads.extend(result)
        else:
            logger.info(f"Scraper {scraper_name} returned 0 leads.")

    # Inject query context for matching
    for lead in all_leads:
        lead['query'] = query
        lead['location_raw'] = location

    return all_leads


__all__ = [
    # Base
    "BaseScraper",
    # Registries
    "LIGHT_SCRAPERS",
    "HEAVY_SCRAPERS",
    "ALL_SCRAPERS",
    "SCRAPER_REGISTRY",
    # Specific scrapers
    "FacebookMarketplaceScraper",
    "RedditScraper",
    # Functions
    "run_scrapers",
]
