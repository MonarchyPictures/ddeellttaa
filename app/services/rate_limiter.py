# app/services/rate_limiter.py
"""
Anti-429 Hardening — Rate Limiting & Throttling
Prevents 429 errors and ensures Railway stability.
"""
import time
import random
import asyncio
from typing import Dict, Optional, Any
from functools import wraps

# Domain tracking for per-domain throttling
DOMAIN_LAST_HIT: Dict[str, float] = {}
DOMAIN_COOLDOWN = 2.0  # 2 seconds between requests to same domain

# Global rate limiting
GLOBAL_REQUEST_COUNT = 0
GLOBAL_WINDOW_START = time.time()
GLOBAL_WINDOW_SIZE = 60  # 1 minute
GLOBAL_MAX_REQUESTS = 30  # Max 30 requests per minute


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower().replace("www.", "")
    except:
        return ""


def check_domain_cooldown(domain: str) -> bool:
    """Check if domain is in cooldown period."""
    if not domain:
        return True
    
    now = time.time()
    last_hit = DOMAIN_LAST_HIT.get(domain, 0)
    
    if now - last_hit < DOMAIN_COOLDOWN:
        return False
    
    DOMAIN_LAST_HIT[domain] = now
    return True


def check_global_rate_limit() -> bool:
    """Check global rate limit (30 req/min)."""
    global GLOBAL_REQUEST_COUNT, GLOBAL_WINDOW_START
    
    now = time.time()
    
    # Reset window if expired
    if now - GLOBAL_WINDOW_START > GLOBAL_WINDOW_SIZE:
        GLOBAL_REQUEST_COUNT = 0
        GLOBAL_WINDOW_START = now
    
    if GLOBAL_REQUEST_COUNT >= GLOBAL_MAX_REQUESTS:
        return False
    
    GLOBAL_REQUEST_COUNT += 1
    return True


async def apply_delay(min_delay: float = 0.5, max_delay: float = 2.0):
    """Apply random delay between requests (jitter)."""
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)


def with_rate_limit(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for rate-limited functions with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    # Check global rate limit
                    if not check_global_rate_limit():
                        wait_time = 60 - (time.time() - GLOBAL_WINDOW_START)
                        await asyncio.sleep(max(wait_time, 5))
                    
                    # Apply jitter before request
                    await apply_delay(0.5, 1.5)
                    
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        # Exponential backoff with jitter
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 2)
                        await asyncio.sleep(delay)
                        
                        if attempt == max_retries - 1:
                            raise RateLimitError(f"Rate limited after {max_retries} retries")
                    else:
                        raise
            
            return None
        return wrapper
    return decorator


class ScraperThrottler:
    """Per-scraper throttling to prevent 429s."""
    
    def __init__(self):
        self.scraper_delays: Dict[str, float] = {
            # Fast scrapers (API-based) - shorter delays
            "DuckDuckGoScraper": 0.5,
            "GoogleCSEScraper": 1.0,
            "SerpAPIScraper": 0.3,
            "YahooScraper": 1.5,
            "BraveScraper": 1.0,
            "YandexScraper": 1.0,
            
            # Heavy scrapers (browser-based) - longer delays
            "TelegramScraper": 3.0,
            "FacebookMarketplaceScraper": 5.0,
            "TwitterScraper": 3.0,
            "KenyanForumsScraper": 2.0,
            "JijiScraper": 2.0,
            "PigiameScraper": 2.0,
            "GoogleMapsScraper": 3.0,
        }
        self.last_request: Dict[str, float] = {}
    
    async def throttle(self, scraper_name: str):
        """Apply appropriate delay for scraper type."""
        delay = self.scraper_delays.get(scraper_name, 1.0)
        
        # Add jitter
        delay += random.uniform(0, 0.5)
        
        # Check last request time
        now = time.time()
        last = self.last_request.get(scraper_name, 0)
        elapsed = now - last
        
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        
        self.last_request[scraper_name] = time.time()


# Global throttler instance
throttler = ScraperThrottler()


class WorkerLimiter:
    """Global worker rate limiting (30 req/min)."""
    
    def __init__(self):
        self.request_count = 0
        self.window_start = time.time()
        self.window_size = 60
        self.max_requests = 30
    
    async def check(self):
        """Check if request is allowed under rate limit."""
        now = time.time()
        
        # Reset window if expired
        if now - self.window_start > self.window_size:
            self.request_count = 0
            self.window_start = now
        
        if self.request_count >= self.max_requests:
            # Wait until window resets
            wait_time = self.window_size - (now - self.window_start)
            await asyncio.sleep(max(wait_time, 1))
            self.request_count = 0
            self.window_start = time.time()
        
        self.request_count += 1


# Global worker limiter instance
worker_limiter = WorkerLimiter()


async def check_rate_limit():
    """Check global rate limit before making request."""
    await worker_limiter.check()


def get_system_health() -> Dict[str, Any]:
    """Get current system health for API responses."""
    return {
        "global_requests": GLOBAL_REQUEST_COUNT,
        "global_max": GLOBAL_MAX_REQUESTS,
        "window_remaining": max(0, GLOBAL_WINDOW_SIZE - (time.time() - GLOBAL_WINDOW_START)),
        "throttled_domains": len(DOMAIN_LAST_HIT),
        "status": "healthy" if GLOBAL_REQUEST_COUNT < GLOBAL_MAX_REQUESTS else "throttled"
    }
