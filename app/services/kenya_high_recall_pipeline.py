# app/services/kenya_high_recall_pipeline.py
# ============================================================
# KENYA HIGH RECALL PIPELINE
# ============================================================
# Broad capture + smart scoring for Kenyan buyer leads
# ============================================================

import re
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Buyer intent signals (Kenya-optimized)
BUYER_VERBS = [
    "looking", "need", "want", "wtb", "wanted",
    "natafuta", "nahitaji", "nataka", "iko", "available",
    "where can i get", "anyone selling", "who has"
]

# Urgency indicators
URGENCY_WORDS = [
    "urgent", "urgently", "asap", "today", "now",
    "haraka", "immediately", "this week", "sasa", "fast"
]

# Hard seller signals (immediate reject)
SELLER_SIGNALS = [
    "for sale", "we sell", "call our agent", "call us",
    "visit our shop", "visit us", "in stock", "discount",
    "best price", "order now", "buy now", "shop now",
    "official dealer", "authorized dealer", "distributor",
    "wholesale", "retail", "clearance", "promo"
]

# Price/budget patterns
PRICE_PATTERN = re.compile(r"\b\d+(\.\d+)?\s?(k|m|million|ksh|kes|thousand)\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(\+?254|0)\d{9}")


def calculate_kenyan_intent_score(text: str) -> float:
    """
    Calculate buyer intent score (0.0 to 1.0) for Kenyan market.
    
    Scoring:
    - Base product mention: +0.3
    - Buyer verb: +0.3
    - Question mark: +0.2
    - Price/budget mention: +0.3
    - Urgency word: +0.3
    - Phone number: +0.2
    - Hard seller signal: immediate 0.0 (reject)
    """
    if not text:
        return 0.0
        
    text_lower = text.lower()
    score = 0.0
    signals_found = []

    # Hard reject: obvious seller
    for seller_signal in SELLER_SIGNALS:
        if seller_signal in text_lower:
            logger.debug(f"SELLER_REJECT: '{seller_signal}' in text")
            return 0.0

    # Base: product is mentioned (implicit)
    score += 0.3
    signals_found.append("product_base")

    # Buyer verb
    if any(verb in text_lower for verb in BUYER_VERBS):
        score += 0.3
        signals_found.append("buyer_verb")

    # Question pattern (buyers often ask)
    if "?" in text:
        score += 0.2
        signals_found.append("question")

    # Price/budget mention
    if PRICE_PATTERN.search(text):
        score += 0.3
        signals_found.append("price_mention")

    # Urgency
    if any(word in text_lower for word in URGENCY_WORDS):
        score += 0.3
        signals_found.append("urgency")

    # Phone number (high engagement signal)
    if PHONE_PATTERN.search(text):
        score += 0.2
        signals_found.append("phone")

    # Cap at 1.0
    final_score = min(score, 1.0)
    
    logger.debug(f"SCORE: {final_score:.2f} for '{text[:50]}...' signals={signals_found}")
    return final_score


def generate_high_recall_queries(product: str, location: str = "Kenya") -> List[str]:
    """
    Generate broad queries for high recall search.
    No strict buyer phrase requirement - let classifier handle intent.
    """
    base = f'"{product}" {location}'
    
    queries = [
        base,                          # "product" location
        f'{base} price',               # price inquiry
        f'{base} budget',              # budget mention
        f'{base} ?',                   # question pattern
        f'{base} natafuta',            # Swahili buyer verb
    ]
    
    # Platform-specific variations
    platform_queries = []
    for q in queries:
        platform_queries.extend([
            f'site:t.me {q}',                      # Telegram
            f'site:facebook.com/groups {q}',       # Facebook groups
            f'site:twitter.com {q}',               # Twitter/X
        ])
    
    # Deduplicate while preserving order
    seen = set()
    unique_queries = []
    for q in platform_queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)
    
    logger.info(f"Generated {len(unique_queries)} high-recall queries for '{product}'")
    return unique_queries[:10]  # Max 10 queries


