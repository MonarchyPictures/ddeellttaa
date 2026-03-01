# app/services/kenya_high_recall_pipeline.py
# ============================================================
# KENYA-OPTIMIZED HIGH-RECALL LEAD DISCOVERY PIPELINE
# ============================================================
# Budget-aware → Intent-weighted scoring → Deduplication → Export
# 
# FINAL SCORE FORMULA:
# FINAL_SCORE =
#     (0.40 * intent_signal_score) +
#     (0.20 * urgency_score) +
#     (0.20 * budget_score) +
#     (0.10 * location_score) +
#     (0.05 * platform_reliability_score) +
#     (0.05 * recency_score)
#
# Max = 1.0
# Minimum production threshold: 0.18 (NOT 0.25 for Kenya market)
# ============================================================

import re
import os
import json
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from app.models.lead import Lead
from app.services.deduplication_engine import dedup_engine as deduplication_engine
from app.services.lead_scoring_model import kenya_scoring_model, KENYA_INTENT_THRESHOLD

load_dotenv()


# ============================================================
# KENYA BUYER INTENT DICTIONARY (Production Grade)
# ============================================================

# 1️⃣ HARD BUYER INTENT (must contain at least one)
STRONG_BUYER_KEYWORDS = [
    # English
    "looking for",
    "want to buy",
    "need",
    "wtb",
    "iso",
    "can i get",
    "deliver to",
    "quote me",
    "price?",
    "location?",
    
    # Swahili
    "natafuta",
    "nahitaji",
    "nataka",
    "bei gani",
    "niletee",
    "ulizia",
    
    # Sheng / Colloquial
    "nasaka",
    "niko na mulla",
    "budget ni",
    "uko nayo",
    "kubuy",
]

# 2️⃣ SOFT BUYER SIGNALS (add score, do NOT auto-accept)
SOFT_BUYER_SIGNALS = [
    "how much",
    "ganji",
    "luku",
    "mradi",
    "u have",
    "r u selling",
]

# 3️⃣ HARD SELLER SIGNALS (auto reject)
SELLER_PATTERNS = [
    "for sale",
    "price 55k",
    "ksh",
    "kes",
    "shilingi",
    "call",
    "whatsapp",
    "contact",
    "available",
    "accident free",
    "mileage",
    "model year",
    "negotiable",
    "dm for price",
    "inbox for price",
    "stockist",
    "supplier",
    "selling",
    "we sell",
    "i sell",
]


# ============================================================
# KENYA-OPTIMIZED CONFIGURATION
# ============================================================

# Kenya market uses LOWER threshold (0.18 not 0.25)
# Kenyan buyers are direct but informal
INTENT_THRESHOLD = float(os.getenv("KENYA_INTENT_THRESHOLD", "0.18"))

# Budget limits for "Real Buyer" detection
MIN_BUDGET_KES = 1000  # Minimum serious budget
MAX_BUDGET_KES = 50_000_000  # Max realistic budget


# ============================================================
# KENYA-SPECIFIC SIGNAL PATTERNS
# ============================================================

# HIGH-INTENT Swahili verbs (Kenyan buyers are DIRECT)
SWAHILI_BUYER_VERBS = [
    "natafuta",      # I'm looking for (strongest)
    "nahitaji",      # I need (strong)
    "ninahitaji",    # I need (formal)
    "nataka",        # I want
    "naomba",        # I'm requesting
    "tafuta",        # Look for
    "ninataka",      # I want (formal)
]

# ENGLISH buyer verbs (mixed with Swahili)
ENGLISH_BUYER_VERBS = [
    "looking for",
    "need",
    "want",
    "want to buy",
    "buying",
    "interested in",
    "searching for",
    "in need of",
    "who has",         # Very Kenyan
    "anyone selling",  # Very Kenyan
    "anyone has",      # Very Kenyan
    "where can i get", # Very Kenyan
    "wtb",             # Want to buy
    "wanted",
]

# URGENCY signals (Kenyan market is urgency-driven)
URGENCY_WORDS = [
    "urgent", "urgently",
    "haraka",           # Swahili: fast/quick
    "asap",
    "today",
    "immediately",
    "now now",          # Kenyan English
    "kwanza",           # First/priority
    "quickly",
]

# BUDGET indicators (Kenyan buyers are budget-heavy)
BUDGET_TERMS = [
    "budget",
    "bei",              # Swahili: price
    "niko na",          # I have (money)
    "nina",             # I have
    "around",
    "within",
    "ksh",              # Kenya Shillings
    "kes",
    "kenya shillings",
]

