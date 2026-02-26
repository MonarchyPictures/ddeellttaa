import logging
import os
import json
import redis
import sqlite3
import time
from threading import Lock
from typing import Optional, Any
from datetime import timedelta
from sqlalchemy import text

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
        self.enabled = False
        self.client = None
        self.fallback_db_path = os.getenv("CACHE_FALLBACK_DB", "cache_fallback.db")
        self._sqlite_lock = Lock()
        self._shared_db_enabled = False
        self._shared_db_engine = None
        
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            self.enabled = True
            logger.info(f"Redis cache connected: {self.redis_url}")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}). Trying shared DB cache fallback.")
            self.enabled = False
            self._init_shared_db_fallback()
            if not self._shared_db_enabled:
                logger.warning("Shared DB cache unavailable. Using SQLite cache fallback.")
                self._init_sqlite_fallback()

    def _init_shared_db_fallback(self):
        try:
            from app.db.database import engine as app_engine
            self._shared_db_engine = app_engine
            with self._shared_db_engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS app_cache (
                            k TEXT PRIMARY KEY,
                            v TEXT NOT NULL,
                            expires_at BIGINT NOT NULL
                        )
                        """
                    )
                )
                conn.execute(
                    text("CREATE INDEX IF NOT EXISTS idx_app_cache_expires_at ON app_cache(expires_at)")
                )
            self._shared_db_enabled = True
            logger.info("Shared DB cache fallback enabled")
        except Exception as e:
            logger.warning(f"Shared DB cache fallback init failed: {e}")
            self._shared_db_enabled = False

    def _init_sqlite_fallback(self):
        with self._sqlite_lock:
            conn = sqlite3.connect(self.fallback_db_path)
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache (
                        k TEXT PRIMARY KEY,
                        v TEXT NOT NULL,
                        expires_at INTEGER NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON cache(expires_at)"
                )
                conn.commit()
            finally:
                conn.close()

    def _sqlite_get(self, key: str) -> Optional[Any]:
        now = int(time.time())
        with self._sqlite_lock:
            conn = sqlite3.connect(self.fallback_db_path)
            try:
                conn.execute("DELETE FROM cache WHERE expires_at <= ?", (now,))
                row = conn.execute("SELECT v FROM cache WHERE k = ?", (key,)).fetchone()
                conn.commit()
            finally:
                conn.close()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except Exception:
            return None

    def _sqlite_set(self, key: str, value: Any, ttl_seconds: int = 300):
        expires_at = int(time.time()) + max(1, int(ttl_seconds))
        payload = json.dumps(value)
        with self._sqlite_lock:
            conn = sqlite3.connect(self.fallback_db_path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (k, v, expires_at) VALUES (?, ?, ?)",
                    (key, payload, expires_at),
                )
                conn.commit()
            finally:
                conn.close()

    def _sqlite_delete(self, key: str):
        with self._sqlite_lock:
            conn = sqlite3.connect(self.fallback_db_path)
            try:
                conn.execute("DELETE FROM cache WHERE k = ?", (key,))
                conn.commit()
            finally:
                conn.close()

    def get(self, key: str) -> Optional[Any]:
        if self.enabled:
            try:
                data = self.client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error(f"Redis GET error: {e}")
                self.enabled = False
                if not self._shared_db_enabled:
                    self._init_shared_db_fallback()

        if self._shared_db_enabled:
            now = int(time.time())
            try:
                with self._shared_db_engine.begin() as conn:
                    conn.execute(text("DELETE FROM app_cache WHERE expires_at <= :now"), {"now": now})
                    row = conn.execute(
                        text("SELECT v FROM app_cache WHERE k = :k"),
                        {"k": key},
                    ).fetchone()
                if row and row[0]:
                    return json.loads(row[0])
            except Exception as e:
                logger.error(f"Shared DB cache GET error: {e}")
                self._shared_db_enabled = False
                self._init_sqlite_fallback()
        
        return self._sqlite_get(key)

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        if self.enabled:
            try:
                self.client.setex(key, timedelta(seconds=ttl_seconds), json.dumps(value))
                return
            except Exception as e:
                logger.error(f"Redis SET error: {e}")
                self.enabled = False
                if not self._shared_db_enabled:
                    self._init_shared_db_fallback()

        if self._shared_db_enabled:
            try:
                payload = json.dumps(value)
                expires_at = int(time.time()) + max(1, int(ttl_seconds))
                with self._shared_db_engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                            INSERT INTO app_cache (k, v, expires_at)
                            VALUES (:k, :v, :expires_at)
                            ON CONFLICT(k) DO UPDATE SET
                                v = excluded.v,
                                expires_at = excluded.expires_at
                            """
                        ),
                        {"k": key, "v": payload, "expires_at": expires_at},
                    )
                return
            except Exception as e:
                logger.error(f"Shared DB cache SET error: {e}")
                self._shared_db_enabled = False
                self._init_sqlite_fallback()
        
        self._sqlite_set(key, value, ttl_seconds)

    def delete(self, key: str):
        if self.enabled:
            try:
                self.client.delete(key)
                return
            except Exception as e:
                logger.error(f"Redis DELETE error: {e}")
                self.enabled = False
                if not self._shared_db_enabled:
                    self._init_shared_db_fallback()

        if self._shared_db_enabled:
            try:
                with self._shared_db_engine.begin() as conn:
                    conn.execute(text("DELETE FROM app_cache WHERE k = :k"), {"k": key})
                return
            except Exception as e:
                logger.error(f"Shared DB cache DELETE error: {e}")
                self._shared_db_enabled = False
                self._init_sqlite_fallback()
        
        self._sqlite_delete(key)

# Global Instance
cache = RedisCache()
