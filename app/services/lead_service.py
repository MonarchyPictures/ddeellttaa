from typing import List, Generator
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.lead import Lead
from app.db.models import ActivityLog
from app.intelligence_v2.thresholds import FLOOR, HIGH_INTENT, STRICT_PUBLIC

from datetime import datetime, timedelta, timezone
from sqlalchemy import func

def get_leads(limit: int, filter_type: str = None): 
    db = SessionLocal() 
    try:
        query = db.query(Lead)
        
        if filter_type == "active":
            # Active listings (24h)
            time_24h_ago = datetime.utcnow() - timedelta(hours=24)
            # Filter for recency AND minimum quality to avoid "10% score" junk
            query = query.filter(
                Lead.created_at >= time_24h_ago,
                Lead.intent_score > 0.2
            )
        elif filter_type == "high_intent":
            # High Intent Matches (intent_score > 0.8)
            query = query.filter(Lead.intent_score > 0.8)
        elif filter_type == "whatsapp":
            # WhatsApp Taps: STRICT BUYER FILTER
            # User reported sellers appearing here.
            # We must enforce:
            # 1. Has WhatsApp link
            # 2. Is NOT a Seller (intent_type != 'SELLER')
            # 3. Has decent intent score (> 0.4)
            query = query.filter(
                Lead.whatsapp_link.isnot(None),
                Lead.intent_type != 'SELLER',
                Lead.intent_score > 0.4
            )
        
        # Global Quality Filter (unless debugging)
        # Always exclude explicit sellers from ANY list unless specifically asked
        if filter_type != "all_debug":
            query = query.filter(Lead.intent_type != 'SELLER')

        # Production Hardening: Sort by Rank Score (Quality) first, then Recency
        # REMOVED strict filter(Lead.rank_score > 0.0) to allow viewing all leads including new ones
        leads = query.order_by(Lead.rank_score.desc(), Lead.created_at.desc())\
            .limit(limit)\
            .all() 
        return leads
    finally:
        db.close()

def get_dashboard_stats():
    db = SessionLocal()
    try:
        # Calculate time threshold for 24h
        time_24h_ago = datetime.utcnow() - timedelta(hours=24)
        
        # 1. Active Listings (24h)
        # Aligned with get_leads filter: No Sellers, Score > 0.2
        active_listings_24h = db.query(Lead).filter(
            Lead.created_at >= time_24h_ago,
            Lead.intent_type != 'SELLER',
            Lead.intent_score > 0.2
        ).count()
        
        # 2. Urgent Sellers (urgency_level='high' OR urgency_score > 0.7)
        # Exclude Sellers here too for consistency
        urgent_sellers = db.query(Lead).filter(
            (Lead.urgency_level == 'high') | (Lead.urgency_score > 0.7),
            Lead.intent_type != 'SELLER'
        ).count()
        
        # 3. WhatsApp Taps (using response_count as proxy or random/0 if not tracked)
        # Since we don't strictly track taps in DB yet, we'll use leads with whatsapp_link
        # as a proxy for "potential" taps or just return a placeholder.
        # Let's count leads with whatsapp links for now.
        # MUST MATCH get_leads FILTER: intent_type != 'SELLER' and intent_score > 0.4
        whatsapp_taps_today = db.query(Lead).filter(
            Lead.whatsapp_link.isnot(None),
            Lead.intent_type != 'SELLER',
            Lead.intent_score > 0.4
        ).count()
        
        # 4. High Intent Matches (intent_score > 0.8)
        # Also exclude sellers
        high_intent_matches = db.query(Lead).filter(
            Lead.intent_score > 0.8,
            Lead.intent_type != 'SELLER'
        ).count()
        
        return {
            "active_listings_24h": active_listings_24h,
            "urgent_sellers": urgent_sellers,
            "whatsapp_taps_today": whatsapp_taps_today,
            "high_intent_matches": high_intent_matches
        }
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {
            "active_listings_24h": 0,
            "urgent_sellers": 0,
            "whatsapp_taps_today": 0,
            "high_intent_matches": 0
        }
    finally:
        db.close()

def export_leads_generator(db: Session, export_type: str) -> Generator[str, None, None]:
    """Generator for streaming lead exports."""
    yield f"--- DELTA-9 LEAD EXPORT ({export_type.upper()}) ---\n"
    yield f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    
    query = db.query(Lead)
    if export_type == "active":
        query = query.filter(Lead.confidence_score >= STRICT_PUBLIC)
    elif export_type == "high_intent":
        query = query.filter(Lead.confidence_score >= HIGH_INTENT, Lead.confidence_score < STRICT_PUBLIC)
    elif export_type == "bootstrap":
        query = query.filter(Lead.confidence_score < HIGH_INTENT)

    # Stream results to avoid memory spikes
    for lead in query.yield_per(100):
        yield f"ID: {lead.id}\n"
        yield f"Product: {lead.title or lead.product_category}\n"
        yield f"Location: {lead.location_raw}\n"
        yield f"Score: {lead.confidence_score}\n"
        yield f"Snippet: {lead.buyer_request_snippet or ''}\n"
        yield f"WhatsApp: {lead.whatsapp_link or lead.contact_phone or 'N/A'}\n"
        yield "---\n\n"

def get_recent_events(db: Session, event_type: str, limit: int = 50):
    """Fetch recent activity events."""
    query = db.query(ActivityLog)
    if event_type == "whatsapp":
        query = query.filter(ActivityLog.event_type == "WHATSAPP_TAP")
    
    return query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()

