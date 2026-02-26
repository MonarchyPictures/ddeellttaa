
# ⚖️ Source Trust & Weights
# Scrapers NEVER score intent; we weigh their raw signals here.

SOURCE_TRUST_WEIGHTS = {
    "google_maps": 0.95,
    "jiji": 0.90,
    "fb_market": 0.85,
    "facebook_marketplace": 0.85,
    "classifieds": 0.85,
    "serpapi": 0.75,
    "google_cse": 0.60,
    "twitter": 0.60,
    "twitter_x": 0.60,
    "reddit": 0.55,
    "duckduckgo": 0.50,
    "unknown": 0.40
}

def get_source_weight(source_name: str) -> float:
    """Returns the trust weight for a given source."""
    if not source_name:
        return SOURCE_TRUST_WEIGHTS["unknown"]
    
    source_lower = source_name.lower()
    for key, weight in SOURCE_TRUST_WEIGHTS.items():
        if key in source_lower:
            return weight
            
    return SOURCE_TRUST_WEIGHTS["unknown"]
