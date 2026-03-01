# app/scrapers/registry.py
# ============================================================
# SCRAPER REGISTRY — Priority-ordered, single registration
# ============================================================
# Priority order (highest first):
# 1. SerpAPI (1000)
# 2. Google CSE (950)
# 3. Telegram (900)
# 4. Facebook Groups (800)
# 5. Kenyan Forums (700)
# 6. Twitter (650)
# 7. Jiji (500)
# 8. PigiaMe (500)
# 9. Google Maps (400)
# 10. WhatsApp (350)
# 11. DuckDuckGo (100)  ← LAST (fallback only)
# ============================================================

import logging
from app.config.runtime import SCRAPER_PRIORITIES

logger = logging.getLogger(__name__)

# --- Single Registry Storage ---
SCRAPER_REGISTRY = {}
SCRAPER_PRIORITY = {}
ACTIVE_SCRAPERS = set()

# --- Scraper Classification ---
# Light scrapers: Fast, low memory, API-based
LIGHT_SCRAPERS = {
    "duckduckgo", "serpapi", "google_cse", "telegram",
    "yahoo", "yandex", "brave"  # Alternative search engines
}

# Heavy scrapers: Playwright-based, high memory, slow
HEAVY_SCRAPERS = {"facebook", "facebook_groups", "twitter", "jiji", "pigiame", "google_maps", "whatsapp_groups", "kenyan_forums"}


def get_scraper_name(scraper_instance) -> str | None:
    """Get scraper name from instance by reverse lookup."""
    for name, registered_scraper in SCRAPER_REGISTRY.items():
        if registered_scraper is scraper_instance:
            return name
    return None


def get_scraper_weight(name: str) -> str:
    """Return 'light' or 'heavy' for a scraper name."""
    if name in LIGHT_SCRAPERS:
        return "light"
    return "heavy"


def register_scraper(name, scraper, priority=None):
    """Register a scraper. Priority from config if not specified."""
    import os
    # OPTIONAL: Limit scrapers via env var (opt-in, not default)
    if os.getenv("LIMIT_SCRAPERS") == "true":
        allowed = {"duckduckgo", "serpapi", "google_cse"}
        if name not in allowed:
            logger.warning(f"LIMIT_SCRAPERS mode: Skipping {name}")
            return
    
    if priority is None:
        priority = SCRAPER_PRIORITIES.get(name, 10)
    if name in SCRAPER_REGISTRY:
        logger.warning(f"Replacing existing scraper registration for '{name}'")
    SCRAPER_REGISTRY[name] = scraper
    SCRAPER_PRIORITY[name] = priority
    ACTIVE_SCRAPERS.add(name)
    logger.info(f"✅ Registered: {name} (priority={priority})")


def enable_scraper(name):
    if name in SCRAPER_REGISTRY:
        ACTIVE_SCRAPERS.add(name)


def disable_scraper(name):
    ACTIVE_SCRAPERS.discard(name)


def get_active_scrapers_sorted():
    """
    Get active scrapers sorted by PRIORITY (highest first).
    SerpAPI runs first, DuckDuckGo runs last.
    """
    active = [name for name in ACTIVE_SCRAPERS if name in SCRAPER_REGISTRY]
    scrapers = sorted(
        [SCRAPER_REGISTRY[name] for name in active],
        key=lambda s: SCRAPER_PRIORITY.get(get_scraper_name(s), 10),
        reverse=True
    )

    names = [get_scraper_name(s) for s in scrapers]
    logger.info(f"📋 Scraper execution order ({len(scrapers)}): {names}")
    return scrapers


def get_active_scrapers():
    return get_active_scrapers_sorted()


# ============================================================
# REGISTER SCRAPERS IN PRIORITY ORDER
# ============================================================
# TIER 1: Premium APIs (run FIRST)
# ============================================================

try:
    from .serpapi_scraper import SerpAPIScraper
    register_scraper("serpapi", SerpAPIScraper(), priority=1000)
    logger.info("🥇 TIER 1: SerpAPI registered (priority=1000)")
except Exception as e:
    logger.warning(f"Could not load SerpAPIScraper: {e}")

# ============================================================
# TIER 1b: Alternative Search Engines (Google alternatives)
# Priority: Yahoo > Yandex > Brave > Google (fallback)
# ============================================================

try:
    from .yahoo import YahooScraper
    register_scraper("yahoo", YahooScraper(), priority=920)
    logger.info("🌐 TIER 1b: Yahoo Search registered (priority=920)")
except Exception as e:
    logger.warning(f"Could not load YahooScraper: {e}")

try:
    from .yandex import YandexScraper
    register_scraper("yandex", YandexScraper(), priority=910)
    logger.info("🌐 TIER 1b: Yandex Search registered (priority=910)")
except Exception as e:
    logger.warning(f"Could not load YandexScraper: {e}")

try:
    from .brave import BraveScraper
    register_scraper("brave", BraveScraper(), priority=900)
    logger.info("🌐 TIER 1b: Brave Search registered (priority=900)")
except Exception as e:
    logger.warning(f"Could not load BraveScraper: {e}")

# Google CSE - now lower priority as fallback (fragile in Kenya)
try:
    from .google_cse import GoogleCSEScraper
    register_scraper("google_cse", GoogleCSEScraper(), priority=850)
    logger.info("🔍 TIER 1b: Google CSE registered (priority=850) — FALLBACK")
