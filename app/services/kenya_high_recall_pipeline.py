# app/services/kenya_high_recall_pipeline.py
# ============================================================
# KENYA HIGH RECALL PIPELINE — Clean Implementation
# ============================================================
# 1. Deduplicate by URL
# 2. Score intent (0.25 threshold)
# 3. Sort descending
# 4. Return top 20
# ============================================================

import re
import os
from typing import List, Dict, Any
from datetime import datetime, timezone


# Buyer intent signals
BUYER_VERBS = [
    "looking", "need", "want", "wtb", "wanted",
    "natafuta", "nahitaji", "nataka", "iko", "available",
    "where can i get", "anyone selling", "who has"
]

# Hard seller signals (immediate reject)
SELLER_SIGNALS = [
    "for sale", "we sell", "call our agent", "call us",
    "visit our shop", "visit us", "in stock", "discount",
    "best price", "order now", "buy now", "shop now",
    "official dealer", "authorized dealer", "distributor",
    "wholesale", "retail", "clearance", "promo"
]

PRICE_PATTERN = re.compile(r"\b\d+(\.\d+)?\s?(k|m|million|ksh|kes|thousand)\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(\+?254|0)\d{9}")


def calculate_kenyan_intent_score(text: str) -> float:
    """
    Calculate buyer intent score (0.0 to 1.0).
    """
    if not text:
        return 0.0
        
    text_lower = text.lower()
    score = 0.0

    # Hard reject: obvious seller
    for seller_signal in SELLER_SIGNALS:
        if seller_signal in text_lower:
            return 0.0

    # Base: product mentioned
    score += 0.3

    # Buyer verb
    if any(verb in text_lower for verb in BUYER_VERBS):
        score += 0.3

    # Question pattern
    if "?" in text:
        score += 0.2

    # Price/budget mention
    if PRICE_PATTERN.search(text):
        score += 0.3

    # Phone number
    if PHONE_PATTERN.search(text):
        score += 0.2

    return min(score, 1.0)


def generate_high_recall_queries(product: str, location: str = "Kenya") -> List[str]:
    """
    Generate broad queries for high recall search.
    """
    base = f'"{product}" {location}'
    
    queries = [
        base,
        f'{base} price',
        f'{base} budget',
        f'{base} ?',
        f'{base} natafuta',
    ]
    
    platform_queries = []
    for q in queries:
        platform_queries.extend([
            f'site:t.me {q}',
            f'site:facebook.com/groups {q}',
            f'site:twitter.com {q}',
        ])
    
    seen = set()
    unique_queries = []
    for q in platform_queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)
    
    return unique_queries[:10]


def process_high_recall_results(raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process raw scraper results.
    
    Steps:
    1. Deduplicate by URL
    2. Score intent
    3. Sort descending
    4. Return top 20
    """
    if not raw_results:
        return []
    
    scored_leads = []
    seen_urls = set()
    
    for result in raw_results:
        url = result.get("url") or result.get("link") or result.get("href", "")
        
        # Deduplicate by URL
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        
        # Extract text
        title = result.get("title", "")
        snippet = result.get("snippet") or result.get("body") or result.get("text", "")
        full_text = f"{title} {snippet}".strip()
        
        if not full_text:
            continue
        
        # Score intent
        score = calculate_kenyan_intent_score(full_text)
        
        # Only include if score meets threshold
        if score >= 0.25:
            # Determine badge
            if score >= 0.7:
                badge = "HOT"
            elif score >= 0.5:
                badge = "WARM"
            else:
                badge = "COLD"
            
            # Extract phone
            phone_match = PHONE_PATTERN.search(full_text)
            phone = phone_match.group(0) if phone_match else ""
            
            scored_leads.append({
                "id": hash(url) % 100000000,
                "title": title[:200] if title else snippet[:200],
                "url": url,
                "source": result.get("source", "unknown"),
                "snippet": snippet[:300],
                "intent_score": round(score, 2),
                "badge": badge,
                "contact_phone": phone,
                "location": result.get("location", "Kenya"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "intent_type": "BUYER",
                "status": "NEW",
                "is_hot_lead": badge == "HOT"
            })
    
    # Sort descending
    scored_leads.sort(key=lambda x: x["intent_score"], reverse=True)
    
    # Return top 20
    return scored_leads[:20]
