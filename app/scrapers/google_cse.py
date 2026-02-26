import logging
import os
import re
import requests
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal
from app.utils.resilience import retry_sync

logger = logging.getLogger(__name__)

class GoogleCSEScraper(BaseScraper):
    source = "google_cse"

    def __init__(self, api_keys=None, cx=None):
        super().__init__()
        # Support rotation: Provide a comma-separated list of keys in env or a list
        env_keys = os.getenv("GOOGLE_CSE_API_KEYS", "")
        if env_keys:
            self.api_keys = [k.strip() for k in env_keys.split(",")]
        else:
            # Use single key if env not set, avoiding dummy placeholders
            default_key = (
                os.getenv("GOOGLE_CSE_API_KEY", "")
                or os.getenv("GOOGLE_API_KEY", "")
                or os.getenv("GOOGLE_CSE_KEY", "")
            )
            self.api_keys = [default_key]
        
        self.current_key_index = 0
        self.cx = cx or os.getenv("GOOGLE_CSE_ID", "") or os.getenv("GOOGLE_CX", "")

    def _simplify_query(self, query: str) -> str:
        location_terms = [
            "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika",
            "kitengela", "ruaka", "kilimani", "kileleshwa", "lavington",
            "westlands", "parklands", "karen", "runda", "muthaiga",
            "kenya"
        ]
        simplified = query
        for term in location_terms:
            simplified = re.sub(rf"(?i)\b{re.escape(term)}\b", " ", simplified)
        simplified = re.sub(r"\s+", " ", simplified).strip().strip(",")
        return simplified or query

    @retry_sync(retries=2, delay=2.0, backoff=2.0, exceptions=(requests.RequestException,))
    def _call_api(self, params):
        return requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=20)

    def scrape(self, query: str, time_window_hours: int):
        # --- Advanced Query Builder ---
        intent_terms = [
            '"looking for"',
            '"need"',
            '"who sells"',
            '"anyone selling"',
            '"natafuta"',
            '"nahitaji"'
        ]
        
        geo_terms = [
            '"Nairobi"',
            '"Kenya"'
        ]
        
        # Make phone pattern optional in the query to increase recall
        expanded_query = f'({" OR ".join(intent_terms)}) {query} ({" OR ".join(geo_terms)})'
        
        logger.info(f"OUTBOUND CALL: Google CSE Scrape for {expanded_query} (Window: {time_window_hours}h)")
        
        date_restrict = "d1"
        if time_window_hours <= 24:
            date_restrict = "d1"
        elif time_window_hours <= 168:
            date_restrict = "w1"
        else:
            date_restrict = "m1"
            
        results = []
        max_retries = len(self.api_keys)
        
        # Try Official API First
        for attempt in range(max_retries):
            api_key = self.api_keys[self.current_key_index]
            # Skip obvious placeholders but allow real Google keys (they usually start with "AIza")
            if not api_key:
                logger.warning("Google CSE: Empty API key detected, skipping to fallback.")
                break
            if "your_key" in api_key or "placeholder" in api_key.lower():
                logger.warning("Google CSE: Placeholder key detected, skipping to fallback.")
                break
            if not self.cx:
                logger.warning("Google CSE: Missing CSE ID (GOOGLE_CSE_ID / GOOGLE_CX), skipping to fallback.")
                break

            params = {
                "q": expanded_query,
                "key": api_key,
                "cx": self.cx,
                "dateRestrict": date_restrict,
                "cr": "countryKE",
                "num": 10
            }
            
            try:
                response = self._call_api(params)
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("items", []):
                        snippet = item.get('snippet', '')
                        link = item.get('link', '')
                        title = item.get('title', '')
                        full_text = f"{title} {snippet}"
                        
                        # Extract contact info from snippet + link as requested
                        contact = self.extract_contact_info(f"{snippet} {link}")
                        
                        signal = ScraperSignal(
                            source=self.source,
                            text=full_text,
                            author="Google User",
                            contact=contact,
                            location="Kenya",
                            url=link,
                            timestamp=datetime.now(timezone.utc).isoformat()
                        )
                        results.append(signal.model_dump())
                    logger.info(f"Google CSE Scrape: Found {len(results)} results for {query} using key index {self.current_key_index}")
                    return results # Success!
                elif response.status_code in [403, 429]:
                    logger.warning(f"Google CSE Key {self.current_key_index} quota exceeded or invalid.")
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                else:
                    logger.error(f"Google CSE Error: {response.status_code} {response.text}")
            except Exception as e:
                logger.error(f"Google CSE Exception: {e}")
        
        # Fallback to DuckDuckGo (Simulating Google CSE)
        if not results:
            logger.info("Google CSE: All keys failed or returned 0 results. Falling back to DuckDuckGo proxy.")
            try:
                from ddgs import DDGS
                
                simplified = self._simplify_query(query)
                ddg_queries = [
                    f'site:kenyatalk.com OR site:wazua.co.ke "{simplified}" "looking for"',
                    f'site:t.me "{simplified}" Kenya "looking for"',
                    f"{simplified} Kenya",
                    f"{simplified} Nairobi",
                    simplified,
                    query
                ]
                if "car" in simplified.lower():
                    ddg_queries.append(simplified.lower().replace("car", "vehicle"))
                    ddg_queries.append("vehicle Kenya")
                if "apartment" in simplified.lower():
                    ddg_queries.append("apartment Kenya")
                    ddg_queries.append("apartments Kenya")
                if "water tank" in simplified.lower():
                    ddg_queries.append("water tank Kenya")
                    ddg_queries.append("water tanks Kenya")

                ddg_results = []
                for q in ddg_queries:
                    try:
                        ddg_results = list(DDGS().text(q, region='ke-en', max_results=20))
                    except Exception as e:
                        logger.warning(f"GoogleCSE Fallback failed for '{q}': {e}")
                        ddg_results = []
                    if not ddg_results:
                        try:
                            ddg_results = list(DDGS().text(q, region='ke-en', max_results=20, backend='html'))
                        except Exception:
                            ddg_results = []
                    if ddg_results:
                        break

                if not ddg_results:
                    try:
                        ddg_results = list(DDGS().text(simplified, region='wt-wt', max_results=20, backend='html'))
                    except Exception as e2:
                        logger.warning(f"GoogleCSE Fallback (Worldwide) failed: {e2}")
                        ddg_results = []
                
                for item in ddg_results:
                    title = item.get('title', '')
                    body = item.get('body', '')
                    href = item.get('href', '')
                    full_text = f"{title} {body}"
                    
                    signal = ScraperSignal(
                        source=self.source, # Keep source as google_cse for consistency
                        text=full_text,
                        author="DDG Proxy",
                        contact=self.extract_contact_info(full_text),
                        location="Kenya",
                        url=href,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    results.append(signal.model_dump())
                logger.info(f"Google CSE (DDG Fallback): Found {len(results)} results.")
            except Exception as e:
                logger.error(f"Google CSE Fallback failed: {e}")

        return results
