import statistics
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta, timezone
from ..db import models

logger = logging.getLogger(__name__)

def get_recent_prices(vehicle_model: str, db: Session, days: int = 30):
    """Fetches prices for a specific vehicle model from the last N days."""
    if not vehicle_model:
        return []
        
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Query for leads with the same model, having a price, and from the recent period
    leads = db.query(models.Lead.price).filter(
        and_(
            models.Lead.product_category == vehicle_model,
            models.Lead.price.isnot(None),
            models.Lead.price > 0,
            models.Lead.created_at >= since
        )
    ).all()
    
    return [l.price for l in leads]

def market_price(vehicle_model: str, db: Session):
    """Calculates the median market price for a vehicle model."""
    prices = get_recent_prices(vehicle_model, db)
    if not prices or len(prices) < 3: # Need at least a few samples for a meaningful median
        return None
    return statistics.median(prices)

def undercut_score(lead: models.Lead, db: Session):
    """
    Determines if a lead is priced below the market average.
    Returns: "🔥 Massive Undercut", "⚠️ Undercut", or None
    """
    if not lead.price or not lead.product_category:
        return None
        
    avg = market_price(lead.product_category, db)
    
    if not avg:
        return None
        
    diff = (avg - lead.price) / avg
    
    if diff >= 0.15:
        return "🔥 Massive Undercut"
    if diff >= 0.07:
        return "⚠️ Undercut"
    return None
