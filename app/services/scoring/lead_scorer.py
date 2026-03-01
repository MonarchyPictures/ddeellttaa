# app/services/scoring/lead_scorer.py
"""
Main lead scorer combining all components.

Kenya-optimized final calculation.
"""
from typing import Dict, Any

from .intent_model import score_intent_signal
from .budget_detector import score_budget
from .urgency_detector import score_urgency
from .location_detector import score_location
from .platform_detector import score_platform_reliability
from .recency_detector import score_recency


# Kenya-optimized threshold
KENYA_INTENT_THRESHOLD = 0.18
MIN_ACCEPTABLE_SCORE = KENYA_INTENT_THRESHOLD


class KenyaLeadScorer:
    """
    Kenya-optimized lead scorer.
    
    Combines all scoring components with proper weights.
    """
    
    # Component weights
    WEIGHTS = {
        "intent": 0.40,
        "urgency": 0.20,
        "budget": 0.20,
        "location": 0.10,
        "platform": 0.05,
        "recency": 0.05,
    }
    
    def calculate_score(
        self,
        text: str,
        source: str = "",
        hours_old: int = 0,
        target_location: str = "Kenya"
    ) -> Dict[str, Any]:
        """
        Calculate weighted lead score using Kenya-optimized formula.
        
        FINAL_SCORE =
            (0.40 * intent_signal_score) +
            (0.20 * urgency_score) +
            (0.20 * budget_score) +
            (0.10 * location_score) +
            (0.05 * platform_reliability_score) +
            (0.05 * recency_score)
        """
        # Calculate component scores
        intent = score_intent_signal(text)
        urgency = score_urgency(text)
        budget = score_budget(text)
        location = score_location(text, target_location)
        platform = score_platform_reliability(source)
        recency = score_recency(hours_old)
        
        # Weighted total
        total = (
            self.WEIGHTS["intent"] * intent +
            self.WEIGHTS["urgency"] * urgency +
            self.WEIGHTS["budget"] * budget +
            self.WEIGHTS["location"] * location +
            self.WEIGHTS["platform"] * platform +
            self.WEIGHTS["recency"] * recency
        )
        
        # Determine badge
        if total >= 0.70:
            badge = "HOT"
        elif total >= 0.50:
            badge = "WARM"
        elif total >= KENYA_INTENT_THRESHOLD:
            badge = "COLD"
        else:
            badge = "REJECT"
        
        return {
            "total_score": round(total, 3),
            "threshold": KENYA_INTENT_THRESHOLD,
            "threshold_passed": total >= KENYA_INTENT_THRESHOLD,
            "badge": badge,
            "components": {
                "intent": {
                    "score": round(intent, 2),
                    "weight": self.WEIGHTS["intent"],
                    "contribution": round(self.WEIGHTS["intent"] * intent, 3)
                },
                "urgency": {
                    "score": round(urgency, 2),
                    "weight": self.WEIGHTS["urgency"],
                    "contribution": round(self.WEIGHTS["urgency"] * urgency, 3)
                },
                "budget": {
                    "score": round(budget, 2),
                    "weight": self.WEIGHTS["budget"],
                    "contribution": round(self.WEIGHTS["budget"] * budget, 3)
                },
                "location": {
                    "score": round(location, 2),
                    "weight": self.WEIGHTS["location"],
                    "contribution": round(self.WEIGHTS["location"] * location, 3)
                },
                "platform": {
                    "score": round(platform, 2),
                    "weight": self.WEIGHTS["platform"],
                    "contribution": round(self.WEIGHTS["platform"] * platform, 3)
                },
                "recency": {
                    "score": round(recency, 2),
                    "weight": self.WEIGHTS["recency"],
                    "contribution": round(self.WEIGHTS["recency"] * recency, 3)
                },
            }
        }


# Global scorer instance
_kenya_scorer = KenyaLeadScorer()


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
    score = (
        0.40 * score_intent_signal(text) +
        0.20 * score_urgency(text) +
        0.20 * score_budget(text) +
        0.10 * score_location(text) +
        0.05 * score_platform_reliability(platform) +
        0.05 * score_recency(age_hours)
    )
    
    return round(score, 3)


def score_lead_kenya(
    text: str,
    source: str = "",
    hours_old: int = 0,
    location: str = "Kenya"
) -> Dict[str, Any]:
    """
    Score a lead using Kenya-optimized model.
    
    Usage:
        result = score_lead_kenya("Natafuta pipes budget 50k Westlands urgently")
        print(result["total_score"])  # 0.92
        print(result["badge"])        # "HOT"
    """
    return _kenya_scorer.calculate_score(text, source, hours_old, location)
