# app/services/search_cache.py
"""
Smart in-memory cache for search results.
Returns instantly (<50ms) for repeated queries within 5 minutes.
"""
import time
from typing import Dict, Any, Optional

from app.services.search_config import SEARCH_CONFIG

# In-memory cache: {cache_key: (timestamp, data)}
CACHE: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = SEARCH_CONFIG.FAST_CACHE_TTL  # 5 minutes
MAX_CACHE_SIZE = 100  # Prevent memory bloat


def get_cache_key(query: str, location: str) -> str:
    """Generate cache key from query parameters."""
    return f"{query.strip().lower()}:{location.strip().lower()}"


def get_cached(query: str, location: str) -> Optional[Dict[str, Any]]:
    """
    Get cached results if available and not expired.
    
    Returns:
        Cached data or None if not found/expired
    """
    cache_key = get_cache_key(query, location)
    
    if cache_key not in CACHE:
        return None
    
    timestamp, data = CACHE[cache_key]
    now = time.time()
    
    # Check if expired
    if now - timestamp > CACHE_TTL_SECONDS:
        # Remove expired entry
        del CACHE[cache_key]
        return None
    
    # Add cache metadata
    data_with_meta = data.copy()
    data_with_meta["cached"] = True
    data_with_meta["cache_age_seconds"] = int(now - timestamp)
    data_with_meta["cache_hit"] = True
    
    return data_with_meta


def set_cache(query: str, location: str, data: Dict[str, Any]) -> None:
    """
    Store results in cache.
    
    Args:
        query: Search query
        location: Location string
        data: Response data to cache
    """
    cache_key = get_cache_key(query, location)
    
    # Clean old entries if cache is full
    if len(CACHE) >= MAX_CACHE_SIZE:
        _clean_expired_entries()
    
    # If still full, remove oldest
    if len(CACHE) >= MAX_CACHE_SIZE:
        oldest_key = min(CACHE.keys(), key=lambda k: CACHE[k][0])
        del CACHE[oldest_key]
    
    # Store with timestamp
    CACHE[cache_key] = (time.time(), data)


def _clean_expired_entries() -> None:
    """Remove expired entries from cache."""
    now = time.time()
    expired_keys = [
        key for key, (timestamp, _) in CACHE.items()
        if now - timestamp > CACHE_TTL_SECONDS
    ]
    for key in expired_keys:
        del CACHE[key]


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring."""
    now = time.time()
    total = len(CACHE)
    expired = sum(1 for ts, _ in CACHE.values() if now - ts > CACHE_TTL_SECONDS)
    
    return {
        "total_entries": total,
        "expired_entries": expired,
        "valid_entries": total - expired,
        "max_size": MAX_CACHE_SIZE,
        "ttl_seconds": CACHE_TTL_SECONDS,
        "ttl_from_config": SEARCH_CONFIG.FAST_CACHE_TTL
    }


def clear_cache() -> None:
    """Clear all cached entries."""
    CACHE.clear()
