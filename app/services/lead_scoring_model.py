# app/services/lead_scoring_model.py
# ============================================================
# KENYA-OPTIMIZED LEAD SCORING MODEL — Weighted & Tunable
# ============================================================
# Kenyan buyer language characteristics:
# - Direct
# - Budget-heavy
# - Location-heavy
# - Urgency-driven
# - Often informal
# - Mixed Swahili + English
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
# Minimum production threshold: 0.18 (NOT 0.25 for Kenya)
# ============================================================

import re
import os
from typing import Dict, Any, List
from dataclasses import dataclass


# Kenya-optimized threshold (lower than Western markets)
KENYA_INTENT_THRESHOLD = 0.18


@dataclass
class KenyaScoringWeights:
    """
    Kenya-optimized scoring weights.
    
    Kenyan buyers are:
    - Direct (high intent weight)
    - Budget-heavy (significant budget weight)
    - Location-heavy (location matters)
    - Urgency-driven (urgency is key)
    """
    intent_signal: float = 0.40      # Highest: Kenyan buyers are direct
    urgency: float = 0.20            # High: Urgency-driven market
    budget: float = 0.20             # High: Budget-heavy decisions
    location: float = 0.10           # Medium: Location matters
    platform_reliability: float = 0.05  # Low: Platform signal
    recency: float = 0.05            # Low: Recency bonus
    
    @classmethod
    def from_env(cls) -> "KenyaScoringWeights":
        """Load weights from environment variables."""
        return cls(
            intent_signal=float(os.getenv("SCORE_WEIGHT_INTENT", "0.40")),
            urgency=float(os.getenv("SCORE_WEIGHT_URGENCY", "0.20")),
            budget=float(os.getenv("SCORE_WEIGHT_BUDGET", "0.20")),
            location=float(os.getenv("SCORE_WEIGHT_LOCATION", "0.10")),
            platform_reliability=float(os.getenv("SCORE_WEIGHT_PLATFORM", "0.05")),
            recency=float(os.getenv("SCORE_WEIGHT_RECENCY", "0.05")),
        )


