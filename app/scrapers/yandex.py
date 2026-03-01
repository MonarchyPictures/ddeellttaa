# app/scrapers/yandex.py
# ============================================================
# YANDEX SEARCH SCRAPER — Alternative to Google, Kenya-optimized
# ============================================================

import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
import requests

from .base_scraper import BaseScraper, ScraperSignal, get_random_headers

logger = logging.getLogger(__name__)


class YandexScraper(BaseScraper):
    """Yandex Search scraper - Google alternative for Kenya production."""
    source = "yandex"
    base_url = "https://yandex.com/search"

    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]:
        """Search Yandex for buyer intent queries."""
        logger.info(f"YANDEX: Searching for '{query}'")
        
        # Build search queries with buyer intent
        search_queries = self._build_queries(query)
        
        all_results = []
        for search_query in search_queries:
            try:
                results = self._search_yandex(search_query)
                if results:
                    all_results.extend(results)
                    if len(all_results) >= 10:
                        break
                time.sleep(2)  # Rate limiting - Yandex is stricter
            except Exception as e:
                logger.warning(f"YANDEX: Search failed for '{search_query}': {e}")
                continue
        
        if not all_results:
            logger.warning(f"YANDEX: No results for '{query}'")
            return []
        
        logger.info(f"YANDEX: Found {len(all_results)} results for '{query}'")
        return self._process_results(all_results)

    def _build_queries(self, query: str) -> List[str]:
        """Build search queries with buyer intent signals."""
        return [
            f"{query} buying Kenya",
            f"{query} natafuta Kenya",
            f"{query} looking for Nairobi",
            f"{query} need Mombasa",
            f"buy {query} Kenya",
        ]

    def _search_yandex(self, query: str) -> List[Dict[str, Any]]:
        """Perform Yandex search with rotating headers."""
        headers = get_random_headers()
        headers["Referer"] = "https://yandex.com/"
        headers["Accept-Language"] = "en-US,en;q=0.9"
        
        params = {
            "text": query,
            "lr": 10395,  # English language region
            "numdoc": 10,
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
            logger.warning(f"YANDEX: Request failed: {e}")
            return []

    def _parse_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Yandex search results from HTML."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Yandex results are in .serp-item containers
        for result in soup.select('.serp-item, .organic'):
            try:
                # Extract title
                title_elem = result.select_one('.organic__url-text, .serp-item__title a, h2 a')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Extract URL
                link_elem = result.select_one('.organic__url, .path__item, a.link')
                url = ""
                if link_elem:
                    url = link_elem.get('href', '')
                    # Yandex uses redirect URLs
                    if url.startswith('/'):
                        continue
                
                # Extract snippet
                snippet_elem = result.select_one('.organic__content-wrapper, .text-container, .serp-item__text')
                snippet = ""
                if snippet_elem:
                    snippet = snippet_elem.get_text(strip=True)
                
                if title and url:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'source': 'yandex'
                    })
            except Exception as e:
                logger.debug(f"YANDEX: Parse error: {e}")
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
                author="Yandex Search",
                contact=self.extract_contact_info(f"{snippet} {url}"),
                location="Kenya",
                url=url,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            signals.append(signal.model_dump())
        
        return signals
