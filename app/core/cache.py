"""
Redis Cache Layer for Search Results

Prevents duplicate scraping for repeated queries.
Cache TTL: 10 minutes (configurable via CACHE_TTL_SECONDS env var)
"""
import os
import json
import logging
from hashlib import md5
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Try to import redis
try:
    import redis as redis_lib
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_lib = None

# Redis client singleton
_redis_client = None

# Cache TTL - default 10 minutes, configurable via env var
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 600))


def get_redis_client():
    """Get or create Redis client singleton."""
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    if not REDIS_AVAILABLE:
        logger.debug("Redis library not available")
        return None
    
    REDIS_URL = os.getenv("REDIS_URL")
    if not REDIS_URL:
        logger.debug("REDIS_URL not set, caching disabled")
        return None
    
    try:
        _redis_client = redis_lib.from_url(REDIS_URL, decode_responses=True)
        # Test connection
        _redis_client.ping()
        logger.info(f"Redis cache connected. TTL: {CACHE_TTL_SECONDS}s")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        return None


def _make_key(query: str, location: str = "Kenya") -> str:
    """Create cache key from query and location."""
    key_string = f"{query.lower().strip()}:{location.lower().strip()}"
    return f"search:v1:{md5(key_string.encode()).hexdigest()}"


def get_cached(query: str, location: str = "Kenya") -> Optional[List[Dict[str, Any]]]:
    """
    Get cached search results.
    
    Args:
        query: Search query
        location: Location string
        
    Returns:
        Cached results or None if not found/expired
    """
    client = get_redis_client()
    if not client:
        return None
    
    try:
        key = _make_key(query, location)
        data = client.get(key)
        
        if data:
            logger.info(f"⚡ Cache HIT for '{query}' in {location}")
            return json.loads(data)
        
        logger.debug(f"Cache MISS for '{query}'")
        return None
        
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None


def set_cached(query: str, results: List[Dict[str, Any]], location: str = "Kenya", ttl: int = None) -> bool:
    """
    Cache search results.
    
    Args:
        query: Search query
        results: Results to cache
        location: Location string
        ttl: Time-to-live in seconds (default: CACHE_TTL_SECONDS)
        
    Returns:
        True if cached successfully
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        key = _make_key(query, location)
        ttl = ttl or CACHE_TTL_SECONDS
        
        # Only cache if we have results
        if not results:
            logger.debug(f"Not caching empty results for '{query}'")
            return False
        
        client.setex(key, ttl, json.dumps(results))
        logger.info(f"💾 Cached {len(results)} results for '{query}' (TTL: {ttl}s)")
        return True
        
    except Exception as e:
        logger.error(f"Cache set error: {e}")
        return False


def invalidate_cache(query: str, location: str = "Kenya") -> bool:
    """
    Invalidate cached results for a query.
    
    Args:
        query: Search query
        location: Location string
        
    Returns:
        True if invalidated
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        key = _make_key(query, location)
        client.delete(key)
        logger.info(f"🗑️ Cache invalidated for '{query}'")
        return True
        
    except Exception as e:
        logger.error(f"Cache invalidate error: {e}")
        return False


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    client = get_redis_client()
    if not client:
        return {"available": False}
    
    try:
        info = client.info()
        return {
            "available": True,
            "ttl_seconds": CACHE_TTL_SECONDS,
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "total_keys": client.dbsize()
        }
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return {"available": True, "error": str(e)}