except Exception as e:
    logger.warning(f"Could not load GoogleCSEScraper: {e}")

# ============================================================
# TIER 2: Telegram (run SECOND — highest quality buyers)
# ============================================================

try:
    from app.config.runtime import ENABLE_TELEGRAM
    if ENABLE_TELEGRAM:
        # Telegram scraper uses the engine module
        # It's registered but may need credentials to actually work
        try:
            from .telegram import TelegramScraper
            register_scraper("telegram", TelegramScraper())
            logger.info("🥈 TIER 2: Telegram registered (priority=900)")
        except ImportError:
            # Create a lightweight DDG-based Telegram scraper as fallback
            logger.info("🥈 TIER 2: Telegram module not found, will use DDG-based search")
except Exception as e:
    logger.warning(f"Telegram setup: {e}")

# ============================================================
# TIER 3: Social Platform Scrapers
# ============================================================

try:
    from .facebook_groups_scraper import FacebookGroupsScraper
    register_scraper("facebook_groups", FacebookGroupsScraper())
    logger.info("🥉 TIER 3: Facebook Groups registered (priority=800)")
except ImportError:
    # Fall back to existing Facebook scraper
    try:
        from .facebook_marketplace import FacebookMarketplaceScraper
        register_scraper("facebook", FacebookMarketplaceScraper())
        logger.info("🥉 TIER 3: Facebook Marketplace registered (priority=750)")
    except Exception as e:
        logger.warning(f"Could not load Facebook scraper: {e}")

try:
    from .kenyan_forums import KenyanForumsScraper
    register_scraper("kenyan_forums", KenyanForumsScraper())
    logger.info("🥉 TIER 3: Kenyan Forums registered (priority=700)")
except ImportError:
    logger.info("Kenyan Forums scraper not found, skipping")

try:
    from .twitter import TwitterScraper
    register_scraper("twitter", TwitterScraper())
    logger.info("🥉 TIER 3: Twitter registered (priority=650)")
except ImportError:
    logger.info("Twitter scraper not found, skipping")

# ============================================================
# TIER 4: Marketplace Scrapers
# ============================================================

try:
    from .jiji import JijiScraper
    register_scraper("jiji", JijiScraper())
    logger.info("📦 TIER 4: Jiji registered (priority=500)")
except Exception as e:
    logger.warning(f"Could not load JijiScraper: {e}")

try:
    from .pigiame import PigiaMeScraper
    register_scraper("pigiame", PigiaMeScraper())
    logger.info("📦 TIER 4: PigiaMe registered (priority=500)")
except Exception as e:
    logger.warning(f"Could not load PigiaMeScraper: {e}")

# ============================================================
# TIER 5: Discovery Scrapers
# ============================================================

try:
    from .google_maps import GoogleMapsScraper
    register_scraper("google_maps", GoogleMapsScraper())
    logger.info("🗺️ TIER 5: Google Maps registered (priority=400)")
except Exception as e:
    logger.warning(f"Could not load GoogleMapsScraper: {e}")

try:
    from .whatsapp_public_groups import WhatsAppPublicGroupScraper
    register_scraper("whatsapp_groups", WhatsAppPublicGroupScraper())
    logger.info("💬 TIER 5: WhatsApp Groups registered (priority=350)")
except Exception as e:
    logger.warning(f"Could not load WhatsAppPublicGroupScraper: {e}")

# ============================================================
# TIER 6: DuckDuckGo (LAST — fallback only)
# ============================================================

try:
    from .duckduckgo import DuckDuckGoScraper
    register_scraper("duckduckgo", DuckDuckGoScraper())
    logger.info("🔍 TIER 6: DuckDuckGo registered (priority=100) — FALLBACK")
except Exception as e:
    logger.warning(f"Could not load DuckDuckGoScraper: {e}")


# ============================================================
# SUMMARY
# ============================================================
logger.info(f"\n{'='*50}")
logger.info(f"SCRAPER REGISTRY SUMMARY")
logger.info(f"{'='*50}")
logger.info(f"Total registered: {len(SCRAPER_REGISTRY)}")
logger.info(f"Active: {len(ACTIVE_SCRAPERS)}")
for name in sorted(ACTIVE_SCRAPERS, key=lambda n: SCRAPER_PRIORITY.get(n, 0), reverse=True):
    p = SCRAPER_PRIORITY.get(name, 0)
    tier = "TIER 1" if p >= 900 else "TIER 2" if p >= 800 else "TIER 3" if p >= 600 else "TIER 4" if p >= 400 else "TIER 5" if p >= 300 else "TIER 6"
    logger.info(f"  {tier} [{p:>4}] {name}")
logger.info(f"{'='*50}\n")


# --- Backward Compatibility ---
def update_scraper_state(name, state, ttl_minutes=None, caller=None):
    is_active = state if isinstance(state, bool) else (state == "active")
    if name not in SCRAPER_REGISTRY:
        return False, f"Scraper '{name}' not found."
    if is_active:
        enable_scraper(name)
    else:
        disable_scraper(name)
    return True, f"Scraper '{name}' {'enabled' if is_active else 'disabled'}."


def update_scraper_mode(name, mode, caller=None):
    if name not in SCRAPER_REGISTRY:
        return False, f"Scraper '{name}' not found."
    return True, f"Scraper '{name}' mode updated to '{mode}'."


def refresh_scraper_states():
    pass
