# 🎛️ SCRAPER GLOBAL CONFIGURATION
# Locked to Vehicles category for production stability

SCRAPER_CONFIG = {
    "facebook": {"enabled": True, "category": "vehicles"},
    "twitter": {"enabled": True, "category": "vehicles"},
    "google": {"enabled": True, "category": "vehicles"},
    "reddit": {"enabled": True, "category": "general"},
    "classifieds": {"enabled": True, "category": "general"},
    "google_cse": {"enabled": True, "category": "vehicles"}
}

def is_scraper_allowed(name: str) -> bool:
    """
    Dispatcher: Checks if a scraper is globally enabled.
    """
    cfg = SCRAPER_CONFIG.get(name)
    if not cfg:
        return False
        
    return cfg.get("enabled", False)
