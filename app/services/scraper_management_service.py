from app.scrapers.registry import SCRAPER_REGISTRY, ACTIVE_SCRAPERS, update_scraper_state, update_scraper_mode, refresh_scraper_states
from app.scrapers.metrics import get_metrics, SCRAPER_METRICS
from app.config.scrapers import is_scraper_allowed
from datetime import datetime
from typing import Optional

def list_all_scrapers():
    """List all scrapers with their current configuration and metrics."""
    try:
        results = []
        for name, scraper_instance in SCRAPER_REGISTRY.items():
            metrics = SCRAPER_METRICS.get(name, {})
            runs = metrics.get("runs", 0)
            failures = metrics.get("failures", 0)
            
            # Calculate dynamic success rate
            success_rate_val = (runs - failures) / runs if runs > 0 else 0
            success_rate_str = f"{int(success_rate_val * 100)}%"
            
            is_active = name in ACTIVE_SCRAPERS
            
            data = {
                "enabled": is_active,
                "core": True,
                "mode": "production",
                "cost": "free",
                "noise": "low",
                "categories": ["general"],
                "metrics": {
                    "leads_found": metrics.get("leads", 0),
                    "success_rate": success_rate_str,
                    "avg_speed": f"{metrics.get('avg_latency', 0.0):.2f}s",
                    "priority_score": round(metrics.get("priority_score", 0.0), 4),
                    "avg_confidence": round(metrics.get("avg_confidence", 0.0), 4),
                    "auto_disabled": metrics.get("auto_disabled", False)
                }
            }
            results.append((name, data))
        
        # Sort by priority score for live ranking visibility
        results.sort(key=lambda x: x[1]["metrics"]["priority_score"], reverse=True)
        
        return dict(results)
    except Exception as e:
        return {"error": f"Failed to list scrapers: {str(e)}", "registry_size": len(SCRAPER_REGISTRY)}

def get_detailed_status():
    """Detailed status for admin dashboard."""
    try:
        refresh_scraper_states()
        
        # Mapping for category check
        mapping = {
            "FacebookMarketplaceScraper": "facebook",
            "TwitterScraper": "twitter",
            "RedditScraper": "reddit",
            "GoogleMapsScraper": "google"
        }
        
        return {
            name: {
                "enabled": name in ACTIVE_SCRAPERS, 
                "core": True,
                "mode": "production",
                "cost": "free",
                "category": "vehicles" if is_scraper_allowed(mapping.get(name, "unknown")) else "other",
                "enabled_until": None,
                "ttl_remaining": None,
                "metrics": get_metrics(name)
            } for name, _ in SCRAPER_REGISTRY.items()
        }
    except Exception as e:
        return {"error": f"Failed to get scraper status: {str(e)}"}

def promote_scraper_to_prod(name: str, caller: str):
    """Promote a scraper from sandbox to production."""
    success, message = update_scraper_mode(name, "production", caller=caller)
    if not success:
        return {"status": "error", "message": message}
    return {"status": "success", "scraper": name, "mode": "production"}

def enable_scraper_service(name: str, ttl: Optional[int], caller: str):
    success, message = update_scraper_state(name, True, ttl_minutes=ttl, caller=caller)
    if not success:
        return {"status": "error", "message": message}
    return {"status": "success", "scraper": name, "enabled": True, "ttl": ttl}

def disable_scraper_service(name: str, caller: str):
    success, message = update_scraper_state(name, False, caller=caller)
    if not success:
        return {"status": "error", "message": message}
    return {"status": "disabled", "scraper": name}

def set_scraper_mode_service(name: str, mode: str, caller: str):
    success, message = update_scraper_mode(name, mode, caller=caller)
    if not success:
        return {"status": "error", "message": message}
    return {"status": "success", "scraper": name, "mode": mode}

def toggle_scraper_service(name: str, enabled: bool, caller: str):
    success, message = update_scraper_state(name, enabled, caller=caller)
    if not success:
        return {"status": "error", "message": message}
    return {"status": "success", "scraper": name, "enabled": enabled}

def get_all_metrics_service():
    return get_metrics()
