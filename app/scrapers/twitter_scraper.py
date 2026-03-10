"""
Twitter/X Scraper - REAL DATA ONLY
Uses Nitter instances (public Twitter frontends)
NO MOCK DATA - Returns empty if no real data found
"""
from typing import List, Optional
from datetime import datetime
import re

from .base import BaseScraper, ScrapeResult


class TwitterScraper(BaseScraper):
    """
    Scraper for Twitter/X - REAL SIGNALS ONLY
    
    This scraper only returns actual data from Twitter/Nitter.
    If no data is available, it returns an empty list.
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
        
        Returns ONLY real data from Nitter/Twitter.
        NO MOCK DATA - Returns empty list if no results.
        """
        print(f"[TwitterScraper] Searching for: '{query}'")
        
        results = []
        
        # Try Nitter instances
        for instance in self.NITTER_INSTANCES:
            try:
                nitter_results = await self._search_nitter(instance, query, limit)
                if nitter_results:
                    results.extend(nitter_results)
                    print(f"[TwitterScraper] Found {len(nitter_results)} results from {instance}")
            except Exception as e:
                print(f"[TwitterScraper] {instance} failed: {e}")
                continue
        
        if not results:
            print(f"[TwitterScraper] No real results found for '{query}'")
        
        return results
    
    async def _search_nitter(self, instance: str, query: str, limit: int) -> List[ScrapeResult]:
        """Search using Nitter instance - returns real tweets only"""
        results = []
        
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
                # Parse HTML response
                html = response.text
                
                # Extract tweets using regex (simplified parsing)
                # Look for tweet containers
                tweet_pattern = r'<div class="timeline-item"[^>]*>.*?<div class="tweet-content"[^>]*>.*?<a href="([^"]+)"[^>]*class="tweet-link"[^>]*>.*?<div class="tweet-body"[^>]*>.*?<div class="tweet-content"[^>]*>(.*?)</div>.*?</div>'
                
                matches = re.findall(tweet_pattern, html, re.DOTALL | re.IGNORECASE)
                
                for i, (tweet_url, content_html) in enumerate(matches[:limit]):
                    # Extract text from HTML
                    text = self._extract_text_from_html(content_html)
                    
                    # Extract author
                    author_match = re.search(r'/@([^/]+)', tweet_url)
                    author = author_match.group(1) if author_match else "unknown"
                    
                    # Extract tweet ID
                    tweet_id_match = re.search(r'/status/(\d+)', tweet_url)
                    tweet_id = tweet_id_match.group(1) if tweet_id_match else f"unknown_{i}"
                    
                    if text and len(text) > 10:  # Only valid tweets
                        results.append(ScrapeResult(
                            external_id=f"twitter_{tweet_id}",
                            source="twitter",
                            title="",
                            content=text,
                            author=author,
                            url=f"{instance}{tweet_url}" if tweet_url.startswith('/') else tweet_url,
                            posted_at=datetime.utcnow(),  # Nitter doesn't always show exact time
                            subreddit=None,
                            metadata={
                                "instance": instance,
                                "source": "nitter"
                            }
                        ))
        
        except Exception as e:
            print(f"[TwitterScraper] Error parsing {instance}: {e}")
        
        return results
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract clean text from HTML content"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Decode HTML entities
        text = text.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        # Clean up whitespace
        text = ' '.join(text.split())
        return text.strip()