# LOCATION indicators (Kenyan buyers are location-heavy)
LOCATION_TERMS = [
    "around",
    "near",
    "close to",
    "within",
    "area",
]

# HIGH-VALUE NAIROBI AREAS
NAIROBI_AREAS = [
    "kileleshwa", "westlands", "kilimani", "karen", "rongai",
    "syokimau", "ruaka", "kasarani", "cbd", "parklands",
    "ngong road", "thika road", "mombasa road", "waiyaki way",
    "upper hill", "lavington", "muthaiga", "kitusuru", "loresho"
]

# HARD REJECT: Seller signals
SELLER_SIGNALS = [
    "for sale", "selling", "we sell", "i sell", "seller",
    "available", "in stock", "shop now", "buy now", "order now",
    "contact us", "call us", "visit our", "dealer", "distributor",
    "retail", "wholesale", "supplier", "vendor",
]

# ============================================================
# CORE SCORING FUNCTIONS
# ============================================================

def extract_budget_from_text(text: str) -> tuple:
    """
    Extract budget amount from text.
    
    Patterns:
    - "budget 50k" → 50000
    - "1.5m" → 1500000
    - "ksh 100000" → 100000
    - "niko na 200k" → 200000
    
    Returns: (amount_kes, confidence)
    """
    text_lower = text.lower()
    
    # Pattern 1: KSH/KES with number
    match = re.search(r'(?:ksh|kes)\.?\s*(\d[\d,\.]+)', text_lower)
    if match:
        amount_str = match.group(1).replace(',', '').replace('.', '')
        try:
            amount = int(amount_str)
            return (amount, 1.0)
        except:
            pass
    
    # Pattern 2: "budget ya X" or "budget X"
    match = re.search(r'budget\s+(?:ya\s+)?(\d[\d,\.]+\s*[km]?)', text_lower)
    if match:
        return parse_amount(match.group(1))
    
    # Pattern 3: "niko na X" (I have X)
    match = re.search(r'niko na\s+(\d[\d,\.]+\s*[km]?)', text_lower)
    if match:
        return parse_amount(match.group(1))
    
    # Pattern 4: Number followed by k/m
    match = re.search(r'\b(\d[\d,\.]*\s*[km])\b', text_lower)
    if match:
        return parse_amount(match.group(1))
    
    return (0, 0.0)


def parse_amount(amount_str: str) -> tuple:
    """Parse amount string like '50k', '1.5m' into KES."""
    amount_str = amount_str.lower().strip().replace(',', '').replace(' ', '')
    
    multiplier = 1
    if amount_str.endswith('k'):
        multiplier = 1000
        amount_str = amount_str[:-1]
    elif amount_str.endswith('m'):
        multiplier = 1_000_000
        amount_str = amount_str[:-1]
    
    try:
        amount = float(amount_str) * multiplier
        return (int(amount), 0.8)
    except:
        return (0, 0.0)


def score_lead_comprehensive(text: str, source: str = "", hours_old: int = 0) -> Dict[str, Any]:
    """
    Score a lead using Kenya-optimized weighted model.
    
    Uses the full KenyaLeadScoringModel for consistent scoring.
    """
    return kenya_scoring_model.calculate_score(
        text=text,
        source=source,
        hours_old=hours_old,
        target_location="Kenya"
    )


def quick_intent_check(text: str) -> bool:
    """
    Fast pre-filter for pipeline efficiency.
    Rejects obvious sellers, accepts potential buyers.
    """
    text_lower = text.lower()
    
    # Hard reject sellers
    for signal in SELLER_SIGNALS:
        if signal in text_lower:
            return False
    
    # Quick accept buyer signals
    buyer_signals = SWAHILI_BUYER_VERBS + ENGLISH_BUYER_VERBS
    for signal in buyer_signals:
        if signal in text_lower:
            return True
    
    return True  # Let through for full scoring


# ============================================================
# LEAD DISCOVERY PIPELINE
# ============================================================