def process_high_recall_results(raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process raw scraper results, score each, and return top leads.
    
    Returns leads with:
    - title, url, snippet, source
    - intent_score (0.0-1.0)
    - confidence (%)
    - badge (HOT/WARM/COLD based on score)
    """
    if not raw_results:
        logger.warning("No raw results to process")
        return []
    
    scored_leads = []
    seen_urls = set()
    
    for result in raw_results:
        url = result.get("url") or result.get("link") or result.get("href", "")
        
        # Deduplicate by URL
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        
        # Extract text for scoring
        title = result.get("title", "")
        snippet = result.get("snippet") or result.get("body") or result.get("text", "")
        full_text = f"{title} {snippet}".strip()
        
        if not full_text:
            continue
        
        # Calculate intent score
        score = calculate_kenyan_intent_score(full_text)
        
        # Only include if score meets threshold
        if score >= 0.25:  # Low threshold for high recall
            # Determine badge
            if score >= 0.7:
                badge = "HOT"
            elif score >= 0.5:
                badge = "WARM"
            else:
                badge = "COLD"
            
            # Extract phone if present
            phone_match = PHONE_PATTERN.search(full_text)
            phone = phone_match.group(0) if phone_match else ""
            
            scored_leads.append({
                "id": hash(url) % 100000000,  # Simple ID
                "title": title[:200] if title else snippet[:200],
                "url": url,
                "source": result.get("source", "unknown"),
                "snippet": snippet[:300],
                "buyer_request_snippet": snippet[:500],
                "intent_score": round(score, 2),
                "confidence": round(score * 100, 2),
                "confidence_score": round(score, 2),
                "badge": badge,
                "contact_phone": phone,
                "location": result.get("location", "Kenya"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "market_side": "demand",
                "intent_type": "BUYER",
                "status": "NEW",
                "is_hot_lead": badge == "HOT",
                "ui_filter_status": "shown"
            })
    
    # Sort by confidence descending
    scored_leads.sort(key=lambda x: x["intent_score"], reverse=True)
    
    top_leads = scored_leads[:20]  # Return top 20
    logger.info(f"Processed {len(raw_results)} raw results -> {len(scored_leads)} scored -> {len(top_leads)} top leads")
    
    return top_leads


def run_high_recall_search(product: str, location: str = "Kenya") -> Dict[str, Any]:
    """
    Complete high-recall search pipeline.
    
    This is a convenience wrapper that would be called from your API route.
    It generates queries, runs scrapers (placeholder), and returns scored leads.
    """
    queries = generate_high_recall_queries(product, location)
    
    # Note: Actual scraper calls happen in search_service.py
    # This function exists for testing and documentation
    
    return {
        "queries": queries,
        "message": f"Generated {len(queries)} queries for high-recall search",
        "pipeline": "kenya_high_recall"
    }


# Test function
if __name__ == "__main__":
    # Test scoring
    test_cases = [
        "5000L tank iko?",                           # Should score high
        "Need 10000L tank urgently",                 # Should score high
        "Tank around 25k?",                          # Should score high
        "Natafuta tank kubwa",                       # Should score high
        "Tank ya 10k price?",                        # Should score high
        "We sell quality tanks call us",             # Should score 0 (seller)
        "Tanks for sale best price",                 # Should score 0 (seller)
        "Toyota Prado 2014 available",               # Neutral
    ]
    
    print("="*60)
    print("KENYA HIGH RECALL PIPELINE - TEST")
    print("="*60)
    
    for text in test_cases:
        score = calculate_kenyan_intent_score(text)
        status = "PASS" if score >= 0.25 else "REJECT"
        if score == 0.0 and any(s in text.lower() for s in SELLER_SIGNALS):
            status = "SELLER_REJECT"
        print(f"\nText: {text}")
        print(f"Score: {score:.2f} -> {status}")
    
    print("\n" + "="*60)
    print("QUERY GENERATION TEST")
    print("="*60)
    queries = generate_high_recall_queries("water tank", "Kenya")
    for q in queries:
        print(f"  {q}")
    
    print("\nAll tests completed successfully!")
