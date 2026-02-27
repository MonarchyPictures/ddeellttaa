from collections import defaultdict, deque
from datetime import datetime 
from typing import Optional, Dict, Any
import logging
from app.db.database import SessionLocal
from app.db import models

logger = logging.getLogger(__name__)

# In-memory cache for performance, synced with DB
SCRAPER_METRICS = {}
CATEGORY_STATS = {}

def sync_metrics_from_db():
    """Load metrics from database into memory on startup."""
    db = SessionLocal()
    try:
        # Load Scraper Metrics
        scrapers = db.query(models.ScraperMetric).all()
        for s in scrapers:
            SCRAPER_METRICS[s.scraper_name] = {
                "runs": s.runs,
                "leads": s.leads_found,
                "verified": s.verified_leads,
                "failures": s.failures,
                "consecutive_failures": s.consecutive_failures,
                "avg_latency": s.avg_latency or 0.0,
                "avg_confidence": s.avg_confidence or 0.0,
                "avg_freshness": s.avg_freshness or 0.0,
                "avg_geo_score": s.avg_geo_score or 0.0,
                "priority_score": s.priority_score or 0.0,
                "priority_boost": s.priority_boost or 1.0,
                "auto_disabled": bool(s.auto_disabled),
                "last_success": s.last_success,
                "history": deque(s.history or [], maxlen=20)
            }
            # Sync auto_disabled to registry if it exists
            if s.auto_disabled:
                try:
                    from .registry import SCRAPER_REGISTRY
                    if s.scraper_name in SCRAPER_REGISTRY:
                        SCRAPER_REGISTRY[s.scraper_name]["enabled"] = False
                        logger.info(f"Sync: {s.scraper_name} marked as disabled from DB metrics.")
                except ImportError:
                    pass
            
        # Load Category Stats
        categories = db.query(models.CategoryMetric).all()
        for c in categories:
            CATEGORY_STATS[c.category_name] = {
                "leads": c.total_leads,
                "verified": c.verified_leads,
                "verified_rate": c.verified_rate
            }
        logger.info(f"Metrics synced from DB: {len(SCRAPER_METRICS)} scrapers, {len(CATEGORY_STATS)} categories.")
    except Exception as e:
        logger.error(f"Failed to sync metrics from DB: {e}")
    finally:
        db.close()