class KenyaLeadScoringModel:
    """
    Kenya-optimized lead scoring model.
    
    Accounts for Kenyan buyer behavior:
    - Direct language (natafuta, nahitaji)
    - Budget mentions (50k, 100k, 1.5m)
    - Location specificity (Westlands, Rongai)
    - Urgency signals (haraka, urgently)
    - Mixed Swahili/English
    """
    
    def __init__(self, weights: KenyaScoringWeights = None):
        self.weights = weights or KenyaScoringWeights.from_env()
    
    # ============================================================
    # INTENT SIGNAL SCORE (Weight: 40%)
    # Strongest signal in Kenya
    # ============================================================
    
    def score_intent_signal(self, text: str) -> float:
        """
        Score buyer intent signals (0.0 to 1.0).
        
        Kenya-specific tiers:
        - STRONG (+1.0 raw): natafuta, nahitaji, looking for, wtb, cash ready, need urgently
        - MEDIUM (+0.7 raw): any leads, who knows, inbox me, dm me, recommend
        - WEAK (+0.4 raw): price, available, how much
        
        Hard reject sellers: "for sale", "selling", "we sell", etc.
        """
        if not text:
            return 0.0
            
        text_lower = text.lower()
        
        # HARD REJECT: Seller signals (check first)
        seller_signals = [
            "for sale", "we sell", "i sell", "in stock", "selling",
            "shop now", "buy now", "order now", "on sale",
            "contact us", "call us", "visit our", "call me", "whatsapp me",
            "dealer", "distributor", "retail", "wholesale", 
            "supplier", "vendor", "price drop", "clearance",
            # Car/vehicle seller patterns
            "papers available", "accident free", "new tyres", "new tires",
            "mileage", "km", "kilometers", "model year", "year model",
            "negotiable", "price negotiable", "asking price", "fixed price",
            "slightly used", "good condition", "excellent condition",
            "urgent sale", "quick sale", "must sell"
        ]
        
        for signal in seller_signals:
            if signal in text_lower:
                return 0.0  # Hard reject
        
        # Check for "selling" as a word boundary
        if re.search(r'\bselling\b', text_lower):
            return 0.0
        
        # STRONG signals (+1.0 raw) - Direct buyer intent
        strong_signals = [
            "natafuta",      # I'm looking for (Swahili - strongest)
            "nahitaji",      # I need (Swahili - strongest)
            "looking for",   # Direct English
            "want to buy",   # Direct English
            "wtb",           # Want to buy (shorthand)
            "need urgently", # Urgent need
            "cash ready",    # Ready to buy
        ]
        
        for signal in strong_signals:
            if signal in text_lower:
                return 1.0
        
        # MEDIUM signals (+0.7 raw) - Implied buyer intent
        medium_signals = [
            "any leads",     # Looking for recommendations
            "who knows",     # Seeking info
            "inbox me",      # Kenyan style
            "dm me",         # Want details
            "recommend",     # Seeking suggestions
        ]
        
        for signal in medium_signals:
            if signal in text_lower:
                return 0.7
        
        # WEAK signals (+0.4 raw) - Possible interest
        weak_signals = [
            "price",         # Asking about price
            "available",     # Checking availability
            "how much",      # Budget inquiry
        ]
        
        for signal in weak_signals:
            if signal in text_lower:
                return 0.4
        
        return 0.0  # No buyer intent detected
    
    # ============================================================
    # URGENCY SCORE (Weight: 20%)
    # Kenyan buyers often express urgency
    # ============================================================
    
    def score_urgency(self, text: str) -> float:
        """
        Score urgency (0.0 to 1.0).
        
        Kenyan urgency terms:
        - "urgently", "asap", "today", "immediately", "haraka"
        """
        if not text:
            return 0.0
            
        text_lower = text.lower()
        
        urgent_terms = [
            "urgent", "urgently", "asap",
            "today", "immediately", "haraka"
        ]
        
        for u in urgent_terms:
            if u in text_lower:
                return 1.0
        
        return 0.0
    
    # ============================================================
    # BUDGET SCORE (Weight: 20%)
    # Kenyan buyers frequently mention money
    # ============================================================
    
    def score_budget(self, text: str) -> float:
        """
        Score budget clarity (0.0 to 1.0).
        
        Kenyan budget patterns:
        - "budget" = serious buyer (1.0)
        - "ksh" or "kes" = currency mention (1.0)
        - "50k", "1.5m" = price shorthand (0.8)
        
        Budget mention = serious buyer.
        """
        if not text:
            return 0.0
            
        text_lower = text.lower()
        
        # EXPLICIT budget mention = serious buyer
        if "budget" in text_lower:
            return 1.0
        
        # Currency mention (KSH/KES)
        if re.search(r"\b(ksh|kes)\b", text_lower):
            return 1.0
        
        # Price shorthand (50k, 100k, 1m, 1.5m)
        if re.search(r"\b\d+\s?k\b", text_lower):
            return 0.8
        
        if re.search(r"\b\d+\s?m\b", text_lower):
            return 0.8
        
        return 0.0
    
    # ============================================================
    # LOCATION SCORE (Weight: 10%)
    # Kenyan buyers often mention specific estates/counties
    # ============================================================
    
    def score_location(self, text: str, target_location: str = "Kenya") -> float:
        """
        Score location specificity (0.0 to 1.0).
        
        If specific estate/county mentioned: boost to 1.0
        """
        if not text:
            return 0.0
            
        text_lower = text.lower()
        
        KENYA_LOCATIONS = [
            "nairobi", "kileleshwa", "rongai", "ruaka",
            "syokimau", "westlands", "mombasa",
            "kisumu", "nakuru"
        ]
        
        for loc in KENYA_LOCATIONS:
            if loc in text_lower:
                return 1.0
        
        return 0.0
    
    # ============================================================
    # PLATFORM RELIABILITY SCORE (Weight: 5%)
    # Higher trust platforms
    # ============================================================
    
    def score_platform_reliability(self, source: str) -> float:
        """
        Score platform reliability (0.0 to 1.0).
        
        Platform reliability:
        - facebook group: 1.0
        - telegram group: 0.9
        - jiji: 0.8
        - pigiame: 0.8
        - twitter: 0.6
        - unknown: 0.4
        """
        source_lower = (source or "").lower()
        
        if "facebook" in source_lower:
            return 1.0
        if "telegram" in source_lower:
            return 0.9
        if "jiji" in source_lower:
            return 0.8
        if "pigiame" in source_lower:
            return 0.8
        if "twitter" in source_lower:
            return 0.6
        
        return 0.4  # Unknown
    
    # ============================================================
    # RECENCY SCORE (Weight: 5%)
    # Fresher leads are better
    # ============================================================
    
    def score_recency(self, hours_old: int = 0) -> float:
        """
        Score recency (0.0 to 1.0).
        
        Recency scoring:
        - Within 24 hours: 1.0
        - Within 7 days: 0.7
        - Older: 0.3
        """
        if hours_old < 24:
            return 1.0
        if hours_old < 168:  # 7 days
            return 0.7
        return 0.3
    
    # ============================================================
    # MAIN SCORING METHOD
    # ============================================================
    
    def calculate_score(self, 
                       text: str, 
                       source: str = "",
                       hours_old: int = 0,
                       target_location: str = "Kenya") -> Dict[str, Any]:
        """
        Calculate weighted lead score using Kenya-optimized formula.
        
        FORMULA:
        FINAL_SCORE =
            (0.40 * intent_signal_score) +
            (0.20 * urgency_score) +
            (0.20 * budget_score) +
            (0.10 * location_score) +
            (0.05 * platform_reliability_score) +
            (0.05 * recency_score)
        """
        # Calculate component scores
        intent_score = self.score_intent_signal(text)
        urgency_score = self.score_urgency(text)
        budget_score = self.score_budget(text)
        location_score = self.score_location(text, target_location)
        platform_score = self.score_platform_reliability(source)
        recency_score = self.score_recency(hours_old)
        
        # Weighted total
        total_score = (
            self.weights.intent_signal * intent_score +
            self.weights.urgency * urgency_score +
            self.weights.budget * budget_score +
            self.weights.location * location_score +
            self.weights.platform_reliability * platform_score +
            self.weights.recency * recency_score
        )
        
        # Determine badge (Kenya-optimized thresholds)
        if total_score >= 0.70:
            badge = "HOT"
        elif total_score >= 0.50:
            badge = "WARM"
        elif total_score >= KENYA_INTENT_THRESHOLD:  # 0.18
            badge = "COLD"
        else:
            badge = "REJECT"
        
        return {
            "total_score": round(total_score, 3),
            "threshold": KENYA_INTENT_THRESHOLD,
            "threshold_passed": total_score >= KENYA_INTENT_THRESHOLD,
            "badge": badge,
            "components": {
                "intent_signal": {
                    "score": round(intent_score, 2),
                    "weight": self.weights.intent_signal,
                    "contribution": round(self.weights.intent_signal * intent_score, 3)
                },
                "urgency": {
                    "score": round(urgency_score, 2),
                    "weight": self.weights.urgency,
                    "contribution": round(self.weights.urgency * urgency_score, 3)
                },
                "budget": {
                    "score": round(budget_score, 2),
                    "weight": self.weights.budget,
                    "contribution": round(self.weights.budget * budget_score, 3)
                },
                "location": {
                    "score": round(location_score, 2),
                    "weight": self.weights.location,
                    "contribution": round(self.weights.location * location_score, 3)
                },
                "platform_reliability": {
                    "score": round(platform_score, 2),
                    "weight": self.weights.platform_reliability,
                    "contribution": round(self.weights.platform_reliability * platform_score, 3)
                },
                "recency": {
                    "score": round(recency_score, 2),
                    "weight": self.weights.recency,
                    "contribution": round(self.weights.recency * recency_score, 3)
                },
            }
        }


