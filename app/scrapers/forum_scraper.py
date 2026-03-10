"""
Forum Scraper - REAL DATA ONLY
Scrapes real forums and Q&A sites
NO MOCK DATA - Returns empty if no real data found
"""
from typing import List, Optional
from datetime import datetime
import re

from .base import BaseScraper, ScrapeResult


class ForumScraper(BaseScraper):
    """
    Scraper for forums - REAL SIGNALS ONLY
    
    Scrapes real forums like Quora, Reddit, StackExchange.
    NO MOCK DATA - Returns empty list if no results.
    """
    
    @property
    def source_name(self) -> str:
        return "forum"
    
    async def search(self, query: str, limit: int = 15) -> List[ScrapeResult]:
        """
        Search forums for real posts
        
        Returns ONLY real data from actual forums.
        NO MOCK DATA.
        """
        print(f"[ForumScraper] Searching for: '{query}'")
        
        results = []
        
        # Try Quora
        try:
            quora_results = await self._search_quora(query, limit // 3)
            if quora_results:
                results.extend(quora_results)
                print(f"[ForumScraper] Found {len(quora_results)} results from Quora")
        except Exception as e:
            print(f"[ForumScraper] Quora search failed: {e}")
        
        # Try StackExchange
        try:
            se_results = await self._search_stackexchange(query, limit // 3)
            if se_results:
                results.extend(se_results)
                print(f"[ForumScraper] Found {len(se_results)} results from StackExchange")
        except Exception as e:
            print(f"[ForumScraper] StackExchange search failed: {e}")
        
        if not results:
            print(f"[ForumScraper] No real results found for '{query}'")
        
        return results
    
    async def _search_quora(self, query: str, limit: int) -> List[ScrapeResult]:
        """Search Quora for real questions"""
        results = []
        
        try:
            # Quora search URL
            search_url = f"https://www.quora.com/search"
            params = {"q": query, "type": "question"}
            
            response = await self._rate_limited_request(
                search_url,
                params=params,
                timeout=15.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            
            if response.status_code == 200:
                html = response.text
                
                # Look for question links
                # Pattern: question URLs like /unanswered/What-is-the-best-...
                question_pattern = r'href="(/[^"]*?/([^"]*?))"[^>]*class="[^"]*?question_link[^"]*?"'
                matches = re.findall(question_pattern, html)
                
                for i, (path, slug) in enumerate(matches[:limit]):
                    # Extract title from slug
                    title = slug.replace('-', ' ').replace('_', ' ')
                    title = ' '.join(word.capitalize() for word in title.split())
                    
                    # Only include if looks like a real question
                    if len(title) > 10 and '?' in title or any(word in title.lower() for word in ['best', 'recommend', 'looking', 'need', 'how', 'what', 'where']):
                        results.append(ScrapeResult(
                            external_id=f"quora_{slug}_{i}",
                            source="forum",
                            title=title,
                            content=title,  # Use title as content for now
                            author="quora_user",  # Quora doesn't show author in search
                            url=f"https://www.quora.com{path}",
                            posted_at=datetime.utcnow(),
                            subreddit="Quora",
                            metadata={"source": "quora", "type": "question"}
                        ))
        
        except Exception as e:
            print(f"[ForumScraper] Quora error: {e}")
        
        return results
    
    async def _search_stackexchange(self, query: str, limit: int) -> List[ScrapeResult]:
        """Search StackExchange API for real questions"""
        results = []
        
        try:
            # StackExchange API
            api_url = "https://api.stackexchange.com/2.3/search/advanced"
            params = {
                "q": query,
                "sort": "creation",
                "order": "desc",
                "site": "stackoverflow",
                "pagesize": limit
            }
            
            response = await self._rate_limited_request(api_url, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                for item in items:
                    if item.get("title"):
                        results.append(ScrapeResult(
                            external_id=f"se_{item.get('question_id')}",
                            source="forum",
                            title=item.get("title", ""),
                            content=item.get("title", ""),
                            author=item.get("owner", {}).get("display_name", "unknown"),
                            url=item.get("link", ""),
                            posted_at=datetime.fromtimestamp(item.get("creation_date", 0)) if item.get("creation_date") else datetime.utcnow(),
                            subreddit="StackExchange",
                            metadata={
                                "source": "stackexchange",
                                "score": item.get("score", 0),
                                "answer_count": item.get("answer_count", 0)
                            }
                        ))
        
        except Exception as e:
            print(f"[ForumScraper] StackExchange error: {e}")
        
        return results
