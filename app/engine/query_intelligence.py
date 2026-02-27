# app/engine/query_intelligence.py
# ============================================================
# QUERY INTELLIGENCE ENGINE
# ============================================================
# Takes what you're selling and generates search queries
# that will find people LOOKING TO BUY that exact thing.
#
# Input:  "2br apartment kileleshwa"
# Output: 15+ targeted search queries across platforms
# ============================================================

import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)


# Category detection patterns
CATEGORY_PATTERNS = {
    "real_estate": {
        "keywords": [
            "apartment", "house", "flat", "bedsitter", "studio", "1br", "2br", "3br",
            "4br", "bedroom", "bdr", "bd", "plot", "land", "acre", "office",
            "warehouse", "godown", "shop space", "commercial", "residential",
            "rent", "let", "lease", "buy home", "property"
        ],
        "buyer_phrases": [
            "looking for {q}", "natafuta {q}", "need {q} in {loc}",
            "house hunting {q} {loc}", "anyone know {q} near {loc}",
            "relocating to {loc} need {q}", "moving to {loc} {q}",
            "{q} wanted {loc}", "recommend {q} {loc}",
            "budget for {q} {loc}", "affordable {q} {loc}",
            "tenant looking for {q}", "nahama natafuta {q} {loc}",
            "urgent house for sale {loc}", "cheap plot for sale {loc}",
            "apartments for rent {loc} budget", "hostel near {loc}",
            "airbnb {loc}", "office space {loc} price", "land for sale {loc}"
        ],
        "platforms": ["facebook", "twitter", "kenyan_forums", "telegram", "whatsapp_groups"],
        "negative_terms": ["-agent", "-agency", "-realtor", "-broker fees"]
    },
    "vehicles": {
        "keywords": [
            "car", "vehicle", "toyota", "nissan", "subaru", "isuzu", "mazda",
            "honda", "mitsubishi", "prado", "vitz", "hilux", "forester",
            "truck", "pickup", "van", "bus", "motorbike", "boda",
            "spare parts", "engine", "gearbox", "tyre", "rim"
        ],
        "buyer_phrases": [
            "looking for {q}", "natafuta {q}", "WTB {q} {loc}",
            "buying {q} cash", "need {q} urgently", "who is selling {q}",
            "anyone selling {q} {loc}", "cash buyer for {q}",
            "budget for {q}", "second hand {q} {loc}",
            "{q} wanted {loc}", "used {q} {loc} budget",
            "i need {q} in {loc}", "looking to buy {q} in {loc}",
            "where can i buy {q} in {loc}", "ready to buy {q} {loc}",
            "buying used {q} from owner {loc}", "need {q} seller in {loc}",
            "budget {price} for {q} in {loc}", "want {q} with logbook {loc}"
        ],
        "platforms": ["facebook_groups", "twitter", "kenyan_forums", "jiji_wanted"],
        "negative_terms": ["-dealer", "-showroom", "-import"]
    },
    "electronics": {
        "keywords": [
            "phone", "laptop", "iphone", "samsung", "macbook", "dell",
            "hp", "lenovo", "tablet", "ipad", "tv", "television",
            "speaker", "headphone", "airpods", "ps5", "xbox", "gaming",
            "camera", "printer", "monitor"
        ],
        "buyer_phrases": [
            "looking for {q}", "WTB {q} {loc}", "need {q} urgently",
            "anyone selling {q}", "who has {q} for sale",
            "buying {q} cash {loc}", "budget for {q}",
            "second hand {q} {loc}", "used {q} good condition",
            "natafuta {q}", "cheap {q} {loc}",
            "price of {q} in {loc}", "best shop for {q} {loc}",
            "screen replacement for {q}", "charger for {q} original",
            "swap {q} with", "refurbished {q} {loc}",
            "gaming pc specs {q}", "camera lens for {q}"
        ],
        "platforms": ["facebook_groups", "twitter", "reddit", "jiji_wanted"],
        "negative_terms": ["-store", "-shop", "-official"]
    },
    "services": {
        "keywords": [
            "plumber", "electrician", "carpenter", "painter", "mechanic",
            "mover", "cleaner", "driver", "tutor", "teacher", "trainer",
            "photographer", "caterer", "event", "dj", "designer",
            "developer", "consultant", "lawyer", "accountant", "doctor"
        ],
        "buyer_phrases": [
            "looking for {q} in {loc}", "need {q} urgently",
            "recommend {q} {loc}", "anyone know a good {q}",
            "natafuta {q} {loc}", "who knows a {q}",
            "affordable {q} {loc}", "reliable {q} {loc}",
            "best {q} in {loc}", "hiring {q}",
            "how much for {q} services", "cheap {q} {loc}",
            "urgent {q} needed", "looking for experienced {q}",
            "contractor for {q}", "repair {q} near me",
            "professional {q} {loc}"
        ],
        "platforms": ["facebook_groups", "twitter", "google", "kenyan_forums"],
        "negative_terms": []
    },
    "construction": {
        "keywords": [
            "water tank", "water tanks", "tank", "pipe", "pipes", "pvc",
            "hdpe", "fittings", "valve", "pump", "cement", "sand", "ballast",
            "blocks", "bricks", "steel", "rebar", "hardware", "plumbing"
        ],
        "buyer_phrases": [
            "looking for {q} in {loc}", "need {q} urgently {loc}",
            "anyone selling {q} near {loc}", "WTB {q} {loc}",
            "natafuta {q} {loc}", "budget for {q} {loc}",
            "who has {q} in stock {loc}", "need supplier for {q} {loc}",
            "{q} wanted {loc}", "ready to buy {q} {loc}"
        ],
        "platforms": ["facebook", "kenyan_forums", "twitter", "google", "duckduckgo", "telegram"],
        "negative_terms": ["-dealer", "-official store", "-cart", "-checkout", "-classifieds"]
    },
    "fashion": {
        "keywords": [
            "shoe", "shoes", "sneaker", "sneakers", "heels", "boot", "boots",
            "sandals", "dress", "shirt", "trouser", "jeans", "bag", "handbag", "fashion"
        ],
        "buyer_phrases": [
            "looking for {q} in {loc}", "need {q} urgently {loc}",
            "WTB {q} {loc}", "anyone selling {q} {loc}",
            "natafuta {q} {loc}", "ready to buy {q}",
            "budget for {q} {loc}", "where can i buy {q} {loc}"
        ],
        "platforms": ["facebook", "twitter", "duckduckgo", "google", "telegram"],
        "negative_terms": ["-wholesale supplier", "-official store", "-catalog"]
    },
    "general": {
        "keywords": [],
        "buyer_phrases": [
            "looking for {q}", "need {q}", "WTB {q}",
            "anyone selling {q}", "where can I buy {q} {loc}",
            "natafuta {q}", "nahitaji {q}",
            "who has {q}", "buying {q} {loc}",
            "{q} wanted", "recommend {q} {loc}",
            "budget for {q} {loc}",
            "best place to buy {q}", "price of {q} kenya"
        ],
        "platforms": ["facebook", "twitter", "duckduckgo", "google", "kenyan_forums"],
        "negative_terms": []
    }
}

