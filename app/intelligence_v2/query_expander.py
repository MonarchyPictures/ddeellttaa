
from typing import List, Optional
import random

def expand_query(product: str, location: str = "Kenya", category: Optional[str] = None) -> List[str]:
    """
    Expands a simple product/location pair into a high-yield search matrix (15+ queries).
    Targets specific platforms and buyer intent keywords.
    """
    if not product:
        return []

    queries = []

    # --- 1. CORE INTENT (High Precision) ---
    core_intents = [
        f'"{product}"',
        f'"{product}" {location}',
        f'"{product}" for sale {location}',
        f'buy "{product}" {location}',
        f'price of "{product}" in {location}',
    ]
    queries.extend(core_intents)

    # --- 2. BUYER SIGNALS (High Recall) ---
    buyer_phrases = [
        "looking for",
        "want to buy",
        "wtb",
        "need",
        "anyone selling",
        "where can i buy",
        "recommendations for",
        "best place to buy",
        "budget for"
    ]
    for phrase in buyer_phrases:
        queries.append(f'{phrase} "{product}" {location}')

    # --- 3. LOCAL SIGNALS (Swahili/Sheng) ---
    local_phrases = [
        "natafuta",
        "nahitaji",
        "nani anauza",
        "bei ya",
        "anauza",
        "sokoni"
    ]
    for phrase in local_phrases:
        queries.append(f'{phrase} "{product}" {location}')

    # --- 4. PLATFORM SPECIFIC (Targeting Social Dorks) ---
    # These are powerful for Google/DDG scrapers
    platforms = [
        ("site:facebook.com", "groups"),
        ("site:twitter.com", "status"),
        ("site:reddit.com", "comments"),
        ("site:instagram.com", "post"),
        ("site:tiktok.com", "video"),
        ("site:kenyatalk.com", "thread"),
        ("site:wazua.co.ke", "topic"),
        ("site:jamiiforums.com", "thread")
    ]
    
    # Add a few high-value platform queries
    for site, _ in platforms:
        queries.append(f'{site} "{product}" {location}')
        queries.append(f'{site} "{product}" "looking for"')

    # --- 5. CATEGORY CONTEXT (If available) ---
    if category:
        queries.append(f'"{product}" {category} {location}')
        queries.append(f'buy {category} "{product}"')

    # --- 6. URGENCY SIGNALS ---
    urgency_words = ["urgent", "asap", "emergency", "immediately", "cash ready"]
    for word in urgency_words:
        queries.append(f'"{product}" {location} {word}')

    # Deduplicate while preserving order
    unique_queries = list(dict.fromkeys(queries))
    
    # Limit to reasonable number if too many (but user asked for 15+)
    return unique_queries
