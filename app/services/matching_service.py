import logging
import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.db.models import BuyerIntent
from app.intelligence.matcher import buyer_match_score
from app.services.notification_service import create_notification, send_instant_notification

logger = logging.getLogger(__name__)

class MatchingService:
    """
    Real-Time Matching Service.
    Objective: Fulfill the promise of a seller finding a buyer immediately.
    """

    def __init__(self, db: Session):
        self.db = db
        self.min_confidence = 0.4  # User requested 0.4

    def process_lead(self, lead: Lead) -> List[Dict[str, Any]]:
        """
        Main entry point.
        When a new lead enters the system, this service immediately queries the database for its inverse.
        """
        try:
            logger.info(f"MATCHING: Processing new lead {lead.id} ({lead.title})...")
            
            matches = self.find_matches(lead)
            
            if matches:
                logger.info(f"MATCHING: Found {len(matches)} potential matches for lead {lead.id}")
                self.notify_matches(lead, matches)
            else:
                logger.info(f"MATCHING: No matches found for lead {lead.id}")
                
            return matches
        except Exception as e:
            logger.error(f"CRITICAL ERROR in Matching Service: {e}", exc_info=True)
            # Self-healing: Ensure we don't crash the main process, return empty matches
            return []

    def find_matches(self, lead: Lead) -> List[Dict[str, Any]]:
        """
        Search for active buy leads/intents that match the incoming sell lead.
        """
        # Get all active buyer intents
        # Optimization: In production, use vector search or filtered SQL queries
        active_intents = self.db.query(BuyerIntent).filter(
            BuyerIntent.is_active == True
        ).all()
        
        valid_matches = []
        
        for intent in active_intents:
            score = self.calculate_match_confidence(lead, intent)
            
            if score >= self.min_confidence:
                valid_matches.append({
                    "intent": intent,
                    "score": score,
                    "reasons": self._explain_match(lead, intent)
                })
        
        # Sort by score descending
        valid_matches.sort(key=lambda x: x["score"], reverse=True)
        return valid_matches

    def calculate_match_confidence(self, lead: Lead, intent: BuyerIntent) -> float:
        """
        Score the match based on:
        - Keyword overlap
        - Price proximity
        - Location proximity
        - Recency
        """
        score = 0.0
        
        # 1. Keyword Overlap (40%)
        # Simple containment check for now
        # INCLUDE SNIPPET AND QUERY FOR BETTER MATCHING
        lead_text = (f"{lead.title} {lead.description or ''} {lead.product_category or ''} {lead.buyer_request_snippet or ''} {lead.query or ''}").lower()
        
        # Fallback to interest_type if keywords missing (Legacy support)
        intent_kw_str = intent.keywords or intent.interest_type or ""
        intent_keywords = intent_kw_str.lower().split(",")
        
        match_count = 0
        for kw in intent_keywords:
            kw = kw.strip()
            if kw and kw in lead_text:
                match_count += 1
        
        if match_count > 0:
            # Boost for multiple keyword matches
            score += 0.4 * min(match_count / max(len(intent_keywords), 1), 1.0)
            
        # 2. Price Proximity (30%)
        lead_price = self._parse_price(lead.price)
        
        if lead_price > 0 and intent.min_price and intent.max_price:
            if intent.min_price <= lead_price <= intent.max_price:
                score += 0.3
            elif intent.min_price * 0.8 <= lead_price <= intent.max_price * 1.2:
                # Close enough (within 20%)
                score += 0.15
                
        # 3. Location Proximity (20%)
        if lead.location and intent.location:
            if lead.location.lower() == intent.location.lower():
                score += 0.2
            elif intent.location.lower() in lead.location.lower():
                 score += 0.2
                 
        # 4. Recency (10%)
        # New leads are hot
        score += 0.1
        
        return round(min(score, 1.0), 2)

    def _explain_match(self, lead: Lead, intent: BuyerIntent) -> List[str]:
        reasons = []
        lead_text = (f"{lead.title} {lead.description or ''}").lower()
        
        intent_kw_str = intent.keywords or intent.interest_type or ""
        intent_keywords = intent_kw_str.lower().split(",")
        
        matched_kws = [kw.strip() for kw in intent_keywords if kw.strip() and kw.strip() in lead_text]
        if matched_kws:
            reasons.append(f"Keywords matched: {', '.join(matched_kws)}")
            
        lead_price = self._parse_price(lead.price)
        if lead_price > 0 and intent.min_price and intent.max_price:
             if intent.min_price <= lead_price <= intent.max_price:
                 reasons.append(f"Price ({lead_price}) within budget")
                 
        if lead.location and intent.location and lead.location.lower() == intent.location.lower():
            reasons.append("Exact location match")
            
        return reasons

    def _parse_price(self, price_str: Any) -> float:
        if not price_str:
            return 0.0
        try:
            if isinstance(price_str, (int, float)):
                return float(price_str)
            # Remove non-numeric except dot
            clean = re.sub(r'[^\d.]', '', str(price_str))
            return float(clean) if clean else 0.0
        except:
            return 0.0

    def notify_matches(self, lead: Lead, matches: List[Dict[str, Any]]):
        """
        Trigger immediate notifications.
        - WebSocket (Frontend)
        - Email
        - SMS
        """
        for match in matches:
            intent = match["intent"]
            score = match["score"]
            reasons = match["reasons"]
            
            logger.info(f"🔔 NOTIFY: Match found for Buyer {intent.user_id} (Score: {score}) - {reasons}")
            
            # Send Instant Notifications (Email, SMS, WebSocket)
            try:
                # Prepare match data for notification
                match_data = {
                    "score": score,
                    "reasons": reasons,
                    "lead_id": str(lead.id),
                    "lead_title": lead.title,
                    "lead_price": lead.price,
                    "lead_location": lead.location
                }
                
                send_instant_notification(intent, match_data)
                
            except Exception as e:
                # Self-healing: Log error but continue to next match
                logger.error(f"Failed to send notification to {intent.user_id}: {e}")