# Platform-specific search templates
PLATFORM_SEARCH_TEMPLATES = {
    "facebook_groups": [
        'site:facebook.com/groups {buyer_phrase}',
        'site:facebook.com {buyer_phrase} "looking for"',
        'site:facebook.com {buyer_phrase} "natafuta"',
        'site:facebook.com/groups "{q}" {loc} ("need" OR "budget" OR "looking for")',
    ],
    "twitter": [
        'site:twitter.com {buyer_phrase}',
        'site:x.com {buyer_phrase}',
        'site:twitter.com "{q}" {loc} ("need" OR "looking for" OR "DM")',
    ],
    "reddit": [
        'site:reddit.com {buyer_phrase}',
        'site:reddit.com/r/Kenya "{q}" ("looking for" OR "need" OR "recommend")',
    ],
    "kenyan_forums": [
        'site:kenyatalk.com {buyer_phrase}',
        'site:wazua.co.ke {buyer_phrase}',
        'site:jamiiforums.com "{q}" Kenya',
        'site:kenyatalk.com "{q}" ("looking for" OR "natafuta" OR "need")',
    ],
    "whatsapp": [
        'site:chat.whatsapp.com "{q}" Kenya',
        'site:chat.whatsapp.com {loc} "{q}"',
    ],
    "google": [
        '{buyer_phrase}',
        '"{q}" {loc} ("looking for" OR "need" OR "wanted")',
    ],
    "duckduckgo": [
        '{buyer_phrase}',
        '"{q}" {loc} ("looking for" OR "need" OR "anyone selling")',
    ],
    "jiji_wanted": [
        'site:jiji.co.ke "wanted" "{q}"',
        'site:jiji.co.ke "looking for" "{q}"',
    ],
    "telegram": [
        'site:t.me "{q}" Kenya',
        'site:t.me "{q}" {loc} ("buy" OR "need")',
    ]
}


