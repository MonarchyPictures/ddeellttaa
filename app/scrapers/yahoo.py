# app/scrapers/yahoo.py
# ============================================================
# YAHOO SEARCH SCRAPER — Alternative to Google, Kenya-optimized
# ============================================================

import logging
import re
import time
import json
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any
import requests

from .base_scraper import BaseScraper, ScraperSignal, get_random_headers

logger = logging.getLogger(__name__)


class YahooScraper(BaseScraper):
    """Yahoo Search scraper - Google alternative for Kenya production."""
    source = "yahoo"
    base_url = "https://search.yahoo.com/search"

    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]:
        """Search Yahoo for buyer intent queries."""
        logger.info(f"YAHOO: Searching for '{query}'")
        
        # Build search queries with buyer intent
        search_queries = self._build_queries(query)
        
        all_results = []
        for search_query in search_queries:
            try:
                results = self._search_yahoo(search_query)
                if results:
                    all_results.extend(results)
                    if len(all_results) >= 10:
                        break
                time.sleep(1.5)  # Rate limiting between queries
            except Exception as e:
                logger.warning(f"YAHOO: Search failed for '{search_query}': {e}")
                continue
        
        if not all_results:
            logger.warning(f"YAHOO: No results for '{query}'")
            return []
        
        logger.info(f"YAHOO: Found {len(all_results)} results for '{query}'")
        return self._process_results(all_results)

    def _build_queries(self, query: str) -> List[str]:
        """Build search queries with buyer intent signals."""
        platforms = (
            'site:facebook.com OR site:reddit.com OR site:twitter.com '
            'OR site:x.com OR site:instagram.com'
        )
        
        buyer_terms = (
            '"looking for" OR "want to buy" OR "wtb" OR "buying" '
            'OR "natafuta" OR "nahitaji" OR "need"'
        )
        
        return [
            f"{platforms} {query} ({buyer_terms})",
            f"{query} buying Kenya",
            f"{query} natafuta Kenya",
            f"{query} looking for Nairobi",
        ]

    def _search_yahoo(self, query: str) -> List[Dict[str, Any]]:
        """Perform Yahoo search with rotating headers."""
        headers = get_random_headers()
        headers["Referer"] = "https://search.yahoo.com/"
        
        params = {
            "p": query,
            "n": 10,  # Number of results
        }
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            return self._parse_results(response.text)
        except requests.RequestException as e:
            logger.warning(f"YAHOO: Request failed: {e}")
            return []

    def _parse_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Yahoo search results from HTML."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Yahoo results are in .algo or .srp-result containers
        for result in soup.select('.algo, .srp-result, .dd.algo'):
            try:
                # Extract title
                title_elem = result.select_one('h3.title a, h3 a, .title a')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                # Extract snippet
                snippet_elem = result.select_one('.compText p, .abstract, .summary')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                if title and url:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'source': 'yahoo'
                    })
            except Exception as e:
                logger.debug(f"YAHOO: Parse error: {e}")
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
                author="Yahoo Search",
                contact=self.extract_contact_info(f"{snippet} {url}"),
                location="Kenya",
                url=url,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            signals.append(signal.model_dump())
        
        return signals