# Global model instance
kenya_scoring_model = KenyaLeadScoringModel()

# Kenya-optimized threshold
MIN_ACCEPTABLE_SCORE = KENYA_INTENT_THRESHOLD  # 0.18


def score_lead_kenya(text: str, 
                     source: str = "",
                     hours_old: int = 0,
                     location: str = "Kenya") -> Dict[str, Any]:
    """
    Score a lead using Kenya-optimized model.
    
    Usage:
        result = score_lead_kenya("Natafuta pipes budget 50k Westlands urgently")
        print(result["total_score"])  # 0.92
        print(result["badge"])        # "HOT"
    """
    return kenya_scoring_model.calculate_score(text, source, hours_old, location)


def calculate_final_score(text: str, platform: str, age_hours: int) -> float:
    """
    Calculate final weighted score for a lead.
    
    Kenya-optimized formula:
        score = (
            0.40 * intent_signal_score(text) +
            0.20 * urgency_score(text) +
            0.20 * budget_score(text) +
            0.10 * location_score(text) +
            0.05 * platform_score(platform) +
            0.05 * recency_score(age_hours)
        )
    
    Threshold: MIN_ACCEPTABLE_SCORE = 0.18
    
    Returns:
        Final score rounded to 3 decimal places
    """
    model = kenya_scoring_model
    
    score = (
        0.40 * model.score_intent_signal(text) +
        0.20 * model.score_urgency(text) +
        0.20 * model.score_budget(text) +
        0.10 * model.score_location(text) +
        0.05 * model.score_platform_reliability(platform) +
        0.05 * model.score_recency(age_hours)
    )
    
    return round(score, 3)


# Documentation
KENYA_SCORING_DOCUMENTATION = """
Kenya-Optimized Lead Scoring Model
====================================

FORMULA:
FINAL_SCORE =
    (0.40 * intent_signal_score) +
    (0.20 * urgency_score) +
    (0.20 * budget_score) +
    (0.10 * location_score) +
    (0.05 * platform_reliability_score) +
    (0.05 * recency_score)

INTENT SIGNAL TIERS (40% weight):
- STRONG (+1.0): natafuta, nahitaji, looking for, wtb, cash ready, need urgently
- MEDIUM (+0.7): any leads, who knows, recommend, dm me, inbox me
- WEAK (+0.4): price, available, how much

THRESHOLDS (Kenya-Optimized):
- HOT:    score >= 0.70
- WARM:   score >= 0.50
- COLD:   score >= 0.18 (minimum)
- REJECT: score < 0.18

KENYAN BUYER CHARACTERISTICS:
- Direct (high intent weight: 0.40)
- Budget-heavy (high budget weight: 0.20)
- Location-heavy (location weight: 0.10)
- Urgency-driven (urgency weight: 0.20)
- Mixed Swahili + English
- Often informal

ENVIRONMENT VARIABLES:
SCORE_WEIGHT_INTENT=0.40
SCORE_WEIGHT_URGENCY=0.20
SCORE_WEIGHT_BUDGET=0.20
SCORE_WEIGHT_LOCATION=0.10
SCORE_WEIGHT_PLATFORM=0.05
SCORE_WEIGHT_RECENCY=0.05
"""
