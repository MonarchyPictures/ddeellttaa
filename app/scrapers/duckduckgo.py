# app/scrapers/duckduckgo.py
# ============================================================
# DUCKDUCKGO SCRAPER — Fixed imports, time filtering, title handling
# ============================================================

import logging
import re
import time
from datetime import datetime, timezone

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)


class DuckDuckGoScraper(BaseScraper):
    source = "duckduckgo"

    def scrape(self, query: str, time_window_hours: int):
        if DDGS is None:
            logger.error("DDG package not installed!")
            return []

        # Build search query with buyer intent
        platforms = (
            'site:facebook.com OR site:reddit.com OR site:kenyatalk.com '
            'OR site:twitter.com OR site:x.com OR site:instagram.com '
            'OR site:tiktok.com OR site:linkedin.com'
        )

        buyer_query = (
            f'{platforms} {query} '
            f'("looking for" OR "want to buy" OR "wtb" OR "buying" '
            f'OR "natafuta" OR "nahitaji" OR "need" OR "anyone selling")'
        )

        logger.info(f"DDG Scrape: {buyer_query[:100]}...")
        
        location_terms = [
            "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika",
            "kitengela", "ruaka", "kilimani", "kileleshwa", "lavington",
            "westlands", "parklands", "karen", "runda", "muthaiga",
            "kenya"
        ]
        simplified_query = query
        for term in location_terms:
            simplified_query = re.sub(rf"(?i)\b{re.escape(term)}\b", " ", simplified_query)
        simplified_query = re.sub(r"\s+", " ", simplified_query).strip().strip(",")
        if not simplified_query:
            simplified_query = query
        
        # Map requested freshness window to DDG timelimit.
        if time_window_hours <= 24:
            timelimit = "d"
        elif time_window_hours <= 24 * 7:
            timelimit = "w"
        else:
            timelimit = "m"

        # Define helper for robust searching
        def search_ddg(q, region, max_res, backend=None):
            time.sleep(1) # Rate limit protection
            kwargs = {'region': region, 'max_results': max_res, 'timelimit': timelimit}
            if backend:
                kwargs['backend'] = backend
            try:
                res = list(DDGS().text(q, **kwargs))
                if not res:
                     logger.warning(f"DDG: 0 results for '{q}' in '{region}' backend={backend}")
                return res
            except TypeError:
                # Some DDGS versions do not support timelimit. Retry without it.
                kwargs.pop('timelimit', None)
                try:
                    return list(DDGS().text(q, **kwargs))
                except Exception as e:
                    logger.error(f"DDG Search Error for '{q}': {e}")
                    return []
            except Exception as e:
                logger.error(f"DDG Search Error for '{q}': {e}")
                return []

        results = []
        
        # 1. Try Buyer Intent Query (site:facebook etc)
        # This is the most valuable query, try it first
        logger.info(f"DDG: Trying Buyer Query: {buyer_query[:50]}...")
        results = search_ddg(buyer_query, 'ke-en', 10)
        if not results: results = search_ddg(buyer_query, 'ke-en', 10, 'html')
        if not results: results = search_ddg(buyer_query, 'wt-wt', 10)
        
        # 2. Fallback: Simple Query + Kenya
        if not results:
            alt_queries = [
                f"{simplified_query} Kenya",
                f"{simplified_query} Nairobi",
                simplified_query
            ]
            if "car" in simplified_query.lower():
                alt_queries.append(simplified_query.lower().replace("car", "vehicle"))
                alt_queries.append("vehicle Kenya")
            if "water tank" in simplified_query.lower():
                alt_queries.append("water tank Kenya")
                alt_queries.append("water tanks Kenya")
            logger.info(f"DDG: Buyer Query failed. Trying Simple Kenya: {alt_queries[0]}")
            for q in alt_queries:
                results = search_ddg(q, 'ke-en', 10)
                if results:
                    break
            if not results:
                for q in alt_queries:
                    results = search_ddg(q, 'wt-wt', 10)
                    if results:
                        break

        # 3. Fallback: Bare Query (Last Resort)
        if not results:
            logger.info(f"DDG: Simple Kenya failed. Trying Bare Query: {simplified_query}")
            results = search_ddg(simplified_query, 'ke-en', 10)
            if not results: results = search_ddg(simplified_query, 'wt-wt', 10)
            if not results: results = search_ddg(simplified_query, 'wt-wt', 10, 'html')
            
        # 4. Fallback: Bare Query with 'lite' backend (sometimes works when others fail)
        if not results:
             try:
                 results = search_ddg(simplified_query, 'wt-wt', 10, 'lite')
             except: pass

        if not results:
            logger.warning(f"DUCKDUCKGO: Zero results for '{query}' after all attempts.")
            return []

        logger.info(f"DUCKDUCKGO: Found {len(results)} raw results for '{query}'")
        
        # Processing results
        logger.info(f"DDG found {len(results)} results")
        
        signals = []
        for r in results:
            body = r.get('body', '')
            title = r.get('title', '')
            link = r.get('href', '')

            # FIXED: Ensure title is never empty or "general"
            if not title or title.strip().lower() in ('general', ''):
                title = (body[:80] + "...") if body and len(body) > 80 else body
                if not title:
                    title = f"Lead from {link[:50]}"

            full_text = f"{title} {body}"

            signal = ScraperSignal(
                source=self.source,
                text=full_text,
                title=title,
                author="DuckDuckGo User",
                contact=self.extract_contact_info(f"{body} {link}"),
                location="Kenya",
                url=link,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            signals.append(signal.model_dump())

        return signals
