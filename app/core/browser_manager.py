"""
Browser Manager - Production-Ready Playwright for Railway

Provides a singleton browser instance with Railway-safe Chromium flags.
Reuses browser across requests to minimize memory usage.
"""
import asyncio
import logging
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)

# Global singleton instances
_browser: Browser = None
_playwright = None
_lock = asyncio.Lock()

# Railway-safe Chromium flags
RAILWAY_CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-setuid-sandbox",
    "--no-first-run",
    "--no-zygote",
    "--single-process",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-client-side-phishing-detection",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-features=TranslateUI",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-renderer-backgrounding",
    "--force-color-profile=srgb",
    "--metrics-recording-only",
    "--mute-audio",
]


async def get_browser() -> Browser:
    """
    Get or create the singleton browser instance.
    Thread-safe. Reuses existing browser if available.
    """
    global _browser, _playwright

    if _browser and _browser.is_connected():
        return _browser

    async with _lock:
        # Double-check after acquiring lock
        if _browser and _browser.is_connected():
            return _browser

        logger.info("Starting Chromium browser with Railway-safe flags...")
        
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=RAILWAY_CHROMIUM_ARGS
        )
        
        logger.info("Browser started successfully")
        return _browser


async def new_page(block_media: bool = True, timeout_ms: int = 15000) -> Page:
    """
    Create a new page with production optimizations.
    
    Args:
        block_media: Block images, fonts, media to reduce bandwidth/memory
        timeout_ms: Default timeout for operations (15s default)
    """
    browser = await get_browser()
    page = await browser.new_page()
    
    # Set strict timeout
    page.set_default_timeout(timeout_ms)
    page.set_default_navigation_timeout(timeout_ms)
    
    # Block unnecessary resources
    if block_media:
        await page.route("**/*", lambda route: (
            route.abort()
            if route.request.resource_type in ["image", "media", "font", "stylesheet"]
            else route.continue_()
        ))
    
    return page


async def close_page(page: Page):
    """
    Close a page properly. Does NOT close the browser (kept for reuse).
    """
    try:
        if page and not page.is_closed():
            await page.close()
    except Exception as e:
        logger.debug(f"Error closing page: {e}")


async def close_browser():
    """
    Close the global browser instance.
    Call this on shutdown.
    """
    global _browser, _playwright

    async with _lock:
        if _browser:
            try:
                await _browser.close()
                logger.info("Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            _browser = None
        
        if _playwright:
            try:
                await _playwright.stop()
            except Exception as e:
                logger.error(f"Error stopping playwright: {e}")
            _playwright = None
