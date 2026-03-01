import logging
import os
import json
import redis
import time
from typing import Optional, Any
from datetime import timedelta, datetime

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "")
        self.enabled = False
        self.client = None
        
        # Only try Redis if REDIS_URL is set
        if self.redis_url:
            try:
                self.client = redis.from_url(self.redis_url, decode_responses=True)
                self.client.ping()
                self.enabled = True
                logger.info(f"Redis cache connected: {self.redis_url}")
            except Exception as e:
                logger.warning(f"Redis unavailable: {e}")
                self.enabled = False
        else:
            logger.info("REDIS_URL not set, using database cache")

    def _get_db_cache(self, key: str) -> Optional[Any]:
        """Get from database cache (PostgreSQL/SQLite)."""
        try:
            from app.db.database import SessionLocal
            from app.db.models import Cache
            
            db = SessionLocal()
            try:
                # Clean expired entries
                now = datetime.utcnow()
                db.query(Cache).filter(Cache.expires_at < now).delete()
                
                # Get cache entry
                cache_entry = db.query(Cache).filter(Cache.query == key).first()
                
                if cache_entry and cache_entry.data:
                    return cache_entry.data
                return None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"DB cache GET error: {e}")
            return None

    def _set_db_cache(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set in database cache (PostgreSQL/SQLite)."""
        try:
            from app.db.database import SessionLocal
            from app.db.models import Cache
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            
            db = SessionLocal()
            try:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
                
                # Try upsert - delete old, insert new (simple approach)
                db.query(Cache).filter(Cache.query == key).delete()
                
                cache_entry = Cache(
                    query=key,
                    location="default",
                    data=value,
                    expires_at=expires_at
                )
                db.add(cache_entry)
                db.commit()
                logger.debug(f"Cached to DB: {key}")
            except Exception as e:
                db.rollback()
                logger.error(f"DB cache SET error: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"DB cache SET outer error: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Get from cache (Redis -> DB -> None)."""
        try:
            # Try Redis first
            if self.enabled and self.client:
                try:
                    data = self.client.get(key)
                    if data:
                        return json.loads(data)
                except Exception as e:
                    logger.error(f"Redis GET error: {e}")
                    self.enabled = False
            
            # Fall back to database cache
            return self._get_db_cache(key)
            
        except Exception as e:
            logger.error(f"Cache GET failed: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set in cache (Redis and DB)."""
        try:
            # Try Redis first
            if self.enabled and self.client:
                try:
                    self.client.setex(key, timedelta(seconds=ttl_seconds), json.dumps(value))
                    return
                except Exception as e:
                    logger.error(f"Redis SET error: {e}")
                    self.enabled = False
            
            # Fall back to database cache
            self._set_db_cache(key, value, ttl_seconds)
            
        except Exception as e:
            logger.error(f"Cache SET failed: {e}")

    def delete(self, key: str):
        """Delete from cache."""
        try:
            # Delete from Redis
            if self.enabled and self.client:
                try:
                    self.client.delete(key)
                except Exception as e:
                    logger.error(f"Redis DELETE error: {e}")
            
            # Delete from DB
            try:
                from app.db.database import SessionLocal
                from app.db.models import Cache
                
                db = SessionLocal()
                try:
                    db.query(Cache).filter(Cache.query == key).delete()
                    db.commit()
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"DB cache DELETE error: {e}")
                
        except Exception as e:
            logger.error(f"Cache DELETE failed: {e}")


# Global Instance
cache = RedisCache()


# Backward compatibility functions
def get_cached(query: str, location: str = "Kenya") -> Optional[Any]:
    """Get cached search results."""
    key = f"{query}:{location}"
    return cache.get(key)


def set_cached(query: str, results: Any, location: str = "Kenya", ttl: int = 600) -> bool:
    """Cache search results."""
    try:
        key = f"{query}:{location}"
        cache.set(key, results, ttl)
        return True
    except Exception as e:
        logger.error(f"set_cached error: {e}")
        return False
