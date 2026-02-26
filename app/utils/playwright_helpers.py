from playwright.sync_api import sync_playwright
import logging

logger = logging.getLogger(__name__)

def get_page_content(url, wait_selector=None, user_agent=None):
    """
    Utility to fetch page content using Playwright.
    Handles cookie consent and waiting for selectors.
    """
    print("Navigating to:", url)
    if not user_agent:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        
    logger.info(f"PLAYWRIGHT: Fetching {url}")
    try:
        with sync_playwright() as p:
            # Use a shorter launch timeout and specify chromium
            browser = p.chromium.launch(headless=True, timeout=30000)
            context = browser.new_context(
                user_agent=user_agent,
                viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()
            
            # Set default timeout for all actions
            page.set_default_timeout(30000)
            
            try:
                # Use "domcontentloaded" instead of "networkidle" for speed
                response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                if response and response.status == 429:
                    logger.warning(f"PLAYWRIGHT: Rate limited (429) at {url}")
                    return None

                if "google.com" in url:
                    try:
                        # Faster check for consent
                        consent_btn = page.query_selector('button:has-text("Accept all"), button:has-text("I agree"), button:has-text("Accept everything")')
                        if consent_btn:
                            consent_btn.click()
                            # Don't wait too long after click
                            page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except:
                        pass
                
                # 📜 Scroll to Load More Content (Handles lazy-loading)
                print(f"Scrolling to load content for {url}...")
                for i in range(3):
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    page.wait_for_timeout(3000) # wait for content to load

                if wait_selector:
                    try:
                        # Primary selector
                        page.wait_for_selector(wait_selector, timeout=15000)
                    except Exception as e:
                        print(f"Primary selector '{wait_selector}' failed, trying fallback...")
                        try:
                            # Fallback for dynamic layout
                            page.wait_for_selector("[role='main'], [role='presentation'], .main-content, #main", timeout=15000)
                        except Exception as fe:
                            print("PLAYWRIGHT ERROR (fallback):", str(fe))
                            logger.warning(f"PLAYWRIGHT: Both primary and fallback selectors failed at {url}")
                
                return page.content()
            except Exception as e:
                print("PLAYWRIGHT ERROR (page_op):", str(e))
                logger.error(f"PLAYWRIGHT: Page operation error at {url}: {str(e)}")
                return None
            finally:
                browser.close()
    except Exception as e:
        print("PLAYWRIGHT ERROR (browser_launch):", str(e))
        logger.error(f"PLAYWRIGHT: Browser launch/context error: {str(e)}")
        return None
