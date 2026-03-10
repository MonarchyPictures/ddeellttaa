"""
Twitter/X Scraper
Uses Nitter instances (Twitter frontend) or mock data for demo
"""
from typing import List, Optional
from datetime import datetime

from .base import BaseScraper, ScrapeResult


class TwitterScraper(BaseScraper):
    """
    Scraper for Twitter/X
    
    Note: Twitter requires authentication. This implementation:
    1. Tries Nitter instances (public Twitter frontends)
    2. Falls back to mock data for demonstration
    
    For production, use Twitter API v2 with proper credentials.
    """
    
    NITTER_INSTANCES = [
        "https://nitter.net",
        "https://nitter.it",
        "https://nitter.cz",
    ]
    
    @property
    def source_name(self) -> str:
        return "twitter"
    
    async def search(self, query: str, limit: int = 20) -> List[ScrapeResult]:
        """
        Search Twitter for tweets matching query
        
        For demo purposes, returns mock data.
        In production, integrate with Twitter API v2.
        """
        results = []
        
        # Try Nitter first (public Twitter frontend)
        try:
            nitter_results = await self._search_nitter(query, limit)
            if nitter_results:
                return nitter_results
        except Exception as e:
            print(f"Nitter search failed: {e}")
        
        # Fallback to mock data for demonstration
        print(f"Twitter: Using mock data for '{query}'")
        results = self._generate_mock_data(query, limit)
        
        return results
    
    async def _search_nitter(self, query: str, limit: int) -> List[ScrapeResult]:
        """Try to search using Nitter"""
        results = []
        
        for instance in self.NITTER_INSTANCES:
            try:
                search_url = f"{instance}/search"
                params = {
                    "f": "tweets",
                    "q": query,
                }
                
                response = await self._rate_limited_request(
                    search_url,
                    params=params,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    # Parse Nitter HTML (simplified)
                    # In production, use BeautifulSoup
                    # For now, return empty to use mock data
                    pass
                    
            except Exception:
                continue
        
        return results
    
    def _generate_mock_data(self, query: str, limit: int) -> List[ScrapeResult]:
        """Generate realistic mock data for demonstration"""
        import random
        
        mock_users = [
            "john_buyer", "sarah_startup", "tech_guy_ke", "business_mom",
            "startup_founder", "dev_nairobi", "marketing_pro", "ceo_ke"
        ]
        
        mock_contents = [
            f"Looking for recommendations on {query}. Anyone used a good service?",
            f"Need {query} ASAP! Please DM me if you provide this service.",
            f"Who's the best {query} provider in Nairobi? Looking to hire soon.",
            f"URGENT: Looking for {query}. Budget is flexible. Contact me!",
            f"Can anyone recommend {query}? Need it for my business.",
            f"Searching for reliable {query}. Please share your experiences.",
            f"Looking to purchase {query} this week. Any leads?",
            f"Need help finding {query}. First time buyer here.",
        ]
        
        results = []
        for i in range(min(limit, len(mock_contents))):
            results.append(ScrapeResult(
                external_id=f"tweet_{i}_{hash(query) % 10000}",
                source="twitter",
                title="",
                content=mock_contents[i % len(mock_contents)],
                author=random.choice(mock_users),
                url=f"https://twitter.com/i/web/status/{i}",
                posted_at=datetime.now(),
                subreddit=None,
                metadata={
                    "likes": random.randint(0, 50),
                    "retweets": random.randint(0, 10),
                }
            ))
        
        return results
