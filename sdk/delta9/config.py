"""SDK Configuration management."""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """Delta9 SDK configuration.
    
    Environment variables:
        DELTA9_API_KEY: API authentication key
        DELTA9_API_URL: Base API URL (default: http://localhost:8000)
        DELTA9_TIMEOUT: Request timeout in seconds (default: 30)
    
    Example:
        >>> from delta9 import Config
        >>> config = Config(api_key="your-key", api_url="https://api.delta9.io")
    """
    
    api_key: Optional[str] = None
    api_url: str = "http://localhost:8000"
    timeout: int = 30
    
    def __post_init__(self):
        # Load from environment if not provided
        if self.api_key is None:
            self.api_key = os.getenv("DELTA9_API_KEY")
        if os.getenv("DELTA9_API_URL"):
            self.api_url = os.getenv("DELTA9_API_URL")
        if os.getenv("DELTA9_TIMEOUT"):
            self.timeout = int(os.getenv("DELTA9_TIMEOUT"))
    
    @property
    def headers(self) -> dict:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