def record_run(name: str, leads_count: int, latency: float = 0.0, avg_confidence: float = 0.0, avg_freshness: float = 0.0, avg_geo_score: float = 0.0, error: bool = False):
    """Update metrics for a single scraper run and persist to DB."""
    if name not in SCRAPER_METRICS:
        SCRAPER_METRICS[name] = {
            "runs": 0, "leads": 0, "verified": 0, "failures": 0, 
            "consecutive_failures": 0, "avg_latency": 0.0, "avg_confidence": 0.0, 
            "avg_freshness": 0.0, "avg_geo_score": 0.0, "priority_score": 0.0, "priority_boost": 1.0, 
            "auto_disabled": False, "last_success": None, "history": deque(maxlen=20)
        }
        
    metrics = SCRAPER_METRICS[name] 
    metrics["runs"] += 1 
    
    # 📉 Moving average for performance indicators
    if latency > 0:
        metrics["avg_latency"] = (metrics["avg_latency"] * 0.7) + (latency * 0.3) if metrics["avg_latency"] > 0 else latency
            
    if avg_confidence > 0:
        metrics["avg_confidence"] = (metrics["avg_confidence"] * 0.7) + (avg_confidence * 0.3) if metrics["avg_confidence"] > 0 else avg_confidence

    if avg_freshness > 0:
        metrics["avg_freshness"] = (metrics["avg_freshness"] * 0.7) + (avg_freshness * 0.3) if metrics["avg_freshness"] > 0 else avg_freshness

    if avg_geo_score > 0:
        metrics["avg_geo_score"] = (metrics["avg_geo_score"] * 0.7) + (avg_geo_score * 0.3) if metrics["avg_geo_score"] > 0 else avg_geo_score

    timestamp = datetime.utcnow().isoformat()
    
    if error:
        metrics["failures"] += 1
        metrics["consecutive_failures"] += 1
        metrics["history"].append({
            "timestamp": timestamp, "leads": 0, "verified": 0, "success": False, "latency": latency
        })
        
        # Self-Healing: Auto-Disable if too many failures
        if metrics["consecutive_failures"] >= 5:
            metrics["auto_disabled"] = True
            logger.critical(f"🚨 SELF-HEALING: Auto-disabling scraper {name} after 5 consecutive failures.")
            # TODO: Send admin alert
            
    else:
        metrics["consecutive_failures"] = 0
        if leads_count > 0: 
            metrics["leads"] += leads_count 
            metrics["last_success"] = datetime.utcnow() 
        metrics["history"].append({
            "timestamp": timestamp, "leads": leads_count, "verified": 0, "success": True, "latency": latency, "confidence": avg_confidence
        })

    # 🤖 SELF-OPTIMIZATION LOGIC
    # Enforce Auto-Disable based on failure rate or consecutive failures
    failure_rate = metrics["failures"] / metrics["runs"] if metrics["runs"] > 0 else 0
    
    should_disable = False
    disable_reason = ""
    
    if metrics["runs"] >= 10 and failure_rate > 0.4:
        should_disable = True
        disable_reason = f"Failure Rate {failure_rate:.2%} > 40%"
    elif metrics["consecutive_failures"] >= 5:
        should_disable = True
        disable_reason = f"{metrics['consecutive_failures']} consecutive failures"

    if should_disable and not metrics["auto_disabled"]:
        logger.warning(f"OPTIMIZER: Auto-disabling {name} ({disable_reason}, Runs: {metrics['runs']})")
        metrics["auto_disabled"] = True
        from .registry import update_scraper_state
        update_scraper_state(name, enabled=False, caller="Self-Optimization Engine")
    
    # Base boost logic
    # Start with 1.0 but allow manual overrides if we ever add a way to set them
    # For now, we calculate it dynamically
    boost = 1.0
    
    # Boost if high confidence
    if metrics["avg_confidence"] > 0.85:
        boost += 0.5
        logger.info(f"OPTIMIZER: Boosting {name} (+0.5) for high confidence ({metrics['avg_confidence']:.2f})")
        
    # Boost if fast
    if 0 < metrics["avg_latency"] < 2.0:
        boost += 0.3
        logger.info(f"OPTIMIZER: Boosting {name} (+0.3) for speed ({metrics['avg_latency']:.2f}s)")
        
    metrics["priority_boost"] = boost

    # 📈 UPDATE PRIORITY SCORE
    metrics["priority_score"] = calculate_priority(metrics)
    logger.info(f"METRICS: Updated priority score for {name} to {metrics['priority_score']}")

    # Persist to DB
    db = SessionLocal()
    try:
        db_metric = db.query(models.ScraperMetric).filter_by(scraper_name=name).first()
        if not db_metric:
            db_metric = models.ScraperMetric(scraper_name=name)
            db.add(db_metric)
        
        db_metric.runs = metrics["runs"]
        db_metric.leads_found = metrics["leads"]
        db_metric.verified_leads = metrics["verified"]
        db_metric.failures = metrics["failures"]
        db_metric.consecutive_failures = metrics["consecutive_failures"]
        db_metric.avg_latency = metrics["avg_latency"]
        db_metric.avg_confidence = metrics["avg_confidence"]
        db_metric.avg_freshness = metrics["avg_freshness"]
        db_metric.avg_geo_score = metrics.get("avg_geo_score", 0.0)
        db_metric.priority_score = metrics["priority_score"]
        db_metric.priority_boost = metrics["priority_boost"]
        db_metric.auto_disabled = 1 if metrics["auto_disabled"] else 0
        db_metric.last_success = metrics["last_success"]
        db_metric.history = list(metrics["history"])
        db.commit()
    except Exception as e:
        logger.error(f"Failed to persist run metrics for {name}: {e}")
        db.rollback()
    finally:
        db.close()