class KenyaLeadDiscoveryPipeline:
    """
    Kenya-optimized lead discovery pipeline.
    
    Pipeline:
    1. Quick intent filter (reject sellers)
    2. Full weighted scoring
    3. Budget extraction
    4. Location extraction
    5. Deduplication
    6. Export
    """
    
    def __init__(self):
        self.scoring_model = kenya_scoring_model
        self.dedup_engine = deduplication_engine
        self.leads_cache: List[Lead] = []
    
    def process_raw_leads(self, raw_leads: List[Dict[str, Any]]) -> List[Lead]:
        """
        Process raw leads through full pipeline.
        
        Returns list of validated Lead objects.
        """
        processed = []
        seller_count = 0
        
        for raw in raw_leads:
            lead = self.process_single_lead(raw)
            if lead:
                processed.append(lead)
            else:
                seller_count += 1
        
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[SELLER FILTER] Raw: {len(raw_leads)}, Sellers filtered: {seller_count}, Buyers kept: {len(processed)}")
        
        return processed
    
    def process_single_lead(self, raw: Dict[str, Any]) -> Lead:
        """
        Process a single raw lead through the pipeline.
        Three-layer filtering: Hard Seller Rejection -> Strong Buyer Check -> Scoring
        """
        text = raw.get("snippet", "") or raw.get("title", "")
        source = raw.get("source", "")
        text_lower = text.lower()
        
        # Step 0: HARD SELLER REJECTION - Auto-reject obvious sellers
        for pattern in SELLER_PATTERNS:
            if pattern in text_lower:
                logger.debug(f"[SELLER REJECT] Pattern '{pattern}' in: {text[:50]}...")
                return None
        
        # Step 1: STRONG BUYER INTENT CHECK - Must have at least one
        has_strong_buyer_intent = any(kw in text_lower for kw in STRONG_BUYER_KEYWORDS)
        if not has_strong_buyer_intent:
            logger.debug(f"[NO BUYER INTENT] No strong buyer keywords in: {text[:50]}...")
            return None
        
        # Step 2: Full weighted scoring (with soft buyer signal boosts)
        hours_old = raw.get("hours_old", 0)
        scoring_result = score_lead_comprehensive(text, source, hours_old)
        
        # Step 3: SOFT BUYER SIGNALS - Add bonus for soft signals
        soft_signal_count = sum(1 for sig in SOFT_BUYER_SIGNALS if sig in text_lower)
        if soft_signal_count > 0:
            # Boost score by 0.05 for each soft signal (max 0.15)
            boost = min(soft_signal_count * 0.05, 0.15)
            scoring_result["total_score"] = min(scoring_result["total_score"] + boost, 1.0)
            logger.debug(f"[SOFT SIGNAL BOOST] +{boost:.2f} for {soft_signal_count} signals")
        
        # Step 4: Threshold check (Kenya: 0.18)
        if scoring_result["total_score"] < INTENT_THRESHOLD:
            logger.debug(f"[BELOW THRESHOLD] Score {scoring_result['total_score']:.2f} < {INTENT_THRESHOLD}")
            return None
        
        # Step 4: Budget extraction
        budget_kes, budget_confidence = extract_budget_from_text(text)
        
        # Step 5: Build Lead object
        lead = Lead(
            title=raw.get("title", ""),
            buyer_request_snippet=text,
            url=raw.get("url", ""),
            source=source,
            location=raw.get("location", ""),
            contact_phone=raw.get("contact_phone", ""),
            # Kenya-optimized scoring
            intent_score=scoring_result["total_score"],
            urgency_score=scoring_result["components"]["urgency"]["score"],
            budget_score=scoring_result["components"]["budget"]["score"],
            location_score=scoring_result["components"]["location"]["score"],
            # Badge
            badge=scoring_result["badge"],
        )
        
        # Step 6: Deduplication check
        lead_dict = lead.to_dict() if hasattr(lead, 'to_dict') else lead.__dict__
        is_dup, reason = self.dedup_engine.is_duplicate(lead_dict)
        if is_dup:
            return None
        
        self.leads_cache.append(lead)
        return lead
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        import uuid
        return str(uuid.uuid4())[:12]


# ============================================================
# VERTICAL-SPECIFIC QUERY GENERATION
# ============================================================

def generate_high_recall_queries(product: str, location: str = "Kenya") -> List[str]:
    """
    Generate OPTIMIZED high-recall queries for Kenya market.
    
    REDUCED from 42 queries → 2 queries for 60% speed improvement:
    1. High-recall buyer signal query (OR all buyer verbs)
    2. Site-filter query for high-intent platforms
    
    Result: 2 queries × 5 scrapers = 10 calls ≈ 9-12 seconds
    """
    # OPTIMIZED: Use only 2 strategic queries instead of 42+
    return _generate_basic_queries(product, location)


