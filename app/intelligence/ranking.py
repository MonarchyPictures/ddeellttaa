
class RankingEngine:
    """
    🎯 RANKING ENGINE (Runs After Save)
    
    Calculates a unified priority score for every lead to determine:
    1. High Priority -> Immediate Notification
    2. Medium Priority -> Silent Storage
    3. Low Priority -> Archive Bucket
    
    Formula:
    ranked_score = (intent_score * 0.4) + (geo_score * 0.3) + (urgency_boost * 0.2) + (source_weight * 0.1)
    """
    
    def __init__(self):
        # Weights defined in requirements
        self.W_INTENT = 0.4
        self.W_GEO = 0.3
        self.W_URGENCY = 0.2
        self.W_SOURCE = 0.1
        
        # Thresholds
        self.THRESHOLD_HIGH = 0.75  # Notification (Immediate)
        self.THRESHOLD_MEDIUM = 0.5 # Badge Only
        # Below 0.5 = Silent / Archive
        
        # Source Weights (0.0 - 1.0)
        self.SOURCE_WEIGHTS = {
            "twitter": 1.0,   # Real-time, high urgency usually
            "facebook": 0.8,  # Good but can be slower
            "instagram": 0.7, # Visual, sometimes less direct
            "reddit": 0.6,    # Discussion based, often research phase
            "jiji": 0.9,      # High intent marketplace
            "default": 0.5
        }
        
        # Urgency Mapping
        self.URGENCY_MAP = {
            "high": 1.0,
            "medium": 0.6,
            "low": 0.2,
            None: 0.0
        }

    def calculate_score(self, lead_data: dict) -> float:
        """
        Calculate the ranked_score based on normalized lead data.
        """
        # 1. Intent Score (0.0 - 1.0)
        intent_score = float(lead_data.get("intent_score", 0.0))
        
        # 2. Geo Score (0.0 - 1.0)
        geo_score = float(lead_data.get("geo_score", 0.0))
        
        # 3. Urgency Boost (Derived from urgency_level or urgency_score)
        urgency_val = lead_data.get("urgency_level", "low")
        if isinstance(urgency_val, (int, float)):
             # If it's already a score, use it directly (clamped 0-1)
             urgency_boost = min(max(float(urgency_val), 0.0), 1.0)
        else:
            urgency_boost = self.URGENCY_MAP.get(str(urgency_val).lower(), 0.0)
            
        # 4. Source Weight
        source = str(lead_data.get("source_platform", "default")).lower()
        source_weight = self.SOURCE_WEIGHTS.get(source, self.SOURCE_WEIGHTS["default"])
        
        # Calculate Weighted Sum
        ranked_score = (
            (intent_score * self.W_INTENT) +
            (geo_score * self.W_GEO) +
            (urgency_boost * self.W_URGENCY) +
            (source_weight * self.W_SOURCE)
        )
        
        return round(ranked_score, 4)

    def classify_lead(self, score: float) -> str:
        """
        Classify lead based on score.
        Returns: 'HIGH', 'MEDIUM', or 'LOW'
        """
        if score >= self.THRESHOLD_HIGH:
            return "HIGH"
        elif score >= self.THRESHOLD_MEDIUM:
            return "MEDIUM"
        else:
            return "LOW"
