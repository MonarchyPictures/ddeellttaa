"""
Base Scraper Class
All scrapers inherit from this
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import httpx
import asyncio


@dataclass
class ScrapeResult:
    """Result from a scraper"""
    external_id: str
    source: str
    title: str
    content: str
    author: str
    url: str
    posted_at: Optional[datetime]
    subreddit: Optional[str] = None
    metadata: Dict = None


class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, rate_limit: float = 1.0):
        """
        Initialize scraper
        
        Args:
            rate_limit: Seconds between requests
        """
        self.rate_limit = rate_limit
        self.last_request = 0
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source name (reddit, twitter, etc.)"""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[ScrapeResult]:
        """
        Search for content matching query
        
        Args:
            query: Search query
            limit: Max results to return
            
        Returns:
            List of scrape results
        """
        pass
    
    async def _rate_limited_request(self, url: str, **kwargs) -> httpx.Response:
        """Make a rate-limited HTTP request"""
        # Wait if needed
        elapsed = asyncio.get_event_loop().time() - self.last_request
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        
        response = await self.client.get(url, **kwargs)
        self.last_request = asyncio.get_event_loop().time()
        return response
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