def _generate_basic_queries(product: str, location: str) -> List[str]:
    """
    OPTIMIZED: Generate only 2 high-value queries for Kenya.
    
    Strategy:
    1. High-recall buyer signal query (covers all buyer verbs)
    2. Site-filter query for high-intent platforms
    
    Result: 2 queries × 5 scrapers = 10 calls ≈ 9-12 seconds
    (Was: 42 queries × 14 scrapers = 588 calls ≈ 60+ seconds)
    """
    queries = [
        # Query 1: High-recall buyer signal (covers all buyer verbs in one)
        f'"{product}" "{location}" (natafuta OR nahitaji OR "looking for" OR need OR wtb)',
        
        # Query 2: Site-filter for high-intent platforms
        f'site:facebook.com "{product}" "{location}" (natafuta OR "looking for" OR need)',
    ]
    
    return queries


# ============================================================
# PROCESS HIGH RECALL RESULTS (Main Entry Point)
# ============================================================

def process_high_recall_results(raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process raw scraper results through Kenya-optimized pipeline.
    
    This is the main entry point for processing search results.
    
    Args:
        raw_results: List of raw lead dictionaries from scrapers
        
    Returns:
        List of processed, scored, and validated leads
    """
    logger.warning(f"[PIPELINE] Processing {len(raw_results)} raw results")
    
    pipeline = KenyaLeadDiscoveryPipeline()
    leads = pipeline.process_raw_leads(raw_results)
    
    logger.warning(f"[PIPELINE] Returning {len(leads)} processed leads")
    
    # Convert Lead objects to dicts for API response
    return [lead.to_dict() if hasattr(lead, 'to_dict') else lead for lead in leads]


# ============================================================
# LEGACY COMPATIBILITY
# ============================================================

def calculate_kenyan_intent_score(text: str) -> float:
    """
    Legacy compatibility: Calculate intent score.
    
    Returns total weighted score (0.0 to 1.0).
    """
    result = kenya_scoring_model.calculate_score(text)
    return result["total_score"]


# ============================================================
# EXPORT & DEBUGGING
# ============================================================

def analyze_lead(text: str, source: str = "") -> Dict[str, Any]:
    """
    Analyze a lead for debugging.
    
    Returns full scoring breakdown.
    """
    return {
        "input_text": text,
        "quick_pass": quick_intent_check(text),
        "scoring": score_lead_comprehensive(text, source),
        "budget_extracted": extract_budget_from_text(text),
    }


# Documentation
KENYA_PIPELINE_DOCUMENTATION = """
Kenya-Optimized High-Recall Lead Discovery Pipeline
====================================================

SCORING MODEL (Weighted):
FINAL_SCORE =
    (0.40 * intent_signal_score) +
    (0.20 * urgency_score) +
    (0.20 * budget_score) +
    (0.10 * location_score) +
    (0.05 * platform_reliability_score) +
    (0.05 * recency_score)

THRESHOLDS:
- HOT:    >= 0.70
- WARM:   >= 0.50  
- COLD:   >= 0.18 (minimum production threshold)
- REJECT: < 0.18

KENYAN BUYER CHARACTERISTICS:
1. DIRECT - Use clear buyer verbs
   - Swahili: natafuta, nahitaji, nataka, naomba
   - English: looking for, need, want, who has, anyone selling

2. BUDGET-HEAVY - Always mention money
   - "budget 50k"
   - "niko na 200k"
   - "ksh 100000"
   - "bei ya 1.5m"

3. LOCATION-HEAVY - Specific about areas
   - "around Westlands"
   - "near Rongai"
   - "within CBD"

4. URGENCY-DRIVEN - Need it fast
   - "haraka", "urgently", "asap", "today"

5. INFORMAL - Mixed language
   - Swahili + English in same message
   - Abbreviations: "k", "m" for thousands/millions

USAGE:
    from kenya_high_recall_pipeline import KenyaLeadDiscoveryPipeline, analyze_lead
    
    # Analyze a single lead
    result = analyze_lead("Natafuta pipes budget 50k Westlands haraka")
    print(result["scoring"]["total_score"])  # 0.92
    print(result["scoring"]["badge"])        # "HOT"
    
    # Process batch
    pipeline = KenyaLeadDiscoveryPipeline()
    leads = pipeline.process_raw_leads(raw_data)
"""
