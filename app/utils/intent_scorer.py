"""
AI Intent Scorer for Lead Classification

Scores leads based on buying intent from 0-100:
- HOT (80-100): Urgent buyer, ready to purchase
- WARM (60-79): Active buyer, researching  
- COLD (40-59): Passive interest, considering
- REJECT (<40): Not a genuine buyer

Scoring Factors:
1. Urgency indicators (+30 points)
2. Specific product mentions (+25 points)
3. Buying action words (+20 points)
4. Price/budget mention (+15 points)
5. Contact readiness (+10 points)
6. Negative signals (-20 to -40 points)

Examples:
    "I need Toyota Vitz urgently today" → 95 (HOT)
    "Looking for Vitz 2016 model" → 72 (WARM)
    "Thinking about maybe buying a car" → 45 (COLD)
    "Just browsing cars for fun" → 25 (REJECT)
"""
import re
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class LeadTemperature(str, Enum):
    """Lead temperature categories"""
    HOT = "HOT"      # 80-100: Urgent buyer
    WARM = "WARM"    # 60-79: Active buyer
    COLD = "COLD"    # 40-59: Passive interest
    REJECT = "REJECT" # <40: Not a buyer


@dataclass
class IntentScore:
    """Intent scoring result"""
    score: int  # 0-100
    temperature: LeadTemperature
    breakdown: Dict[str, int]  # Point breakdown
    reasoning: str  # Human-readable explanation


