# app/services/pipeline/kenya_pipeline.py
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
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.models.lead import Lead
from app.services.scoring import score_lead_kenya, KENYA_INTENT_THRESHOLD


class KenyaLeadPipeline:
    """
    Kenya-optimized lead discovery pipeline.
    """
    
    def __init__(self, dedup_engine=None):
        self.dedup_engine = dedup_engine
        self.leads_cache: List[Lead] = []
    
    def process_raw_leads(self, raw_leads: List[Dict[str, Any]]) -> List[Lead]:
        """
        Process raw leads through full pipeline.
        
        Returns list of validated Lead objects.
        """
        processed = []
        
        for raw in raw_leads:
            lead = self.process_single_lead(raw)
            if lead:
                processed.append(lead)
        
        return processed
    
    def process_single_lead(self, raw: Dict[str, Any]) -> Lead:
        """
        Process a single raw lead through the pipeline.
        """
        text = raw.get("snippet", "") or raw.get("title", "")
        source = raw.get("source", "")
        
        # Step 1: Full weighted scoring
        hours_old = raw.get("hours_old", 0)
        scoring_result = score_lead_kenya(text, source, hours_old)
        
        # Step 2: Intent validation - reject if no buyer intent detected
        intent_component = scoring_result["components"]["intent"]
        if intent_component["score"] == 0.0:
            # No buyer intent detected - likely a seller or irrelevant
            return None
        
        # Step 3: Threshold check (Kenya: 0.18)
        if not scoring_result["threshold_passed"]:
            return None
        
        # Step 4: Build Lead object
        lead = Lead(
            title=raw.get("title", ""),
            snippet=text,
            url=raw.get("url", ""),
            source=source,
            location=raw.get("location", ""),
            contact_phone=raw.get("contact_phone", ""),
            contact_name=raw.get("contact_name", ""),
            # Scores
            intent_score=scoring_result["total_score"],
            urgency_score=scoring_result["components"]["urgency"]["score"],
            budget_score=scoring_result["components"]["budget"]["score"],
            location_score=scoring_result["components"]["location"]["score"],
            # Badge
            badge=scoring_result["badge"],
            scraped_at=raw.get("scraped_at") or datetime.now(timezone.utc),
        )
        
        # Step 5: Deduplication check
        if self.dedup_engine and self.dedup_engine.is_duplicate(lead, self.leads_cache):
            return None
        
        self.leads_cache.append(lead)
        return lead


def process_leads(raw_leads: List[Dict[str, Any]], dedup_engine=None) -> List[Lead]:
    """
    Convenience function to process leads without instantiating pipeline.
    """
    pipeline = KenyaLeadPipeline(dedup_engine)
    return pipeline.process_raw_leads(raw_leads)
