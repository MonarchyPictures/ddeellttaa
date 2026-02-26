from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta, timezone
from ..db import models
from .pricing import undercut_score
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_top_leads(db: Session, last_hours: int = 24) -> List[models.Lead]:
    """Fetch high-quality leads from the last N hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=last_hours)
    
    return db.query(models.Lead).filter(
        and_(
            models.Lead.created_at >= since,
            models.Lead.intent_score >= 0.7,
            models.Lead.property_country == "Kenya"
        )
    ).order_by(models.Lead.intent_score.desc()).all()

def aggregate_by_product(leads: List[models.Lead]) -> List[Dict[str, Any]]:
    """Identifies rising demand by grouping leads by product category."""
    counts = {}
    for lead in leads:
        category = lead.product_category or "Unknown"
        counts[category] = counts.get(category, 0) + 1
    
    # Sort by frequency to find 'hot' categories
    sorted_categories = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [{"category": m, "count": c} for m, c in sorted_categories[:5]]

def daily_intelligence_digest(db: Session) -> Dict[str, Any]:
    """
    Generates the daily retention digest:
    - 🔥 Hottest deals (Top 5 by intent)
    - 📈 Rising demand (Aggregated categories)
    - 🚨 Urgent requests (High urgency flag)
    - 💰 High value opportunities (High intent score)
    """
    leads = get_top_leads(db, last_hours=24)
    
    if not leads:
        logger.info("DIGEST: No high-quality leads found in the last 24 hours.")
        return {
            "hot_deals": [],
            "high_demand_categories": [],
            "urgent_sales": [],
            "high_intent_opportunities": []
        }

    # 🔥 Top 5 Deals
    hot_deals = [l.to_dict() for l in leads[:5]]
    
    # 📈 Rising Demand
    high_demand = aggregate_by_product(leads)
    
    # 🚨 Urgent Requests
    urgent = [l.to_dict() for l in leads if l.urgency_level == "high"]
    
    # 💰 High Intent Opportunities
    high_intent = [l.to_dict() for l in leads if l.intent_score >= 0.85]

    logger.info(f"DIGEST GENERATED: {len(hot_deals)} deals, {len(urgent)} urgent, {len(high_intent)} high intent.")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hot_deals": hot_deals,
        "high_demand_categories": high_demand,
        "urgent_sales": urgent,
        "high_intent_opportunities": high_intent[:5]
    }

def build_digest_html(digest_data: Dict[str, Any]) -> str:
    """Formats the digest data into a high-conversion HTML email."""
    if not digest_data["hot_deals"]:
        return "<h3>No new market signals today. Stay tuned!</h3>"

    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #eee; padding: 20px;">
        <h2 style="color: #2563eb;">Today’s Market Demand (Kenya)</h2>
        <hr>
        
        <h3>📈 Rising Demand</h3>
        <ul>
    """
    
    for item in digest_data.get("high_demand_categories", []):
        html += f"<li><b>{item['category']}</b> — demand rising (+{item['count'] * 5}%)</li>"
        
    html += """
        </ul>
        
        <h3>🎯 High Intent Opportunities</h3>
        <ul>
    """
    
    for item in digest_data.get("high_intent_opportunities", []):
        html += f"<li>High Intent: {item['product']} request detected</li>"
        
    html += f"""
        </ul>
        
        <h3>🚨 Urgent Buyers</h3>
        <p>{len(digest_data['urgent_sales'])} urgent buyers ready to close fast.</p>
        
        <div style="margin-top: 30px; text-align: center;">
            <a href="https://delta-9.io/leads" style="background-color: #2563eb; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">View all leads →</a>
        </div>
        
        <p style="font-size: 12px; color: #666; margin-top: 40px;">
            You are receiving this because you are a premium subscriber to Delta9 Market Intelligence.
        </p>
    </div>
    """
    return html
