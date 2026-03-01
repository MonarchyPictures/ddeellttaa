
import logging
import httpx
import re
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.services.query_rewriter import build_buyer_query
from app.services.market_classifier import classify_market_side
from app.services.kenya_intent_engine import calculate_kenyan_intent_score as calculate_intent_score
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BUSINESS_DOMAINS = [
    # ".co.ke", # Too aggressive for Kenya
    # ".com/",  # Too aggressive
    "/shop",
    "/product",
    "/store",
    "jumia.co.ke",
    "kilimall.co.ke",
    "copia.co.ke",
]

def is_business_domain(url: str):
    return any(d in url.lower() for d in BUSINESS_DOMAINS)

class SerpAPIScraper(BaseScraper):
    
    def __init__(self):
        super().__init__()
        self.source = "serpapi_google"
        self._invalid_key_until = None

    def _get_serpapi_key(self) -> str:
        key = (settings.SERPAPI_KEY or "").strip()
        if not key:
            return ""
        lowered = key.lower()
        if any(token in lowered for token in ["placeholder", "replace_with", "your_key"]):
            return ""
        return key

    def _serpapi_temporarily_disabled(self) -> bool:
        return bool(self._invalid_key_until and datetime.now(timezone.utc) < self._invalid_key_until)

    def _build_params(self, query: str, location: str) -> Dict[str, Any]:
        if "kenya" not in location.lower() and "nairobi" not in location.lower():
             location = f"{location} Kenya"
             
        # transformed_query = build_buyer_query(query, location)
        # FORCE BUYER INTENT: Override rewriter with explicit buyer terms + negative seller terms
        # User Request: Stop scraping generic search results. Focus on Social/Forums.
        platforms = 'site:facebook.com/groups OR site:reddit.com OR site:kenyatalk.com OR site:wazua.co.ke OR site:jamiiforums.com'
        transformed_query = f'{platforms} {query} ("looking for" OR "want to buy" OR "wtb" OR "buying" OR "in search of" OR "natafuta") -seller -store -shop -dealer -price -supply'
        
        logger.info(f"Rewrote query: '{query}' -> '{transformed_query}'")
        
        return {
            "engine": settings.SERPAPI_ENGINE,
            "q": transformed_query,
            "api_key": self._get_serpapi_key(),
            "gl": "ke", # Force Kenya Region
            "hl": "en", # English
            "location": "Kenya", # Explicit location override for SerpAPI
            "num": 30, # Fetch more results to increase chance of finding buyers
        }

    def _process_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        organic_results = data.get("organic_results", [])

        logger.info(f"SerpAPI returned {len(organic_results)} organic results")

        for item in organic_results:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            url = item.get("link", "")
            text_blob = (title + " " + snippet)

            if is_business_domain(url):
                logger.info(f"Filtered (Business Domain): {url}")
                continue

            market_side = classify_market_side(text_blob)
            if market_side == "supply":
                 logger.info(f"Filtered (Supply Side): {title}")
                 continue  # kill seller pages
            
            # Additional Hard-coded Seller Filter
            lower_blob = text_blob.lower()
            if "price in kenya" in lower_blob or "store" in lower_blob or "shop" in lower_blob or "starts at" in lower_blob:
                 logger.info(f"Filtered (Strong Seller Signal): {title}")
                 continue

            results.append({
                "buyer_name": None,
                "title": title,
                "price": None,
                "location": "Kenya",
                "phone": self._extract_phone(snippet),
                "source": "serpapi_google",
                "intent_score": 0.4, 
                "url": item.get("link"),
            })

        return results

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

    def _fallback_ddg(self, query: str) -> List[Dict[str, Any]]:
        results = []
        try:
            from ddgs import DDGS

            platforms = 'site:facebook.com/groups OR site:reddit.com OR site:kenyatalk.com OR site:wazua.co.ke OR site:jamiiforums.com'
            simplified = self._simplify_query(query)
            ddg_queries = [
                f'{platforms} {simplified} "looking for"',
                f'{simplified} Kenya',
                f'{simplified} Nairobi',
                simplified,
                query
            ]
            if "car" in simplified.lower():
                ddg_queries.append(simplified.lower().replace("car", "vehicle"))
                ddg_queries.append("vehicle Kenya")
            if "water tank" in simplified.lower():
                ddg_queries.append("water tank Kenya")

            ddg_results = []
            for q in ddg_queries:
                ddg_results = list(DDGS().text(q, region='ke-en', max_results=30))
                if not ddg_results:
                    try:
                        ddg_results = list(DDGS().text(q, region='ke-en', max_results=30, backend='html'))
                    except Exception:
                        ddg_results = []
                if ddg_results:
                    break
            if not ddg_results:
                ddg_results = list(DDGS().text(simplified, region='wt-wt', max_results=30))
                if not ddg_results:
                    ddg_results = list(DDGS().text(simplified, region='wt-wt', max_results=30, backend='html'))

            for item in ddg_results:
                title = item.get('title', '')
                body = item.get('body', '')
                href = item.get('href', '')

                results.append({
                   "buyer_name": None,
                   "title": title,
                   "price": None,
                   "location": "Kenya",
                   "phone": self._extract_phone(body),
                   "source": "serpapi_google",
                   "intent_score": 0.4,
                   "url": href,
                })
            logger.info(f"SerpAPI (DDG Fallback): Found {len(results)} results.")
        except Exception as e:
            logger.error(f"SerpAPI Fallback failed: {e}")
        return results

    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]:
        """
        Sync implementation calling the search logic.
        """
        results = []
        
        # Check for placeholder key
        use_fallback = False
        if self._serpapi_temporarily_disabled():
            logger.warning("SerpAPI temporarily disabled after repeated auth failures; using fallback.")
            use_fallback = True
        elif not self._get_serpapi_key():
            logger.warning("SerpAPI: Placeholder key detected, skipping to fallback.")
            use_fallback = True
        else:
            params = self._build_params(query, "Kenya")
            try:
                with httpx.Client() as client:
                    response = client.get(
                        "https://serpapi.com/search",
                        params=params,
                        timeout=30
                    )
                    if response.status_code == 401:
                         logger.warning("SerpAPI: 401 Unauthorized. Invalid Key.")
                         self._invalid_key_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                         use_fallback = True
                    else:
                        response.raise_for_status()
                        data = response.json()
                        results = self._process_results(data)
            except Exception as e:
                logger.error(f"SerpAPI sync request failed: {e}")
                use_fallback = True

        if use_fallback or not results:
             logger.info("SerpAPI: Falling back to DuckDuckGo proxy.")
             results = self._fallback_ddg(query)
        
        return results

    async def search(self, query: str, location: str = "Kenya"):
        # 🛡️ CIRCUIT BREAKER CHECK
        if self.circuit_breaker.state == "OPEN":
             from datetime import datetime
             if (self.circuit_breaker.last_failure_time and (datetime.now().timestamp() - self.circuit_breaker.last_failure_time) > self.circuit_breaker.recovery_timeout):
                 self.circuit_breaker.state = "HALF_OPEN"
             else:
                 logger.warning(f"🔌 Circuit Breaker '{self.__class__.__name__}' OPEN. Skipping.")
                 return []

        if self._serpapi_temporarily_disabled():
            logger.warning("SerpAPI temporarily disabled after repeated auth failures; using fallback.")
            return self._fallback_ddg(query)

        if not self._get_serpapi_key():
            logger.warning("SERPAPI_KEY is not set. Using DDG fallback.")
            return self._fallback_ddg(query)

        params = self._build_params(query, location)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params=params,
                    timeout=30
                )
            if response.status_code == 401:
                logger.warning("SerpAPI: 401 Unauthorized. Using DDG fallback.")
                self._invalid_key_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                return self._fallback_ddg(query)
            response.raise_for_status()
            data = response.json()
            
            # 🛡️ CIRCUIT BREAKER SUCCESS
            if self.circuit_breaker.state == "HALF_OPEN":
                self.circuit_breaker.state = "CLOSED"
                self.circuit_breaker.failure_count = 0
            
            return self._process_results(data)
                
        except Exception as e:
            logger.error(f"SerpAPI request failed: {e}")
            # 🛡️ CIRCUIT BREAKER FAILURE
            self.circuit_breaker.failure_count += 1
            from datetime import datetime
            self.circuit_breaker.last_failure_time = datetime.now().timestamp()
            if self.circuit_breaker.failure_count >= self.circuit_breaker.failure_threshold:
                self.circuit_breaker.state = "OPEN"
            return self._fallback_ddg(query)

    def _extract_price(self, text: str) -> str:
        match = re.search(r'(?:Ksh|KES)\.?\s*([\d,]+)', text, re.IGNORECASE)
        return match.group(0) if match else ""

    def _extract_phone(self, text: str) -> str:
        # Match +254..., 07..., 01..., 7..., 1...
        # Same as search_service.py extract_phone
        match = re.search(r'(\+?254|0)?([17]\d{8})', text)
        return match.group(0) if match else None

    def transform_query(self, query):
        if any(k in query.lower() for k in BUYER_PATTERNS):
            return query
        return f"looking for {query} {settings.SERPAPI_REGION.upper()}"

    def is_buyer(self, title):
        # Even with "looking for" in query, Google can return e-commerce product pages.
        # We need to filter out obvious seller titles.
        
        lower_title = title.lower()
        
        # Explicit SELLER keywords to reject
        SELLER_KEYWORDS = [
            "for sale", "buy online", "price in kenya", "shop online", 
            "store", "add to cart", "checkout", "selling", "best price",
            "discount", "offer"
        ]
        
        # If it explicitly says "looking for" or "wanted", we accept it even if it has price info
        # e.g. "Looking for iPhone 13 - Best Price" -> Accept
        if any(p in lower_title for p in BUYER_PATTERNS):
            return True
            
        # Otherwise, if it has seller keywords, REJECT it.
        if any(s in lower_title for s in SELLER_KEYWORDS):
            return False
            
        # If neutral (no buyer or seller keywords), we accept it because the query was strong.
        # But maybe we should be skeptical?
        # Let's trust it for now but the intent scorer will lower its score if it looks like a product.
        return True
