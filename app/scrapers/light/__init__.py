# app/scrapers/light/__init__.py
"""
Light scrapers - API-based, low resource usage.

These scrapers use simple HTTP requests and can run
with higher concurrency (max 4).
"""

# Light scraper registry
LIGHT_SCRAPERS = {
    "duckduckgo": "DuckDuckGoScraper",
    "serpapi": "SerpApiScraper",
    "google_cse": "GoogleCSEScraper",
    "yahoo": "YahooScraper",
    "yandex": "YandexScraper",
    "brave": "BraveScraper",
}

__all__ = ["LIGHT_SCRAPERS"]
