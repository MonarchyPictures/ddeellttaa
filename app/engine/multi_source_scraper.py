# app/engine/multi_source_scraper.py
# ============================================================
# MULTI-SOURCE SCRAPER
# ============================================================
# Executes search queries across multiple platforms in parallel.
# Each source is independent and fault-tolerant.
# ============================================================

import logging
import asyncio
import time
import random
import os
from typing import List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None


from app.scrapers.registry import SCRAPER_REGISTRY, get_active_scrapers

class MultiSourceScraper:
    """
    Executes search queries across multiple sources.
    Designed for parallel execution and fault tolerance.
    """

    def __init__(self):
        self.timeout = int(os.getenv("SEARCH_PLATFORM_TIMEOUT_SEC", "35"))
        self.global_timeout = int(os.getenv("SEARCH_GLOBAL_TIMEOUT_SEC", "60"))
        self.max_results_per_query = 15
        self.max_results_per_source = 30

    async def execute_search_plan(
        self, plan: Dict, max_total_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Execute the search plan from QueryIntelligenceEngine.
        Runs all platform searches in parallel.
        """
        all_results = []
        seen_urls = set()

        platforms = plan.get("platforms", {})
        logger.info(f"Executing search across {len(platforms)} platforms")

        # Run each platform in parallel via executor-backed futures.
        loop = asyncio.get_event_loop()

        task_map = {}
        for platform, queries in platforms.items():
            task = loop.run_in_executor(
                None,
                self._scrape_platform,
                platform, queries, plan.get("original_query", ""),
                plan.get("location", "Kenya")
            )
            task_map[task] = platform

        # Collect as each task finishes; never block on one slow source.
        done, pending = await asyncio.wait(
            list(task_map.keys()),
            timeout=self.global_timeout,
            return_when=asyncio.ALL_COMPLETED
        )

        if pending:
            for p in pending:
                platform = task_map.get(p, "unknown")
                logger.warning(f"⏰ {platform}: global timeout exceeded; cancelling")
                p.cancel()

        for task in done:
            platform = task_map.get(task, "unknown")
            try:
                results = task.result()
                if results:
                    # Deduplicate
                    for r in results:
                        url = r.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(r)

                    logger.info(f"✅ {platform}: {len(results)} results")
                else:
                    logger.info(f"⚠️ {platform}: 0 results")
            except Exception as e:
                logger.error(f"❌ {platform}: {e}")

            if len(all_results) >= max_total_results:
                break

        logger.info(f"📊 Total unique results: {len(all_results)}")
        return all_results

    def _scrape_platform(
        self, platform: str, queries: List[str],
        original_query: str, location: str
    ) -> List[Dict]:
        """Scrape a single platform with multiple queries."""
        
        # Check if we have a dedicated scraper in the registry
        if platform in SCRAPER_REGISTRY:
            scraper = SCRAPER_REGISTRY[platform]
            logger.info(f"🚀 Using dedicated scraper for {platform}")
            
            results = []
            seen = set()
            
            # Use the first query + location for best results
            # Most dedicated scrapers handle the specific query construction internally
            search_query = f"{original_query}"
            
            try:
                # Run the dedicated scraper
                # It handles its own retries and resilience
                batch = scraper.scrape(search_query, time_window_hours=24)
                
                for r in batch:
                    url = r.get("url", "")
                    if url and url not in seen:
                        seen.add(url)
                        results.append(r)
                        
            except Exception as e:
                logger.error(f"❌ Dedicated scraper {platform} failed: {e}")
                
            return results

        # Fallback to DDG for unknown platforms
        scraper_map = {
            "facebook_groups": self._search_ddg,
            "twitter": self._search_ddg,
            "reddit": self._search_ddg,
            "kenyan_forums": self._search_ddg, # Now likely covered by registry, but keep as fallback
            "whatsapp": self._search_ddg,      # Now covered by registry
            "google": self._search_google_with_fallback,
            "duckduckgo": self._search_ddg,
            "jiji_wanted": self._search_ddg,   # Covered by registry
            "telegram": self._search_ddg,      # Covered by registry
        }

        scraper_fn = scraper_map.get(platform, self._search_ddg)
        results = []
        seen = set()

        for query in queries:
            if len(results) >= self.max_results_per_source:
                break

            try:
                # Small delay between queries to avoid rate limiting
                time.sleep(random.uniform(1, 3))
                batch = scraper_fn(query, platform, location)

                for r in batch:
                    url = r.get("url", "")
                    if url not in seen:
                        seen.add(url)
                        results.append(r)

            except Exception as e:
                logger.error(f"Query error on {platform}: {e}")

        return results

    def _search_ddg(
        self, query: str, source: str, location: str
    ) -> List[Dict]:
        """Search using DuckDuckGo."""
        if DDGS is None:
            logger.error("DDG not available")
            return []

        results = []

        # Try with different time filters, regions, and backends to survive anti-bot throttling
        for timelimit in ['w', 'm', None]:
            if results:
                break
            for region in ['ke-en', 'wt-wt']:
                if results:
                    break
                for backend in [None, 'html', 'lite']:
                    if results:
                        break
                    try:
                        with DDGS() as ddgs:
                            kwargs = {
                                "max_results": self.max_results_per_query,
                                "region": region,
                                "timelimit": timelimit
                            }
                            if backend:
                                kwargs["backend"] = backend
                            ddg_results = list(ddgs.text(query, **kwargs))

                            for r in ddg_results:
                                url = r.get('href', '')
                                title = r.get('title', '')
                                body = r.get('body', '')

                                if not url:
                                    continue

                                # Basic URL filtering
                                url_lower = url.lower()
                                skip_domains = [
                                    'amazon.com', 'ebay.com', 'alibaba.com',
                                    'aliexpress.com', 'wikipedia.org'
                                ]
                                if any(d in url_lower for d in skip_domains):
                                    continue

                                # Platform validation for specific sources
                                if source == "facebook_groups":
                                    if 'facebook.com' not in url_lower:
                                        continue
                                elif source == "twitter":
                                    if not any(d in url_lower for d in ['twitter.com', 'x.com']):
                                        continue
                                elif source == "reddit":
                                    if 'reddit.com' not in url_lower:
                                        continue
                                elif source == "kenyan_forums":
                                    forum_domains = ['kenyatalk.com', 'wazua.co.ke', 'jamiiforums.com']
                                    if not any(d in url_lower for d in forum_domains):
                                        continue
                                elif source == "whatsapp":
                                    if 'chat.whatsapp.com' not in url_lower:
                                        continue
                                elif source == "telegram":
                                    if 't.me' not in url_lower:
                                        continue

                                results.append({
                                    "source": source,
                                    "url": url,
                                    "title": title or (body[:80] + "..." if body else ""),
                                    "text": f"{title} {body}".strip(),
                                    "body": body,
                                    "location": location,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                })

                            if ddg_results:
                                logger.debug(
                                    f"DDG ({source}): {len(results)} results for timelimit={timelimit} "
                                    f"region={region} backend={backend}"
                                )

                    except Exception as e:
                        err = str(e).lower()
                        if 'ratelimit' in err or '429' in err:
                            logger.warning("DDG rate limited. Waiting...")
                            time.sleep(random.uniform(8, 15))
                        else:
                            logger.error(f"DDG error ({source}): {e}")

        return results

    def _search_google_with_fallback(self, query: str, source: str, location: str) -> List[Dict]:
        """
        Prefer Google CSE when configured; fallback to robust DDG search on any failure/empty result.
        """
        results = self._search_google_cse(query, source, location)
        if results:
            return results
        return self._search_ddg(query, source, location)

    def _search_google_cse(
        self, query: str, source: str, location: str
    ) -> List[Dict]:
        """Search using Google Custom Search Engine API."""
        import os
        import requests

        api_key = os.getenv("GOOGLE_CSE_API_KEY", "")
        cx = os.getenv("GOOGLE_CSE_ID", "")

        if not api_key or not cx:
            return []

        try:
            params = {
                "q": query,
                "key": api_key,
                "cx": cx,
                "cr": "countryKE",
                "num": 10
            }
            response = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params, timeout=15
            )

            if response.status_code != 200:
                return []

            data = response.json()
            results = []

            for item in data.get("items", []):
                results.append({
                    "source": "google_cse",
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "text": f"{item.get('title', '')} {item.get('snippet', '')}",
                    "body": item.get("snippet", ""),
                    "location": location,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            return results

        except Exception as e:
            logger.error(f"Google CSE error: {e}")
            return []


# Singleton
MULTI_SCRAPER = MultiSourceScraper()