class IntentScorer:
    """
    AI-powered intent scorer for lead classification.
    
    Analyzes text for buying signals and scores 0-100.
    """
    
    # ═══════════════════════════════════════════════════════════════
    # SCORING CRITERIA
    # ═══════════════════════════════════════════════════════════════
    
    # URGENCY INDICATORS (+30 max)
    URGENCY_KEYWORDS = {
        # High urgency (+30)
        r'\burgently?\b': 30,
        r'\bimmediately\b': 30,
        r'\basap\b': 30,
        r'\btoday\b': 25,
        r'\bnow\b': 25,
        r'\byesterday\b': 30,
        r'\bhapo sasa\b': 30,  # Swahili
        r'\bsasa hivi\b': 30,  # Swahili
        
        # Medium urgency (+20)
        r'\bthis week\b': 20,
        r'\bsoon\b': 15,
        r'\bquickly\b': 15,
        r'\bfast\b': 15,
        
        # Low urgency (+10)
        r'\bthis month\b': 10,
    }
    
    # SPECIFIC PRODUCT (+25 max)
    SPECIFICITY_INDICATORS = {
        # Very specific (+25)
        r'\b(?:toyota|honda|nissan|mazda|subaru|bmw|mercedes|vw|volkswagen)\s+\w+\s*(?:\d{4}|\d{2})?\b': 25,
        r'\b\w+\s+vitz\s*(?:\d{4}|\d{2})?\b': 25,
        r'\b\w+\s+fielder\s*(?:\d{4}|\d{2})?\b': 25,
        r'\b\w+\s+probox\s*(?:\d{4}|\d{2})?\b': 25,
        r'\b\w+\s+hiace\s*(?:\d{4}|\d{2})?\b': 25,
        r'\b\w+\s+premio\s*(?:\d{4}|\d{2})?\b': 25,
        r'\b\w+\s+axio\s*(?:\d{4}|\d{2})?\b': 25,
        
        # Model year mentioned (+20)
        r'\b20\d{2}\s+(?:model|edition)\b': 20,
        r'\b(?:20\d{2}|\'\d{2})\s*\w+\b': 20,
        
        # Color preference (+15)
        r'\b(?:white|black|silver|grey|red|blue)\s+(?:one|color|paint)\b': 15,
    }
    
    # BUYING ACTION WORDS (+20 max)
    BUYING_KEYWORDS = {
        # Strong buying intent (+20)
        r'\bneed\b': 20,
        r'\bwant\s+to\s+buy\b': 20,
        r'\blooking\s+for\b': 18,
        r'\bsearching\s+for\b': 18,
        r'\btrying\s+to\s+find\b': 18,
        r'\bnatafuta\b': 20,  # Swahili
        r'\bnahitaji\b': 20,  # Swahili
        
        # Medium buying intent (+15)
        r'\binterested\s+in\s+buying\b': 15,
        r'\bwant\b': 15,
        r'\bwould\s+like\b': 12,
        r'\bplanning\s+to\s+buy\b': 12,
        
        # Weak buying intent (+8)
        r'\bconsidering\b': 8,
        r'\bthinking\s+about\b': 8,
        r'\bmight\s+buy\b': 8,
    }
    
    # PRICE/BUDGET MENTION (+15 max)
    PRICE_KEYWORDS = {
        r'\bbudget\b': 15,
        r'\bksh\s*\d+': 15,
        r'\b\d+\s*k\b': 15,
        r'\b\d+\s*thousand\b': 15,
        r'\bpesa\s+\d+': 15,  # Swahili
        r'\bbei\b': 12,  # Swahili
        r'\baround\s+\d+': 12,
        r'\bbetween\s+\d+\s+and\s+\d+': 15,
        r'\b\d+\s*-\s*\d+\s*k': 15,
    }
    
    # CONTACT READINESS (+10 max)
    CONTACT_KEYWORDS = {
        r'\bcall\s+me\b': 10,
        r'\btext\s+me\b': 10,
        r'\bwhatsapp\b': 10,
        r'\bDM\b': 8,
        r'\binbox\b': 8,
        r'\bcontact\b': 8,
        r'\breach\s+out\b': 8,
        r'\b\d{10,12}\b': 10,  # Phone number present
    }
    
    # NEGATIVE SIGNALS (-40 to -20)
    NEGATIVE_KEYWORDS = {
        # Strong negative (-40)
        r'\bjust\s+(?:browsing|looking)\b': -40,
        r'\bfor\s+fun\b': -40,
        r'\bcurious\b': -35,
        r'\bwindow\s+shopping\b': -40,
        
        # Medium negative (-30)
        r'\bmaybe\s+(?:later|someday)\b': -30,
        r'\bnot\s+sure\b': -25,
        r'\bthinking\b': -20,
        r'\bconsidering\b': -20,
        
        # Weak negative (-20)
        r'\bif\s+i\s+get\b': -20,
        r'\bwould\s+be\s+nice\b': -20,
        r'\bdream\s+car\b': -20,
    }
    
    # QUALITY INDICATORS (+5 to +10)
    QUALITY_KEYWORDS = {
        r'\bgood\s+condition\b': 5,
        r'\bclean\b': 5,
        r'\bwelle?\s+maintained\b': 5,
        r'\boriginal\s+paint\b': 5,
        r'\bfull\s+documents\b': 5,
        r'\bready\s+for\s+transfer\b': 10,
    }
    
    @classmethod
    def calculate_score(cls, text: str) -> IntentScore:
        """
        Calculate intent score (0-100) for lead text.
        
        Args:
            text: Lead message/text
            
        Returns:
            IntentScore with breakdown and reasoning
        """
        if not text:
            return IntentScore(
                score=0,
                temperature=LeadTemperature.REJECT,
                breakdown={},
                reasoning="Empty text"
            )
        
        text_lower = text.lower()
        breakdown = {}
        total_score = 0
        
        # Calculate each category
        categories = [
            ("Urgency", cls.URGENCY_KEYWORDS),
            ("Specificity", cls.SPECIFICITY_INDICATORS),
            ("Buying Intent", cls.BUYING_KEYWORDS),
            ("Price/Budget", cls.PRICE_KEYWORDS),
            ("Contact Ready", cls.CONTACT_KEYWORDS),
            ("Quality Indicators", cls.QUALITY_KEYWORDS),
            ("Negative Signals", cls.NEGATIVE_KEYWORDS),
        ]
        
        for category_name, keywords in categories:
            category_score = 0
            for pattern, points in keywords.items():
                if re.search(pattern, text_lower, re.IGNORECASE):
                    category_score += points
            
            breakdown[category_name] = category_score
            total_score += category_score
        
        # Ensure score is within 0-100
        total_score = max(0, min(100, total_score))
        
        # Determine temperature
        temperature = cls._get_temperature(total_score)
        
        # Generate reasoning
        reasoning = cls._generate_reasoning(total_score, breakdown, text)
        
        return IntentScore(
            score=total_score,
            temperature=temperature,
            breakdown=breakdown,
            reasoning=reasoning
        )
    
    @classmethod
    def _get_temperature(cls, score: int) -> LeadTemperature:
        """Get temperature category from score"""
        if score >= 75:
            return LeadTemperature.HOT
        elif score >= 50:
            return LeadTemperature.WARM
        elif score >= 25:
            return LeadTemperature.COLD
        else:
            return LeadTemperature.REJECT
    
    @classmethod
    def _generate_reasoning(cls, score: int, breakdown: Dict[str, int], text: str) -> str:
        """Generate human-readable reasoning"""
        reasons = []
        
        # Positive factors
        if breakdown.get("Urgency", 0) >= 20:
            reasons.append("High urgency detected")
        if breakdown.get("Specificity", 0) >= 20:
            reasons.append("Specific product mentioned")
        if breakdown.get("Buying Intent", 0) >= 15:
            reasons.append("Strong buying intent")
        if breakdown.get("Price/Budget", 0) > 0:
            reasons.append("Budget mentioned")
        if breakdown.get("Contact Ready", 0) >= 8:
            reasons.append("Ready for contact")
        
        # Negative factors
        if breakdown.get("Negative Signals", 0) < -20:
            reasons.append("Weak commitment signals")
        
        if not reasons:
            if score >= 60:
                reasons.append("Moderate buying interest")
            elif score >= 40:
                reasons.append("Casual interest only")
            else:
                reasons.append("Not a serious buyer")
        
        return "; ".join(reasons)
    
    @classmethod
    def classify(cls, text: str) -> Tuple[str, int, str]:
        """
        Quick classification - returns (temperature, score, reasoning).
        
        Args:
            text: Lead text
            
        Returns:
            Tuple of (temperature, score, reasoning)
        """
        result = cls.calculate_score(text)
        return (
            result.temperature.value,
            result.score,
            result.reasoning
        )


