# app/scrapers/heavy/__init__.py
"""
Heavy scrapers - Playwright-based, high resource usage.

These scrapers use browser automation and must run
with lower concurrency (max 2).
"""

# Heavy scraper registry
HEAVY_SCRAPERS = {
    "facebook": "FacebookScraper",
    "twitter": "TwitterScraper",
    "telegram": "TelegramScraper",
    "jiji": "JijiScraper",
    "pigiame": "PigiameScraper",
    "google_maps": "GoogleMapsScraper",
    "kenyan_forums": "KenyanForumsScraper",
    "whatsapp_groups": "WhatsAppGroupsScraper",
    "instagram": "InstagramScraper",
    "reddit": "RedditScraper",
}

__all__ = ["HEAVY_SCRAPERS"]
