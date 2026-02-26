from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from app.db.models import Lead
import statistics

class DemandForecaster:
    def __init__(self, db: Session):
        self.db = db

    def get_market_trends(self, days: int = 7):
        """Analyze lead volume trends per category over the last X days."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get lead counts per category per day
        results = self.db.query(
            Lead.product_category,
            func.date(Lead.timestamp).label('day'),
            func.count(Lead.id).label('count')
        ).filter(Lead.timestamp >= cutoff_date).group_by(
            Lead.product_category,
            'day'
        ).all()
        
        trends = {}
        for category, day, count in results:
            if category not in trends:
                trends[category] = []
            trends[category].append({"date": day, "count": count})
            
        return trends

    def predict_demand_spikes(self, category: str):
        """Identify if a category is experiencing a demand spike."""
        # Get daily counts for the last 30 days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        daily_counts = self.db.query(
            func.date(Lead.timestamp).label('day'),
            func.count(Lead.id).label('count')
        ).filter(
            Lead.product_category == category,
            Lead.timestamp >= cutoff_date
        ).group_by('day').all()
        
        counts = [r.count for r in daily_counts]
        if len(counts) < 3:
            return {"status": "insufficient_data"}
            
        avg_demand = statistics.mean(counts[:-1])
        std_dev = statistics.stdev(counts[:-1]) if len(counts) > 1 else 0
        current_demand = counts[-1]
        
        # Threshold for a spike: current demand > avg + 2*std_dev
        is_spike = current_demand > (avg_demand + 2 * std_dev)
        
        return {
            "category": category,
            "avg_daily_demand": round(avg_demand, 2),
            "current_demand": current_demand,
            "is_spike": is_spike,
            "growth_rate": round(((current_demand - avg_demand) / avg_demand) * 100, 2) if avg_demand > 0 else 0
        }

    def get_emerging_markets(self):
        """Find locations (cities/regions) with rapidly increasing demand."""
        # Simple implementation: find locations with most new leads in last 24h vs last 7 days
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(days=1)
        last_7d = now - timedelta(days=7)
        
        # leads in last 24h grouped by location
        recent = self.db.query(
            Lead.location_raw,
            func.count(Lead.id).label('count')
        ).filter(Lead.timestamp >= last_24h).group_by(Lead.location_raw).all()
        
        # leads in last 7 days grouped by location
        historical = self.db.query(
            Lead.location_raw,
            func.count(Lead.id).label('count')
        ).filter(Lead.timestamp >= last_7d).group_by(Lead.location_raw).all()
        
        emerging = []
        hist_map = {loc: count for loc, count in historical}
        
        for loc, recent_count in recent:
            hist_count = hist_map.get(loc, 1) # avoid div by zero
            # Normalize hist_count to daily avg
            daily_hist_avg = hist_count / 7
            
            if recent_count > (daily_hist_avg * 1.5): # 50% increase over avg
                emerging.append({
                    "location": loc,
                    "growth_index": round(recent_count / daily_hist_avg, 2),
                    "recent_leads": recent_count
                })
                
        return sorted(emerging, key=lambda x: x['growth_index'], reverse=True)
