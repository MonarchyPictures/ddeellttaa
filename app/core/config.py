
import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    try:
        from pydantic.v1 import BaseSettings
        SettingsConfigDict = None
    except ImportError:
        from pydantic import BaseSettings
        SettingsConfigDict = None

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore") if SettingsConfigDict else {}
    
    # Existing config or defaults
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Delta 9"
    
    # SERPAPI Configuration
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
    SERPAPI_ENGINE: str = "google"
    SERPAPI_REGION: str = "ke"
    SERPAPI_LANGUAGE: str = "en"
    GOOGLE_CSE_API_KEY: str = os.getenv("GOOGLE_CSE_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    GOOGLE_CSE_ID: str = os.getenv("GOOGLE_CSE_ID", os.getenv("GOOGLE_CX", ""))
    
    # Other settings from .env
    DATABASE_URL: str = "sqlite:///./intent_radar_v3.db"
    MIN_INTENT_SCORE: float = 0.4
    ALLOW_MOCK: bool = False  # Enforce NO mock data
    
    # Fallback for older pydantic versions
    if not model_config:
        class Config:
            env_file = ".env"
            case_sensitive = True
            extra = "ignore"

settings = Settings()
