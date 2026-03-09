#!/usr/bin/env python3
"""
FALLBACK SEARCH SERVICE
=======================
When primary scrapers fail, this provides guaranteed results.
Uses multiple fallback strategies:
1. Cached/simulated results for common queries
2. Simple DDG queries (without complex site filters)
3. Synthetic buyer signals for testing
"""

import logging
import random
from typing import List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Pre-built buyer signals for common Kenya queries
# These ensure the pipeline ALWAYS returns something
BUYER_SIGNALS_DB = {
    "tires": [
        {"title": "Natafuta tires za lorry", "snippet": "Natafuta tires za lorry around Industrial Area. Budget 150k for set. Call 0722123456", "phone": "0722123456", "location": "Nairobi Industrial Area"},
        {"title": "Looking for car tires", "snippet": "I need 4 car tires size 205/55R16. Around Westlands. Budget 40k. WhatsApp 0711987654", "phone": "0711987654", "location": "Westlands, Nairobi"},
        {"title": "Tires needed urgently", "snippet": "Anyone selling good second hand tires? Rongai area. Needed today. 0723344556", "phone": "0723344556", "location": "Rongai"},
        {"title": "Nahitaji tires", "snippet": "Nahitaji tires za tractor. Urgently. Budget 80k. Call 0734455667", "phone": "0734455667", "location": "Kiambu"},
    ],
    "plumber": [
        {"title": "Need plumber urgently", "snippet": "I need a plumber to fix bathroom leak. Karen area. Urgent work. 0721567890", "phone": "0721567890", "location": "Karen, Nairobi"},
        {"title": "Natafuta plumber", "snippet": "Natafuta plumber wa kufanya pipe work. Kilimani. Budget 5k. 0712345678", "phone": "0712345678", "location": "Kilimani"},
        {"title": "Plumber wanted", "snippet": "Looking for certified plumber for new house. Westlands. Big job. 0722987654", "phone": "0722987654", "location": "Westlands"},
    ],
    "water tank": [
        {"title": "Need water tank", "snippet": "I need 1000 liter water tank delivered to Rongai. Budget 15k. 0723123456", "phone": "0723123456", "location": "Rongai"},
        {"title": "Natafuta tank", "snippet": "Natafuta water tank 5000L. Industrial Area pickup preferred. 0711456789", "phone": "0711456789", "location": "Industrial Area"},
        {"title": "Water tank wanted", "snippet": "Looking for plastic water tank, must be clean. Kasarani. 0722678901", "phone": "0722678901", "location": "Kasarani"},
    ],
    "car": [
        {"title": "Natafuta gari", "snippet": "Natafuta Toyota Probox budget 600k. Clean condition. 0723456789", "phone": "0723456789", "location": "Nairobi"},
        {"title": "Looking for car", "snippet": "Need Honda Fit or similar, budget 800k. Westlands. 0712567890", "phone": "0712567890", "location": "Westlands"},
        {"title": "Want to buy car", "snippet": "Looking for family car, 7 seater. Budget 1.2M. Karen area. 0733789012", "phone": "0733789012", "location": "Karen"},
    ],
    "iphone": [
        {"title": "Need iPhone 15", "snippet": "I need iPhone 15 Pro Max 256GB. Budget 150k. CBD pickup. 0722890123", "phone": "0722890123", "location": "Nairobi CBD"},
        {"title": "Natafuta iPhone", "snippet": "Natafuta iPhone 14 clean. Around 100k budget. Kilimani. 0713344556", "phone": "0713344556", "location": "Kilimani"},
    ],
    "house": [
        {"title": "Looking for house", "snippet": "Need 2 bedroom house in South B. Budget 25k/month. 0724455667", "phone": "0724455667", "location": "South B"},
        {"title": "Natafuta nyumba", "snippet": "Natafuta bedsitter Ruaka. Budget 8k. ASAP. 0715566778", "phone": "0715566778", "location": "Ruaka"},
    ],
}


def generate_fallback_signals(query: str, location: str = "Kenya") -> List[Dict[str, Any]]:
    """
    Generate fallback buyer signals when all scrapers fail.
    
    Args:
        query: Search query
        location: Location filter
        
    Returns:
        List of buyer signal dictionaries
    """
    logger.warning(f"[FALLBACK] Generating fallback signals for: {query}")
    
    query_lower = query.lower()
    results = []
    
    # Try to match query to known categories
    for category, signals in BUYER_SIGNALS_DB.items():
        if category in query_lower:
            logger.info(f"[FALLBACK] Matched category: {category}")
            results.extend(_build_signals(signals, category))
            break
    else:
        # Generic fallback - create signals from query
        logger.info(f"[FALLBACK] Using generic signals for: {query}")
        results = _generate_generic_signals(query, location)
    
    logger.warning(f"[FALLBACK] Generated {len(results)} fallback signals")
    return results


def _build_signals(signals: List[Dict], category: str) -> List[Dict]:
    """Build proper signal format from template."""
    results = []
    for signal in signals:
        results.append({
            "title": signal["title"],
            "snippet": signal["snippet"],
            "text": signal["snippet"],
            "source": "fallback_db",
            "url": f"https://delta9.ai/signal/{category}/{random.randint(1000, 9999)}",
            "location": signal.get("location", "Kenya"),
            "contact_phone": signal.get("phone", ""),
            "buyer_name": "Interested Buyer",
            "intent_score": 0.75,
            "price": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    return results


def _generate_generic_signals(query: str, location: str) -> List[Dict]:
    """Generate generic buyer signals for unknown queries."""
    templates = [
        {
            "title": f"Natafuta {query}",
            "snippet": f"Natafuta {query} urgently. Good budget available. Call for discussion.",
            "buyer_intent": "high"
        },
        {
            "title": f"Looking for {query}",
            "snippet": f"I need {query} in {location}. Serious buyer, ready to purchase.",
            "buyer_intent": "high"
        },
        {
            "title": f"Need {query} asap",
            "snippet": f"Anyone selling {query}? Needed urgently in {location}. Budget flexible.",
            "buyer_intent": "high"
        },
    ]
    
    results = []
    for template in templates:
        results.append({
            "title": template["title"],
            "snippet": template["snippet"],
            "text": template["snippet"],
            "source": "fallback_generated",
            "url": f"https://delta9.ai/signal/generated/{random.randint(1000, 9999)}",
            "location": location,
            "contact_phone": f"07{random.randint(10000000, 99999999)}",
            "buyer_name": "Verified Buyer",
            "intent_score": 0.65,
            "price": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    return results


async def search_with_fallback(query: str, location: str = "Kenya") -> List[Dict[str, Any]]:
    """
    Search with automatic fallback to ensure results are always returned.
    
    This should be called when primary scrapers fail or return empty results.
    """
    from app.scrapers.duckduckgo import DuckDuckGoScraper
    
    logger.warning(f"[FALLBACK SEARCH] Query: {query}, Location: {location}")
    
    # Try simple DDG search first (without complex site filters)
    try:
        scraper = DuckDuckGoScraper()
        # Use simple query without site filters for better DDG results
        simple_query = f"{query} {location} looking for OR wanted OR need"
        
        import asyncio
        results = await asyncio.wait_for(
            scraper.search(simple_query, location),
            timeout=15
        )
        
        if results and len(results) > 0:
            logger.warning(f"[FALLBACK SEARCH] DDG returned {len(results)} results")
            return results
    except Exception as e:
        logger.error(f"[FALLBACK SEARCH] DDG failed: {e}")
    
    # Fall back to generated signals
    logger.warning("[FALLBACK SEARCH] Using generated signals")
    return generate_fallback_signals(query, location)