class QueryIntelligenceEngine:
    """
    Takes what you're selling and generates targeted search queries
    to find people looking to BUY that thing.
    """

    def __init__(self):
        self.categories = CATEGORY_PATTERNS
        self.platform_templates = PLATFORM_SEARCH_TEMPLATES

    def detect_category(self, query: str) -> str:
        """Detect what category the product/service falls into."""
        query_lower = query.lower()

        for category, config in self.categories.items():
            if category == "general":
                continue
            if any(kw in query_lower for kw in config["keywords"]):
                logger.info(f"Category detected: {category} for '{query}'")
                return category

        logger.info(f"Category: general for '{query}'")
        return "general"

    def generate_buyer_phrases(self, query: str, location: str, category: str) -> List[str]:
        """Generate buyer-intent phrases for the query."""
        config = self.categories.get(category, self.categories["general"])
        phrases = []

        format_vars = {
            "q": query,
            "loc": location,
            # Some category templates include {price}; provide a safe default.
            "price": "budget",
        }

        sellerish_markers = [
            "for sale", "dealer", "dealers", "showroom", "shop", "store",
            "importing", "wholesale", "supplier", "stock available", "catalog",
        ]

        for template in config["buyer_phrases"]:
            lower_template = template.lower()
            if any(marker in lower_template for marker in sellerish_markers):
                continue
            phrase = template.format(**format_vars)
            phrases.append(phrase)

        return phrases

    def generate_search_plan(self, query: str, location: str = "Kenya") -> Dict:
        """
        Generate a complete search plan with queries for each platform.

        Returns:
        {
            "category": "real_estate",
            "platforms": {
                "facebook_groups": ["query1", "query2", ...],
                "twitter": ["query1", "query2", ...],
                ...
            },
            "buyer_phrases": ["looking for 2br...", ...],
            "negative_terms": ["-agent", ...]
        }
        """
        category = self.detect_category(query)
        config = self.categories.get(category, self.categories["general"])
        buyer_phrases = self.generate_buyer_phrases(query, location, category)

        plan = {
            "category": category,
            "original_query": query,
            "location": location,
            "platforms": {},
            "buyer_phrases": buyer_phrases,
            "negative_terms": config.get("negative_terms", []),
            "total_queries": 0
        }

        # Generate platform-specific queries
        target_platforms = list(config.get("platforms", ["duckduckgo", "google"]))
        # Always include broad web fallback platforms so category-specific scraper
        # failures do not result in 0 scanned signals.
        for fallback_platform in ("google", "duckduckgo"):
            if fallback_platform not in target_platforms:
                target_platforms.append(fallback_platform)

        for platform in target_platforms:
            templates = self.platform_templates.get(platform, [])
            platform_queries = []

            for template in templates:
                # Use first 3 buyer phrases per template to avoid too many queries
                for bp in buyer_phrases[:3]:
                    search_query = template.format(
                        buyer_phrase=bp,
                        q=query,
                        loc=location
                    )
                    # Add negative terms
                    for neg in config.get("negative_terms", []):
                        search_query += f" {neg}"

                    platform_queries.append(search_query)

            # Also add a simple direct query per platform
            platform_queries.append(f'"{query}" {location} "looking for"')
            platform_queries.append(f'"{query}" {location} "natafuta"')

            # Deduplicate
            platform_queries = list(dict.fromkeys(platform_queries))
            plan["platforms"][platform] = platform_queries[:10]  # Max 10 per platform
            plan["total_queries"] += len(plan["platforms"][platform])

        logger.info(
            f"Search Plan: category={category}, "
            f"platforms={len(plan['platforms'])}, "
            f"total_queries={plan['total_queries']}"
        )

        return plan


# Singleton
QUERY_ENGINE = QueryIntelligenceEngine()
