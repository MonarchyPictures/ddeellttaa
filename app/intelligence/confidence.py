SOURCE_CONFIDENCE = { 
    "google_maps": 0.95, 
    "GoogleMapsScraper": 0.95,
    "jiji": 0.9, 
    "JijiScraper": 0.9,
    "facebook_marketplace": 0.85, 
    "FacebookMarketplaceScraper": 0.85,
    "ClassifiedsScraper": 0.85,
    "twitter": 0.6, 
    "twitter_x": 0.6,
    "TwitterScraper": 0.6,
    "reddit": 0.55, 
    "RedditScraper": 0.55,
    "duckduckgo": 0.5, 
    "google_cse": 0.6, 
    "GoogleCSEScraper": 0.6,
    "serpapi": 0.7, 
    "unknown": 0.4 
} 

def apply_confidence(lead: dict) -> dict: 
    source_key = lead.get("_scraper_name") or lead.get("source") or "unknown"
    base = SOURCE_CONFIDENCE.get(source_key, 0.4) 

    # 🎯 Generic Intent Scoring: Blend source confidence with intent strength
    # Fallback to intent_score if intent_strength is missing
    intent = lead.get("intent_strength") or lead.get("intent_score", 0.5) 
    lead["confidence_score"] = round((base * 0.6) + (intent * 0.4), 2) 

    return lead
