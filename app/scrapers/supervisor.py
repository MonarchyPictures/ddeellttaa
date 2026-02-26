import logging
from typing import Dict, Any
from .metrics import SCRAPER_METRICS
from .registry import SCRAPER_REGISTRY, ACTIVE_SCRAPERS, update_scraper_state

logger = logging.getLogger("ScraperSupervisor")

def check_scraper_health(scraper_name: str):
    """
    🧠 SELF-HEALING: Auto-disable if unstable (3+ consecutive failures).
    """
    metrics = SCRAPER_METRICS.get(scraper_name, {})
    failures = metrics.get("consecutive_failures", 0)
    
    if failures >= 3:
        logger.warning(f"SELF-HEALING: Scraper {scraper_name} is unstable ({failures} failures). Auto-disabling.")
        update_scraper_state(scraper_name, False, caller="Supervisor")
        return False
    return True

def reset_consecutive_failures(scraper_name: str):
    """Reset failure counter on success."""
    if scraper_name in SCRAPER_METRICS:
        SCRAPER_METRICS[scraper_name]["consecutive_failures"] = 0

def revive_scrapers(): 
    """
    🔁 SELF-HEALING: Auto re-enable smart scrapers (earn trust back).
    Rule: Low failures + high historical verified leads.
    """
    logger.info("SELF-HEALING: Checking for scrapers to revive...")
    for name, metrics in SCRAPER_METRICS.items(): 
        # Skip core scrapers (they are always on) or already enabled ones
        scraper = SCRAPER_REGISTRY.get(name)
        if not scraper:
            continue
            
        is_core = getattr(scraper, "core", False)
        is_enabled = name in ACTIVE_SCRAPERS
        
        if is_core or is_enabled:
            continue

        # Logic: Scrapers earn trust back if they have few failures and high verified leads
        if metrics.get("failures", 0) < 2 and metrics.get("verified", 0) > 5: 
            logger.info(f"TRUST EARNED: Reviving {name} (Failures: {metrics['failures']}, Verified: {metrics['verified']})")
            update_scraper_state(name, True, caller="Supervisor (Revival)")
