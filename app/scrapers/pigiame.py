import logging
import time
import random
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright

from app.scrapers.base_scraper import BaseScraper, ScraperSignal
from app.core.resilience import exponential_backoff
from app.core.proxy_manager import PROXY_MANAGER

logger = logging.getLogger(__name__)

class PigiaMeScraper(BaseScraper):
    """
    Scraper for PigiaMe.co.ke (Kenya).
    Uses Playwright for dynamic content rendering.
    """
    
    BASE_URL = "https://www.pigiame.co.ke"
    
    @exponential_backoff(retries=3, base_delay=2.0)
    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]:
        logger.info(f"🔎 PigiaMeScraper starting search for: {query}")
        
        # PigiaMe uses 'q' parameter
        formatted_query = query.replace(" ", "+")
        search_url = f"{self.BASE_URL}/classifieds?q={formatted_query}"
        
        proxy_config = PROXY_MANAGER.get_playwright_proxy()
        
        results = []
        
        with sync_playwright() as p:
            browser_args = {
                "headless": True,
                "args": ["--no-sandbox", "--disable-setuid-sandbox"]
            }
            if proxy_config:
                browser_args["proxy"] = proxy_config
                
            browser = p.chromium.launch(**browser_args)
            context = browser.new_context(user_agent=self.user_agent)
            page = context.new_page()
            
            try:
                logger.info(f"Visiting {search_url}")
                page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                
                # Check for CAPTCHA
                if page.query_selector("iframe[src*='captcha']") or \
                   "cloudflare" in page.content().lower() or \
                   "human verification" in page.content().lower():
                    logger.warning(f"⚠️ CAPTCHA/Cloudflare detected on PigiaMe ({search_url}). Skipping.")
                    return []

                # Wait for listings
                try:
                    page.wait_for_selector("div.listing-card", timeout=10000)
                except:
                    logger.warning("Timeout waiting for PigiaMe listings. Page might be empty.")
                
                # Extract Data
                items = page.query_selector_all("div.listing-card")
                logger.info(f"Found {len(items)} items on PigiaMe.")
                
                for item in items:
                    try:
                        title_el = item.query_selector(".listing-card__header__title")
                        title = title_el.inner_text().strip() if title_el else "Unknown Title"
                        
                        price_el = item.query_selector(".listing-card__price__value")
                        price = price_el.inner_text().strip() if price_el else "Contact for Price"
                        
                        link_el = item.query_selector("a.listing-card__inner-link")
                        relative_url = link_el.get_attribute("href") if link_el else None
                        full_url = f"{relative_url}" if relative_url else ""
                        if full_url and not full_url.startswith("http"):
                            full_url = f"{self.BASE_URL}{full_url}"
                        
                        loc_el = item.query_selector(".listing-card__header__location")
                        location = loc_el.inner_text().strip() if loc_el else "Kenya"
                        
                        # Create Signal
                        signal = ScraperSignal(
                            source="pigiame",
                            text=f"{title} - {price} - {location}",
                            url=full_url,
                            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                            location=location
                        )
                        results.append(signal.model_dump())
                        
                    except Exception as e:
                        logger.error(f"Error parsing PigiaMe item: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"PigiaMe Scrape Error: {e}")
            finally:
                browser.close()
                
        return results
