# app/engine/buyer_classifier.py
# ============================================================
# AI BUYER CLASSIFIER
# ============================================================
# Determines if a search result represents a BUYER or SELLER.
# Extracts structured data: name, phone, budget, location.
# Works for ANY product category.
# ============================================================

import re
import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


from app.config.runtime import CONFIDENCE_FLOOR

@dataclass
class BuyerSignal:
    """Structured buyer data extracted from raw text."""
    is_buyer: bool = False
    confidence: float = 0.0
    intent_score: float = 0.0
    urgency_score: float = 0.0

    # Extracted fields
    buyer_name: str = "Unknown"
    phone: str = ""
    email: str = ""
    whatsapp: str = ""
    budget: str = ""
    location: str = ""
    specific_need: str = ""
    timeline: str = ""

    # Classification
    category: str = "general"
    badge: str = "COLD"  # HOT, WARM, COLD
    persona: str = "End User"  # End User, Reseller, Business

    # Scoring breakdown
    score_details: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class BuyerClassifier:
    """
    Universal buyer detection that works for ANY product/service.
    Uses keyword matching + pattern analysis (no LLM required).
    """

    # ── BUYER SIGNALS (Things buyers say) ──────────────────
    BUYER_KEYWORDS_STRONG = [
        # English
        "looking for", "looking to buy", "want to buy", "need to buy",
        "searching for", "in search of", "trying to find",
        "anyone selling", "who is selling", "who sells", "who has",
        "where can i buy", "where can i find", "where can i get",
        "ready to buy", "cash buyer", "serious buyer", "cash ready",
        "wtb", "wanted", "urgently need", "desperately need",
        "in need of", "require", "seeking",

        # Swahili
        "natafuta", "nahitaji", "nataka kununua", "nataka",
        "nani anauza", "kuna mtu anauza", "naomba msaada",
        "niko tayari kununua", "niko na pesa", "niko na budget",
        "niko serious", "niko ready", "ninatafuta",

        # Sheng
        "niko na doh", "niko na kakitu", "niko ready manze",
        "nataka deal safi", "nani ako na", "kuna deal"
    ]

    BUYER_KEYWORDS_MEDIUM = [
        "interested in", "considering", "thinking about",
        "recommend", "recommendations", "suggestion",
        "options for", "alternatives to", "compare",
        "how much", "what price", "price range",
        "budget", "affordable", "cheap", "reasonable",
        "second hand", "used", "pre-owned",
        "anyone know", "help me find", "advise"
    ]

    BUYER_KEYWORDS_QUESTION = [
        "?",  # Questions are often buyer behavior
        "does anyone", "is there", "are there",
        "can someone", "could anyone", "would anyone",
        "any leads", "any recommendations", "any suggestions"
    ]

    # ── SELLER SIGNALS (Things sellers say) ────────────────
    SELLER_KEYWORDS_HARD = [
        # These ALWAYS mean seller
        "for sale", "selling", "we sell", "we offer",
        "buy from us", "order now", "order today",
        "visit our shop", "visit our store",
        "call to order", "add to cart", "checkout",
        "official dealer", "official distributor",
        "wholesale available", "stock available",
        "payment on delivery", "free delivery",
        "lipa mdogo mdogo", "installment plan"
    ]

    SELLER_KEYWORDS_SOFT = [
        # These SUGGEST seller but aren't definitive
        "available", "in stock", "brand new",
        "price", "ksh", "kes",  # Price listing
        "contact us", "call us", "dm for price",
        "negotiable", "slightly negotiable"
    ]

    # Marketplace/listing noise terms that are usually not active buyer requests
    LISTING_NOISE_TERMS = [
        "for sale", "for rent", "classifieds", "marketplace", "shop now",
        "order now", "add to cart", "checkout", "seller", "dealer"
    ]

    # ── URGENCY SIGNALS ────────────────────────────────────
    URGENCY_HIGH = [
        "urgent", "urgently", "asap", "immediately", "today",
        "now", "right now", "this week", "haraka", "sasa hivi",
        "emergency", "desperate", "deadline"
    ]

    URGENCY_MEDIUM = [
        "soon", "this month", "next week", "planning",
        "before", "by end of"
    ]

    # ── PERSONA SIGNALS ────────────────────────────────────
    BUSINESS_SIGNALS = [
        "company", "enterprise", "organization", "procurement",
        "tender", "office", "corporate", "bulk order", "institutional"
    ]

    RESELLER_SIGNALS = [
        "bulk", "wholesale", "resell", "stock up",
        "supplier", "distributor", "quantities"
    ]

    # ── CONTACT EXTRACTION PATTERNS ────────────────────────
    PHONE_PATTERNS = [
        r'(\+254\s?\d{9})',           # +254712345678
        r'(\+254\s?\d{3}\s?\d{3}\s?\d{3})',  # +254 712 345 678
        r'(0[17]\d{8})',               # 0712345678
        r'(0[17]\d{2}\s?\d{3}\s?\d{3})',  # 0712 345 678
        r'(\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{3,4})'  # International
    ]

    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    BUDGET_PATTERNS = [
        r'(?:budget|ksh|kes|sh)\s*[\.:=]?\s*([\d,]+(?:\s*[-–to]\s*[\d,]+)?(?:\s*[km])?)',
        r'([\d,]+\s*(?:k|m|K|M))\s*(?:budget|max|monthly|per\s*month)',
        r'(?:around|about|approximately|roughly)\s*([\d,]+(?:\s*[km])?)',
        r'(\d{1,3}(?:,\d{3})+)\s*(?:per|/)\s*(?:month|mo)',
        r'(?:budget\s*(?:is|around|of)?\s*)([\d,]+(?:\s*[-–]\s*[\d,]+)?)',
    ]

    def classify(self, text: str, source: str = "Unknown") -> BuyerSignal:
        """
        Core classification logic.
        Returns a BuyerSignal object with detailed scoring.
        """
        signal = BuyerSignal()
        score = 0
        urgency = 0
        details = []
        buyer_cue_count = 0
        listing_noise_count = 0

        # Normalization
        text_clean = text.lower()

        # ── STEP 1: EXCLUDE SELLERS ────────────────────────
        for kw in self.SELLER_KEYWORDS_HARD:
            if kw in text_clean:
                signal.is_buyer = False
                signal.confidence = 0.1
                signal.badge = "SELLER"
                details.append(f"Seller signal: {kw} (-100)")
                signal.score_details = details
                return signal

        # ── STEP 2: BUYER KEYWORDS ─────────────────────────
        for kw in self.BUYER_KEYWORDS_STRONG:
            if kw in text_clean:
                score += 50
                urgency += 0.4
                details.append(f"Strong intent: {kw} (+50)")
                buyer_cue_count += 2
                break  # Count once

        for kw in self.BUYER_KEYWORDS_MEDIUM:
            if kw in text_clean:
                score += 25
                urgency += 0.2
                details.append(f"Medium intent: {kw} (+25)")
                buyer_cue_count += 1
                break

        for kw in self.BUYER_KEYWORDS_QUESTION:
            if kw in text_clean:
                score += 15
                details.append(f"Question format: {kw} (+15)")
                buyer_cue_count += 1
                break

        # First-person cue is a strong indicator of real buyer demand
        if re.search(r"\b(i|im|i'm|my|me|we|our|natafuta|nahitaji|nataka)\b", text_clean):
            score += 10
            buyer_cue_count += 1
            details.append("First-person cue (+10)")

        # ── STEP 3: URGENCY SIGNALS ────────────────────────
        urgency_terms = ["asap", "urgent", "now", "immediately", "leo", "sasa"]
        for term in urgency_terms:
            if term in text_clean:
                score += 10
                urgency += 0.3
                details.append(f"Urgency: {term} (+10)")
                buyer_cue_count += 1

        # ── STEP 4: CONTACT INFO (High Intent) ─────────────
        # Phone
        phone_match = re.search(r'(\+254|07|01)\d{8}', text)
        if phone_match:
            phone = phone_match.group(0)
            signal.phone = phone
            score += 20
            details.append(f"Phone found: {phone} (+20)")
            
            # WhatsApp Link Gen
            clean = phone.replace("+", "").replace(" ", "")
            if clean.startswith("0"):
                clean = "254" + clean[1:]
            signal.whatsapp = f"https://wa.me/{clean}"

        # Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            signal.email = email_match.group(0)
            score += 10
            details.append(f"Email found (+10)")

        # ── STEP 5: BUDGET EXTRACTION ──────────────────────
        budget_patterns = [
            r'budget\s*(?:is)?\s*([\d,]+)',
            r'(\d+)\s*(?:ksh|kes|shilling)',
            r'(?:ksh|kes)\.?\s*([\d,]+)'
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, text_clean)
            if match:
                budget_str = match.group(1).strip()
                signal.budget = budget_str
                score += 15
                details.append(f"Budget found: {budget_str} (+15)")
                buyer_cue_count += 1
                break

        # ── STEP 6: LOCATION EXTRACTION ────────────────────
        kenyan_locations = [
            "nairobi", "mombasa", "kisumu", "nakuru", "eldoret",
            "thika", "kiambu", "westlands", "kilimani", "kileleshwa",
            "lavington", "karen", "ruaka", "syokimau", "kitengela",
            "juja", "rongai", "south b", "south c", "langata",
            "cbd", "upperhill", "parklands", "eastleigh", "ngong",
            "athi river", "machakos", "nyeri", "nanyuki", "malindi"
        ]
        for loc in kenyan_locations:
            if loc in text_clean:
                signal.location = loc.title()
                score += 10
                details.append(f"Location: {loc.title()} (+10)")
                break

        if not signal.location and "kenya" in text_clean:
            signal.location = "Kenya"
            score += 5
            details.append("Location: Kenya (+5)")

        # Listing noise penalty keeps high-recall while reducing marketplace junk
        for term in self.LISTING_NOISE_TERMS:
            if term in text_clean:
                listing_noise_count += 1
        if listing_noise_count > 0:
            penalty = min(20, listing_noise_count * 6)
            score -= penalty
            details.append(f"Listing noise penalty (-{penalty})")

        # ── STEP 7: SOURCE BONUS ───────────────────────────
        high_value_sources = ["telegram", "facebook_groups", "kenyatalk", "wazua"]
        if any(s in source.lower() for s in high_value_sources):
            score += 10
            details.append(f"High-value source: {source} (+10)")

        # ── STEP 8: FINAL CLASSIFICATION (RELAXED) ───────
        # Normalize score to 0-1 range
        max_possible = 150
        intent_score = min(max(score / max_possible, 0.0), 1.0)

        # RELAXED thresholds — classify as buyer more easily
        signal.intent_score = round(intent_score, 2)
        # Precision-focused but still high-recall: require either stronger score or explicit buyer cues.
        signal.is_buyer = (score >= 25) or (score >= 15 and buyer_cue_count >= 2)
        
        # Correctly using CONFIDENCE_FLOOR from import
        if signal.is_buyer:
            signal.confidence = min(0.99, max(intent_score + 0.1, CONFIDENCE_FLOOR))
        else:
            signal.confidence = max(0.1, intent_score)

        # Badge assignment (also relaxed)
        if intent_score >= 0.6 and urgency >= 0.5:
            signal.badge = "HOT"
        elif intent_score >= 0.3:
            signal.badge = "WARM"
        else:
            signal.badge = "COLD"

        # Extract specific need from text
        signal.specific_need = text[:200].strip()
        signal.score_details = details
        signal.urgency_score = urgency

        logger.debug(
            f"Classified: buyer={signal.is_buyer}, "
            f"score={signal.intent_score}, badge={signal.badge}, "
            f"details={details}"
        )

        return signal


# Singleton
BUYER_CLASSIFIER = BuyerClassifier()
