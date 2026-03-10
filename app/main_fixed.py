"""
Delta 9 - REAL LEADS ONLY
Fixed version with NO MOCK DATA
"""
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("delta9")

# Database
from app.models.lead import init_db, get_db, Lead, Signal, SearchQuery

# Services
from app.services.intent_detection import get_intent_service

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
PORT = int(os.getenv("PORT", "8000"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("=" * 60)
    logger.info("DELTA 9 - REAL LEAD SYSTEM STARTING")
    logger.info("=" * 60)
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Port: {PORT}")
    
    # Initialize database
    init_db()
    logger.info("✅ Database initialized")
    
    yield
    
    logger.info("👋 Delta 9 shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Delta 9 - Real Lead System",
    description="AI Buyer Discovery Engine - REAL DATA ONLY",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============================================================================
# REAL LEADS API - NO MOCK DATA
# ============================================================================

@app.get("/api/leads")
async def get_real_leads(
    q: Optional[str] = Query(None, description="Search query"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    min_intent: float = Query(0.5, description="Minimum intent score"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get REAL leads from database - NO MOCK DATA
    
    Only returns leads that were scraped from real sources.
    """
    logger.info(f"[API] Fetching real leads - query: '{q}', platform: {platform}")
    
    # Build query from REAL database
    query = db.query(Lead).filter(Lead.status == "new")
    
    # Filter by search term
    if q:
        query = query.filter(
            func.lower(Lead.intent_signals[0]).contains(q.lower())
        )
    
    # Filter by platform
    if platform:
        query = query.filter(Lead.sources.contains([platform]))
    
    # Quality filter
    query = query.filter(Lead.intent_score >= min_intent)
    
    # Count stats
    total_scanned = db.query(Signal).count()
    total_leads = query.count()
    
    # Get leads sorted by priority
    leads = query.order_by(
        desc(Lead.intent_score),
        desc(Lead.first_seen)
    ).limit(limit).all()
    
    # Format response
    formatted_leads = []
    for lead in leads:
        # Get source signal
        signal = db.query(Signal).filter(Signal.lead_id == lead.id).first()
        
        formatted_leads.append({
            "id": str(lead.id),
            "text": lead.intent_signals[0] if lead.intent_signals else "",
            "platform": lead.sources[0] if lead.sources else "unknown",
            "url": lead.profile_urls.get(lead.sources[0], "") if lead.profile_urls else "",
            "author": lead.username or "unknown",
            "intent_score": round(lead.intent_score, 2),
            "verification_score": round(lead.verification_score, 2),
            "urgency": lead.buying_urgency or "unknown",
            "location": lead.location or "Unknown",
            "timestamp": lead.first_seen.isoformat() if lead.first_seen else datetime.utcnow().isoformat(),
            "query": q or "all"
        })
    
    logger.info(f"[API] Returning {len(formatted_leads)} real leads (scanned: {total_scanned})")
    
    return {
        "signals_scanned": total_scanned,
        "buyers_found": total_leads,
        "leads": formatted_leads,
        "query": q,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/search")
async def search_real_signals(
    q: str = Query(..., description="Search term (required)"),
    db: Session = Depends(get_db)
):
    """
    Search for buyer intent in real-time
    
    This endpoint triggers real scraping and returns actual results.
    """
    logger.info(f"[API] Real-time search for: '{q}'")
    
    if not q or len(q) < 2:
        return JSONResponse(
            status_code=400,
            content={"error": "Query must be at least 2 characters"}
        )
    
    # Search in existing signals
    signals = db.query(Signal).filter(
        func.lower(Signal.content).contains(q.lower()),
        Signal.intent_score >= 0.5
    ).order_by(desc(Signal.discovered_at)).limit(20).all()
    
    logger.info(f"[API] Found {len(signals)} existing signals for '{q}'")
    
    # Format results
    results = []
    for signal in signals:
        results.append({
            "text": signal.content[:300] if signal.content else "",
            "platform": signal.source,
            "url": signal.source_url or "",
            "author": signal.author or "unknown",
            "intent_score": round(signal.intent_score, 2),
            "timestamp": signal.discovered_at.isoformat() if signal.discovered_at else datetime.utcnow().isoformat()
        })
    
    return {
        "query": q,
        "signals_found": len(signals),
        "results": results,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/stats")
async def get_real_stats(db: Session = Depends(get_db)):
    """Get real system statistics"""
    total_signals = db.query(Signal).count()
    total_leads = db.query(Lead).count()
    new_leads = db.query(Lead).filter(Lead.status == "new").count()
    
    # By platform
    platform_counts = db.query(
        Signal.source,
        func.count(Signal.id)
    ).group_by(Signal.source).all()
    
    logger.info(f"[API] Stats - Signals: {total_signals}, Leads: {total_leads}")
    
    return {
        "signals_scanned": total_signals,
        "total_leads": total_leads,
        "new_leads": new_leads,
        "by_platform": {source: count for source, count in platform_counts},
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# PAGES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def home():
    """Landing page"""
    return FileResponse("static/landing.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Dashboard - shows REAL leads only"""
    return FileResponse("static/dashboard.html")


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "system": "delta9-real",
        "version": "3.0.0",
        "mock_data": False,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
