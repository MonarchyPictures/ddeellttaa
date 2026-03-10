"""
Reddit Scraper
Uses Reddit's JSON API (no auth required for read-only)
"""
from typing import List, Optional
from datetime import datetime
import asyncio

from .base import BaseScraper, ScrapeResult


class RedditScraper(BaseScraper):
    """Scraper for Reddit"""
    
    BASE_URL = "https://www.reddit.com"
    
    @property
    def source_name(self) -> str:
        return "reddit"
    
    async def search(self, query: str, limit: int = 25) -> List[ScrapeResult]:
        """
        Search Reddit for posts matching query
        
        Args:
            query: Search query
            limit: Max results (max 100)
            
        Returns:
            List of ScrapeResult
        """
        results = []
        
        try:
            # Reddit search URL
            search_url = f"{self.BASE_URL}/search.json"
            params = {
                "q": query,
                "limit": min(limit, 100),
                "sort": "new",
                "t": "week",  # Last week
            }
            
            headers = {
                "User-Agent": "Delta9Bot/1.0 (Lead Research)"
            }
            
            response = await self._rate_limited_request(
                search_url, 
                params=params, 
                headers=headers
            )
            
            if response.status_code != 200:
                print(f"Reddit search failed: {response.status_code}")
                return results
            
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            
            for post in posts:
                post_data = post.get("data", {})
                
                # Skip stickied/deleted posts
                if post_data.get("stickied") or post_data.get("removed_by_category"):
                    continue
                
                result = ScrapeResult(
                    external_id=post_data.get("name", ""),  # t3_xxxxx
                    source="reddit",
                    title=post_data.get("title", ""),
                    content=post_data.get("selftext", "") or post_data.get("title", ""),
                    author=post_data.get("author", "[deleted]"),
                    url=f"https://www.reddit.com{post_data.get('permalink', '')}",
                    posted_at=datetime.fromtimestamp(post_data.get("created_utc", 0)),
                    subreddit=post_data.get("subreddit", ""),
                    metadata={
                        "score": post_data.get("score", 0),
                        "num_comments": post_data.get("num_comments", 0),
                        "is_self": post_data.get("is_self", True),
                    }
                )
                results.append(result)
            
            print(f"Reddit: Found {len(results)} posts for '{query}'")
            
        except Exception as e:
            print(f"Reddit scraper error: {e}")
        
        return results
    
    async def search_subreddit(self, subreddit: str, query: str, limit: int = 25) -> List[ScrapeResult]:
        """Search within a specific subreddit"""
        results = []
        
        try:
            search_url = f"{self.BASE_URL}/r/{subreddit}/search.json"
            params = {
                "q": query,
                "limit": min(limit, 100),
                "sort": "new",
                "t": "week",
                "restrict_sr": "on",  # Restrict to subreddit
            }
            
            headers = {
                "User-Agent": "Delta9Bot/1.0 (Lead Research)"
            }
            
            response = await self._rate_limited_request(
                search_url,
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get("data", {}).get("children", [])
                
                for post in posts:
                    post_data = post.get("data", {})
                    if post_data.get("stickied"):
                        continue
                    
                    result = ScrapeResult(
                        external_id=post_data.get("name", ""),
                        source="reddit",
                        title=post_data.get("title", ""),
                        content=post_data.get("selftext", "") or post_data.get("title", ""),
                        author=post_data.get("author", "[deleted]"),
                        url=f"https://www.reddit.com{post_data.get('permalink', '')}",
                        posted_at=datetime.fromtimestamp(post_data.get("created_utc", 0)),
                        subreddit=subreddit,
                        metadata={
                            "score": post_data.get("score", 0),
                            "num_comments": post_data.get("num_comments", 0),
                        }
                    )
                    results.append(result)
        
        except Exception as e:
            print(f"Reddit subreddit search error: {e}")
        
        return results
