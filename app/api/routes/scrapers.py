from fastapi import APIRouter, Depends, Request, Query
from app.middleware.auth import require_admin
from app.services.scraper_management_service import (
    list_all_scrapers, 
    get_detailed_status, 
    promote_scraper_to_prod, 
    enable_scraper_service,
    disable_scraper_service,
    set_scraper_mode_service,
    toggle_scraper_service,
    get_all_metrics_service
)
from typing import Optional

router = APIRouter(tags=["Scrapers"]) 

# Removed legacy verify_admin

@router.get("/") 
def list_scrapers(): 
    """List all scrapers with their current configuration and metrics."""
    return list_all_scrapers()

@router.get("/status")
def get_scraper_status(request: Request, role: str = Depends(require_admin)):
    """Detailed status for admin dashboard."""
    return get_detailed_status()

@router.post("/{name}/promote")
def promote_scraper(request: Request, name: str, role: str = Depends(require_admin)):
    """Promote a scraper from sandbox to production."""
    return promote_scraper_to_prod(name, caller=f"User({role})")

@router.post("/{name}/enable") 
def enable_scraper(
    request: Request,
    name: str, 
    ttl: Optional[int] = Query(None, description="TTL in minutes"),
    role: str = Depends(require_admin)
): 
    return enable_scraper_service(name, ttl, caller=f"User({role})")

@router.post("/{name}/disable") 
def disable_scraper(request: Request, name: str, role: str = Depends(require_admin)): 
    return disable_scraper_service(name, caller=f"User({role})")

@router.post("/{name}/mode")
def set_scraper_mode(request: Request, name: str, mode: str, role: str = Depends(require_admin)):
    """Update scraper mode (production/sandbox)."""
    return set_scraper_mode_service(name, mode, caller=f"User({role})")

@router.post("/toggle")
def toggle_scraper_generic(request: Request, name: str, enabled: bool, role: str = Depends(require_admin)):
    """
    🔐 Standardized toggle endpoint.
    Snippet requested: Use on /scrapers/toggle
    """
    return toggle_scraper_service(name, enabled, caller=f"User({role})")

@router.get("/metrics")
def get_all_metrics(request: Request, role: str = Depends(require_admin)):
    return get_all_metrics_service()

@router.get("/health") 
def scraper_health(): 
    return {"status": "ok", "message": "Scraper health check endpoint is active"}
