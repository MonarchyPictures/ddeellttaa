"""
Application configuration management.

All configuration is loaded from environment variables with sensible defaults.
Uses Pydantic Settings for validation and type safety.
"""

import os
from functools import lru_cache
from typing import List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors_origins(v: Union[str, List[str], None]) -> List[str]:
    """Parse CORS origins from string or list."""
    if v is None:
        return []
    if isinstance(v, str):
        if not v:
            return []
        return [origin.strip() for origin in v.split(",")]
    return v


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # =========================================================================
    # Application Settings
    # =========================================================================
    APP_NAME: str = Field(default="Delta 9", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(
        default="development", 
        description="Environment (development/staging/production)"
    )
    
    # =========================================================================
    # Server Settings
    # =========================================================================
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of worker processes")
    
    # =========================================================================
    # Database Settings
    # =========================================================================
    DATABASE_URL: str = Field(
        default="sqlite:///./delta9.db",
        description="Database connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, description="Database max overflow connections")
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries")
    
    # =========================================================================
    # Redis Settings
    # =========================================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_POOL_SIZE: int = Field(default=10, description="Redis connection pool size")
    
    # =========================================================================
    # Security Settings
    # =========================================================================
    SECRET_KEY: str = Field(
        default="change-me-in-production-immediately",
        description="Secret key for JWT signing"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60, description="JWT access token expiration in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="JWT refresh token expiration in days"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    
    # CORS Settings - handled as string, parsed manually
    CORS_ORIGINS: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins"
    )
    CORS_CREDENTIALS: bool = Field(default=True, description="Allow CORS credentials")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Requests per window")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window in seconds")
    
    # =========================================================================
    # Search & Scraping Settings
    # =========================================================================
    MIN_INTENT_SCORE: float = Field(default=0.18, description="Minimum intent score threshold")
    MAX_SEARCH_RESULTS: int = Field(default=50, description="Maximum search results")
    SEARCH_TIMEOUT: int = Field(default=30, description="Search timeout in seconds")
    SCRAPER_TIMEOUT: int = Field(default=8, description="Individual scraper timeout in seconds")
    
    # API Keys
    SERPAPI_KEY: Optional[str] = Field(default=None, description="SerpAPI key")
    SERPAPI_ENGINE: str = Field(default="google", description="SerpAPI search engine")
    SERPAPI_REGION: str = Field(default="ke", description="SerpAPI region code")
    SERPAPI_LANGUAGE: str = Field(default="en", description="SerpAPI language code")
    GOOGLE_CSE_API_KEY: Optional[str] = Field(default=None, description="Google Custom Search API key")
    GOOGLE_CSE_ID: Optional[str] = Field(default=None, description="Google Custom Search Engine ID")
    
    # =========================================================================
    # Celery Settings
    # =========================================================================
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )
    CELERY_WORKER_CONCURRENCY: int = Field(default=4, description="Celery worker concurrency")
    
    # =========================================================================
    # Telegram Settings
    # =========================================================================
    TELEGRAM_ENABLED: bool = Field(default=False, description="Enable Telegram integration")
    TELEGRAM_API_ID: Optional[str] = Field(default=None, description="Telegram API ID")
    TELEGRAM_API_HASH: Optional[str] = Field(default=None, description="Telegram API hash")
    TELEGRAM_PHONE: Optional[str] = Field(default=None, description="Telegram phone number")
    TELEGRAM_SESSION_NAME: str = Field(default="delta9_session", description="Telegram session name")
    
    # =========================================================================
    # AI/ML Settings
    # =========================================================================
    AI_ENABLED: bool = Field(default=False, description="Enable AI/ML features")
    TRANSFORMERS_CACHE_DIR: Optional[str] = Field(default=None, description="Transformers cache directory")
    
    # =========================================================================
    # Monitoring & Observability
    # =========================================================================
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Logging format (json/console)")
    
    # =========================================================================
    # Kenya-Specific Settings
    # =========================================================================
    DEFAULT_LOCATION: str = Field(default="Kenya", description="Default search location")
    KENYA_LOCK_ENABLED: bool = Field(default=False, description="Enable Kenya geo-locking")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return parse_cors_origins(self.CORS_ORIGINS)
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT.lower() == "testing"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Using lru_cache ensures we only create one Settings instance
    per application lifecycle.
    """
    return Settings()


# Global settings instance
settings = get_settings()
