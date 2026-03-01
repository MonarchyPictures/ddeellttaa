# app/scrapers/brave.py
# ============================================================
# BRAVE SEARCH SCRAPER — Privacy-focused Google alternative
# ============================================================
# Uses Brave Search API (requires API key) or web scraping fallback

import logging
import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
import requests

from .base_scraper import BaseScraper, ScraperSignal, get_random_headers

logger = logging.getLogger(__name__)


class BraveScraper(BaseScraper):
    """Brave Search scraper - Privacy-focused Google alternative."""
    source = "brave"
    api_url = "https://api.search.brave.com/res/v1/web/search"
    
    def __init__(self, user_agent=None):
        super().__init__(user_agent)
        self.api_key = os.getenv("BRAVE_API_KEY")
        if self.api_key:
            logger.info("BRAVE: Using API mode with key")
        else:
            logger.info("BRAVE: No API key, will use web fallback")

    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]:
        """Search Brave for buyer intent queries."""
        logger.info(f"BRAVE: Searching for '{query}'")
        
        # Try API first if key available
        if self.api_key:
            results = self._search_api(query)
            if results:
                return self._process_results(results)
        
        # Fallback to web search
        search_queries = self._build_queries(query)
        
        all_results = []
        for search_query in search_queries:
            try:
                results = self._search_web(search_query)
                if results:
                    all_results.extend(results)
                    if len(all_results) >= 10:
                        break
                time.sleep(1.5)
            except Exception as e:
                logger.warning(f"BRAVE: Search failed: {e}")
                continue
        
        if not all_results:
            logger.warning(f"BRAVE: No results for '{query}'")
            return []
        
        logger.info(f"BRAVE: Found {len(all_results)} results for '{query}'")
        return self._process_results(all_results)

    def _build_queries(self, query: str) -> List[str]:
        """Build search queries with buyer intent signals."""
        return [
            f"{query} buying Kenya",
            f"{query} natafuta Kenya",
            f"{query} looking for Nairobi",
            f"buy {query} Kenya",
        ]

    def _search_api(self, query: str) -> List[Dict[str, Any]]:
        """Search using Brave Search API."""
        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
        }
        
        params = {
            "q": query,
            "count": 10,
            "offset": 0,
            "search_lang": "en",
        }
        
        try:
            response = requests.get(
                self.api_url,
                headers=headers,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("web", {}).get("results", []):
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('description', ''),
                    'source': 'brave_api'
                })
            return results
        except Exception as e:
            logger.warning(f"BRAVE API error: {e}")
            return []

    def _search_web(self, query: str) -> List[Dict[str, Any]]:
        """Perform web search with rotating headers (fallback)."""
        # Brave web search URL
        url = "https://search.brave.com/search"
        headers = get_random_headers()
        headers["Referer"] = "https://search.brave.com/"
        
        params = {
            "q": query,
        }
        
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            return self._parse_results(response.text)
        except requests.RequestException as e:
            logger.warning(f"BRAVE web request failed: {e}")
            return []

    def _parse_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Brave search results from HTML."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Brave results structure
        for result in soup.select('.snippet, .result'):
            try:
                title_elem = result.select_one('.title, .snippet-title a, h3 a')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                snippet_elem = result.select_one('.description, .snippet-description, .abstract')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                if title and url:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'source': 'brave_web'
                    })
            except Exception as e:
                logger.debug(f"BRAVE: Parse error: {e}")
                continue
        
        return results

    def _process_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert raw results to ScraperSignal format."""
        signals = []
        seen_urls = set()
        
        for r in results:
            url = r.get('url', '')
            if url in seen_urls or not url:
                continue
            seen_urls.add(url)
            
            title = r.get('title', '')
            snippet = r.get('snippet', '')
            
            # Ensure title is never empty
            if not title or title.strip().lower() in ('general', ''):
                title = (snippet[:80] + "...") if snippet and len(snippet) > 80 else snippet
                if not title:
                    title = f"Lead from {url[:50]}"
            
            full_text = f"{title} {snippet}"
            
            signal = ScraperSignal(
                source=self.source,
                text=full_text,
                title=title,
                author="Brave Search",
                contact=self.extract_contact_info(f"{snippet} {url}"),
                location="Kenya",
                url=url,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            signals.append(signal.model_dump())
        
        return signals