# Convenience functions
def score_intent(text: str) -> int:
    """Quick score 0-100"""
    return IntentScorer.calculate_score(text).score


def classify_intent(text: str) -> str:
    """Quick classification (HOT/WARM/COLD/REJECT)"""
    return IntentScorer.calculate_score(text).temperature.value


def get_intent_details(text: str) -> Dict[str, Any]:
    """Get full scoring details"""
    result = IntentScorer.calculate_score(text)
    return {
        "score": result.score,
        "temperature": result.temperature.value,
        "breakdown": result.breakdown,
        "reasoning": result.reasoning
    }


# Example usage
if __name__ == "__main__":
    test_cases = [
        # HOT leads (80-100)
        ("I need Toyota Vitz urgently today", "HOT"),
        ("Looking for fielder 2016 model immediately budget 800k call 0723123456", "HOT"),
        ("Nahitaji gari urgently hapo sasa", "HOT"),
        
        # WARM leads (60-79)
        ("Looking for Vitz 2016", "WARM"),
        ("Want to buy Honda Fit this week", "WARM"),
        ("Searching for a clean premio around 1m", "WARM"),
        
        # COLD leads (40-59)
        ("Thinking of buying Vitz maybe", "COLD"),
        ("Considering getting a car", "COLD"),
        ("Might buy if I get money", "COLD"),
        
        # REJECT leads (<40)
        ("Just browsing cars for fun", "REJECT"),
        ("Dream car would be nice someday", "REJECT"),
        ("Curious about car prices", "REJECT"),
    ]
    
    print("AI Intent Scorer - Test Results")
    print("=" * 70)
    
    for text, expected_temp in test_cases:
        result = IntentScorer.calculate_score(text)
        status = "[PASS]" if result.temperature.value == expected_temp else "[FAIL]"
        
        print(f"\n{status} Score: {result.score} ({result.temperature.value})")
        print(f"Text: \"{text}\"")
        print(f"Expected: {expected_temp}")
        print(f"Reasoning: {result.reasoning}")
        print(f"Breakdown: {result.breakdown}")
