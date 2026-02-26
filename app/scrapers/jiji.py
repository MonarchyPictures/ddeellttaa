import logging
import time
import random
from datetime import datetime, timezone
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from app.scrapers.base_scraper import BaseScraper, ScraperSignal
from app.core.resilience import exponential_backoff
from app.core.proxy_manager import PROXY_MANAGER

logger = logging.getLogger(__name__)

class JijiScraper(BaseScraper):
    """
    Scraper for Jiji.co.ke (Kenya).
    Uses Playwright for dynamic content rendering.
    """
    
    BASE_URL = "https://jiji.co.ke"
    
    @exponential_backoff(retries=3, base_delay=2.0)
    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]:
        logger.info(f"🔎 JijiScraper starting search for: {query}")
        
        signals = []
        
        # Format query for URL
        formatted_query = query.replace(" ", "+")
        search_url = f"{self.BASE_URL}/search?query={formatted_query}"
        
        proxy_config = PROXY_MANAGER.get_playwright_proxy()
        
        with sync_playwright() as p:
            # Launch browser with proxy if available
            browser_args = {
                "headless": True,
                "args": ["--no-sandbox", "--disable-setuid-sandbox"]
            }
            if proxy_config:
                browser_args["proxy"] = proxy_config
                
            browser = p.chromium.launch(**browser_args)
            
            # Create context with rotated User Agent
            context = browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 1280, "height": 800}
            )
            
            page = context.new_page()
            
            try:
                logger.info(f"Visiting {search_url}")
                page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                
                # Check for CAPTCHA
                if page.query_selector("iframe[src*='captcha']") or \
                   page.query_selector("div.g-recaptcha") or \
                   "Verify you are human" in page.content():
                    logger.warning(f"⚠️ CAPTCHA detected on Jiji ({search_url}). Skipping as no solver is configured.")
                    return []

                # Wait for listings to load
                # Jiji listings usually have class starting with 'b-list-advert' or similar
                # We'll look for common container classes
                # Updated selectors for robustness
                selectors = [
                    "div.b-list-advert__gallery__item", 
                    "div.b-list-advert-base",
                    "div.qa-advert-list-item",
                    "div.masonry-item"
                ]
                
                found_selector = None
                for selector in selectors:
                    try:
                        if page.query_selector(selector):
                            found_selector = selector
                            break
                    except:
                        continue
                
                if found_selector:
                    logger.info(f"Found Jiji listings using selector: {found_selector}")
                    page.wait_for_selector(found_selector, timeout=10000)
                else:
                    logger.warning(f"Could not find any known Jiji listing selectors. Page title: {page.title()}")
                    # Dump a bit of content to debug
                    content_preview = page.content()[:500]
                    logger.warning(f"Page content preview: {content_preview}")
                
                # Scroll to load more (Jiji uses infinite scroll)
                for _ in range(2):
                    page.mouse.wheel(0, 1000)
                    time.sleep(1)
                
                # Extract Data
                items = page.query_selector_all(found_selector) if found_selector else []
                logger.info(f"Found {len(items)} items on Jiji page.")
                
                for item in items:
                    try:
                        # Extract title - Try multiple selectors
                        title = "Unknown Title"
                        for t_sel in [".qa-advert-title", ".b-list-advert-base__data__title", "div[class*='title']"]:
                            el = item.query_selector(t_sel)
                            if el:
                                title = el.inner_text().strip()
                                break
                        
                        # Extract price
                        price = "Contact for Price"
                        for p_sel in [".qa-advert-price", ".b-list-advert-base__data__price", "div[class*='price']"]:
                            el = item.query_selector(p_sel)
                            if el:
                                price = el.inner_text().strip()
                                break
                        
                        # Extract URL
                        full_url = ""
                        link_el = item.query_selector("a")
                        # Sometimes the item itself is the link or contains an 'a' tag
                        if not link_el and item.evaluate("node => node.tagName") == "A":
                            link_el = item
                            
                        if link_el:
                            relative_url = link_el.get_attribute("href")
                            if relative_url:
                                full_url = f"{self.BASE_URL}{relative_url}" if not relative_url.startswith("http") else relative_url

                        
                        # Extract Location & Region
                        region_el = item.query_selector(".b-list-advert__region__text")
                        location = region_el.inner_text().strip() if region_el else "Kenya"
                        
                        # Extract Description/Snippet (short)
                        snippet_el = item.query_selector(".b-list-advert__description-text")
                        snippet = snippet_el.inner_text().strip() if snippet_el else title
                        
                        # Create Signal
                        # Note: Phone number usually requires clicking "Show Contact", which is expensive.
                        # We'll skip deep scraping for now and just get the listing.
                        
                        signal = {
                            "source": "jiji.co.ke",
                            "text": f"{title} - {price} - {snippet}",
                            "title": title,
                            "price": price,
                            "author": "Jiji Seller", # Generic, difficult to get without visiting page
                            "contact": {
                                "phone": None, # Requires click
                                "whatsapp": None,
                                "email": None
                            },
                            "location": location,
                            "url": full_url,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        signals.append(signal)
                        
                    except Exception as e:
                        logger.warning(f"Error extracting Jiji item: {e}")
                        continue
                        
            except PlaywrightTimeoutError:
                logger.error("Timeout loading Jiji search page.")
                raise # Circuit breaker will catch this
            except Exception as e:
                logger.error(f"Jiji scraper error: {e}")
                raise
            finally:
                browser.close()
                
        return signals