def calculate_priority(scraper: Any) -> float:
    """
    Priority formula (Geo-Marketplace Optimized):
    30% avg_confidence
    25% geo_performance (avg_geo_score)
    15% success_rate
    15% freshness_score
    15% speed (latency-based)
    """
    # Handle both dict (in-memory) and object (DB model)
    if isinstance(scraper, dict):
        runs = scraper.get("runs") or 1
        failures = scraper.get("failures") or 0
        confidence = scraper.get("avg_confidence") or 0
        geo_perf = scraper.get("avg_geo_score") or 0
        freshness = scraper.get("avg_freshness") or 1440 
        latency = scraper.get("avg_latency") or 5
        boost = scraper.get("priority_boost") or 1.0
    else:
        runs = scraper.runs or 1
        failures = scraper.failures or 0
        confidence = scraper.avg_confidence or 0
        geo_perf = getattr(scraper, 'avg_geo_score', 0)
        freshness = scraper.avg_freshness or 1440
        latency = scraper.avg_latency or 5
        boost = scraper.priority_boost or 1.0

    success_rate = max(0, (runs - failures) / runs)
    speed_score = max(0, 1 - (latency / 10))
    freshness_score = max(0, 1 - (freshness / 1440))
    if freshness <= 120:
        freshness_score = 0.8 + (0.2 * (1 - (freshness / 120)))

    base_priority = (
        (confidence * 0.30) +
        (geo_perf * 0.25) +
        (success_rate * 0.15) +
        (freshness_score * 0.15) +
        (speed_score * 0.15)
    )

    final_priority = base_priority * boost
    return round(min(final_priority, 1.0), 4)

def get_scraper_performance_score(name: str) -> float:
    """
    Calculate a unified performance score for a scraper using the standardized ranking formula.
    """
    if name not in SCRAPER_METRICS:
        return 0.5 # Default middle-ground for unknown scrapers
    
    m = SCRAPER_METRICS[name]
    
    # Priority score is already recalculated after every run in record_run
    priority_score = m.get("priority_score", 0.0)
    
    # Fallback to calculation if not yet recorded
    if priority_score == 0.0:
        priority_score = calculate_priority(m)
    
    # Penalty for consecutive failures
    cons_failures = m.get("consecutive_failures", 0)
    if cons_failures > 0:
        penalty = 0.1 * cons_failures
        priority_score = max(0, priority_score - penalty)
    
    return round(priority_score, 4)

def record_verified(name: str, verified_count: int = 1):
    """Update metrics for verified leads and persist to DB."""
    if name not in SCRAPER_METRICS: return
    
    metrics = SCRAPER_METRICS[name]
    metrics["verified"] += verified_count
    
    if metrics["history"] and metrics["history"][-1]["success"]:
        metrics["history"][-1]["verified"] += verified_count

    db = SessionLocal()
    try:
        db_metric = db.query(models.ScraperMetric).filter_by(scraper_name=name).first()
        if db_metric:
            db_metric.verified_leads = metrics["verified"]
            db_metric.history = list(metrics["history"])
            db.commit()
    except Exception as e:
        logger.error(f"Failed to persist verified metrics for {name}: {e}")
        db.rollback()
    finally:
        db.close()

def record_category_lead(category: str, is_verified: bool):
    """Track lead success rate per category and persist to DB."""
    if not category: return
    
    if category not in CATEGORY_STATS:
        CATEGORY_STATS[category] = {"leads": 0, "verified": 0, "verified_rate": 0.0}
        
    stats = CATEGORY_STATS[category]
    stats["leads"] += 1
    if is_verified:
        stats["verified"] += 1
    
    if stats["leads"] > 0:
        stats["verified_rate"] = stats["verified"] / stats["leads"]

    db = SessionLocal()
    try:
        db_cat = db.query(models.CategoryMetric).filter_by(category_name=category).first()
        if not db_cat:
            db_cat = models.CategoryMetric(category_name=category)
            db.add(db_cat)
        
        db_cat.total_leads = stats["leads"]
        db_cat.verified_leads = stats["verified"]
        db_cat.verified_rate = stats["verified_rate"]
        db.commit()
    except Exception as e:
        logger.error(f"Failed to persist category metrics for {category}: {e}")
        db.rollback()
    finally:
        db.close()

def get_metrics(name: Optional[str] = None):
    """Return metrics for one or all scrapers."""
    def format_metric(m):
        if not m:
            return {
                "runs": 0, "leads": 0, "verified": 0, "failures": 0,
                "consecutive_failures": 0, "avg_latency": 0.0, "avg_confidence": 0.0,
                "avg_freshness": 0.0, "avg_geo_score": 0.0, "priority_score": 0.0,
                "priority_boost": 1.0, "auto_disabled": False, "last_success": None,
                "history": []
            }
        res = dict(m)
        res["history"] = list(m.get("history", []))
        return res

    if name:
        return format_metric(SCRAPER_METRICS.get(name, {}))
    return {k: format_metric(v) for k, v in SCRAPER_METRICS.items()}

# Initial sync
sync_metrics_from_db()
