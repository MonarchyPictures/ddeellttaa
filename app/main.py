"""
Delta 9 - AI Buyer Discovery Engine
Complete API with Live Lead Feed
Production-ready for Railway
"""

import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import models
from .models.lead import init_db, get_db, Lead, Signal, SearchQuery, SessionLocal

# Import services
from .services.query_expansion import get_expansion_service
from .services.intent_detection import get_intent_service
from .services.lead_verification import get_verification_service

# Import scrapers
from .scrapers.scraper_manager import get_scraper_manager

# Environment variables
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
PORT = int(os.getenv("PORT", "8000"))

# Live feed connection manager
class ConnectionManager:
    """Manages WebSocket connections for live lead feed"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

# Global connection manager
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print(f"🚀 Delta 9 Starting...")
    print(f"   Environment: {ENVIRONMENT}")
    print(f"   Port: {PORT}")
    
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("👋 Delta 9 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Delta 9",
    description="AI Buyer Discovery Engine - Real-time Lead Generation",
    version="1.0.0",
    debug=DEBUG,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount assets only if directory exists
if os.path.isdir("frontend/dist/assets"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
    print("✅ Mounted /assets")


# ============================================================================
# PUBLIC PAGES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the landing page"""
    return FileResponse("static/landing.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard UI"""
    if os.path.exists("frontend/dist/index.html"):
        return FileResponse("frontend/dist/index.html")
    return FileResponse("static/landing.html")


# ============================================================================
# HEALTH & STATUS
# ============================================================================

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "delta-9",
        "version": "1.0.0",
        "environment": ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/status")
async def get_status():
    """Get system status"""
    return {
        "status": "running",
        "environment": ENVIRONMENT,
        "version": "1.0.0",
        "features": {
            "dashboard": os.path.exists("frontend/dist/index.html"),
            "assets": os.path.isdir("frontend/dist/assets"),
            "live_feed": True,
            "scrapers": ["reddit", "twitter", "forum"],
        },
        "stats": {
            "active_websocket_connections": len(manager.active_connections),
        }
    }


# ============================================================================
# QUERY EXPANSION
# ============================================================================

@app.get("/api/expand")
async def expand_query(
    q: str = Query(..., description="Search query to expand"),
    category: str = Query("general", description="Industry category"),
):
    """
    Expand a query into buyer-intent search phrases
    
    Example: "plumber" -> ["need plumber", "looking for plumber", ...]
    """
    service = get_expansion_service()
    phrases = service.expand(q, category)
    
    return {
        "original": q,
        "category": category,
        "expanded_count": len(phrases),
        "phrases": phrases[:20],  # Return top 20
    }


# ============================================================================
# SEARCH & SCRAPING
# ============================================================================

@app.post("/api/search")
async def search_leads(
    background_tasks: BackgroundTasks,
    query: str,
    expand: bool = True,
    max_results: int = 10,
):
    """
    Search all sources for leads matching the query
    
    This triggers scrapers across Reddit, Twitter, and Forums
    """
    scraper = get_scraper_manager()
    
    try:
        results = await scraper.search_all(
            query=query,
            expand=expand,
            max_results_per_source=max_results
        )
        
        # Broadcast new signals to live feed
        for signal in results.get("signals", [])[:5]:
            await manager.broadcast({
                "type": "signal",
                "data": signal,
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        # Broadcast new leads
        for lead in results.get("leads", [])[:3]:
            await manager.broadcast({
                "type": "lead",
                "data": lead,
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        return results
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/search")
async def search_get(
    q: str = Query(..., description="Search query"),
    expand: bool = Query(True, description="Expand query into buyer-intent phrases"),
    limit: int = Query(10, description="Max results per source"),
):
    """GET version of search for easy testing"""
    scraper = get_scraper_manager()
    
    try:
        results = await scraper.search_all(
            query=q,
            expand=expand,
            max_results_per_source=limit
        )
        return results
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ============================================================================
# LEADS API
# ============================================================================

@app.get("/api/leads")
async def get_leads(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    source: Optional[str] = None,
    min_score: float = 0.0,
    limit: int = 50,
    offset: int = 0,
):
    """Get leads with filtering"""
    query = db.query(Lead)
    
    if status:
        query = query.filter(Lead.status == status)
    if source:
        query = query.filter(Lead.sources.contains([source]))
    if min_score > 0:
        query = query.filter(Lead.priority_score >= min_score)
    
    leads = query.order_by(Lead.priority_score.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": query.count(),
        "leads": [
            {
                "id": l.id,
                "username": l.username,
                "email": l.email,
                "phone": l.phone,
                "location": l.location,
                "intent_score": l.intent_score,
                "priority_score": l.priority_score,
                "status": l.status,
                "sources": l.sources,
                "first_seen": l.first_seen.isoformat() if l.first_seen else None,
            }
            for l in leads
        ]
    }


@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get a single lead by ID"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    
    if not lead:
        return JSONResponse(status_code=404, content={"error": "Lead not found"})
    
    return {
        "id": lead.id,
        "username": lead.username,
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "company": lead.company,
        "location": lead.location,
        "country": lead.country,
        "intent_score": lead.intent_score,
        "intent_category": lead.intent_category,
        "buying_urgency": lead.buying_urgency,
        "verification_score": lead.verification_score,
        "priority_score": lead.priority_score,
        "profile_urls": lead.profile_urls,
        "intent_signals": lead.intent_signals,
        "sources": lead.sources,
        "status": lead.status,
        "notes": lead.notes,
        "tags": lead.tags,
        "first_seen": lead.first_seen.isoformat() if lead.first_seen else None,
        "last_active": lead.last_active.isoformat() if lead.last_active else None,
    }


@app.patch("/api/leads/{lead_id}")
async def update_lead(
    lead_id: int,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Update a lead's status or notes"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    
    if not lead:
        return JSONResponse(status_code=404, content={"error": "Lead not found"})
    
    if status:
        lead.status = status
    if notes:
        lead.notes = notes
    
    db.commit()
    
    return {"message": "Lead updated", "id": lead_id}


# ============================================================================
# SIGNALS API
# ============================================================================

@app.get("/api/signals")
async def get_signals(
    db: Session = Depends(get_db),
    source: Optional[str] = None,
    is_lead: Optional[bool] = None,
    min_intent: float = 0.0,
    limit: int = 50,
):
    """Get raw signals with filtering"""
    query = db.query(Signal)
    
    if source:
        query = query.filter(Signal.source == source)
    if is_lead is not None:
        query = query.filter(Signal.is_lead == is_lead)
    if min_intent > 0:
        query = query.filter(Signal.intent_score >= min_intent)
    
    signals = query.order_by(Signal.discovered_at.desc()).limit(limit).all()
    
    return {
        "signals": [
            {
                "id": s.id,
                "source": s.source,
                "title": s.title,
                "content": s.content[:200] if s.content else None,
                "author": s.author,
                "intent_score": s.intent_score,
                "is_lead": s.is_lead,
                "discovered_at": s.discovered_at.isoformat() if s.discovered_at else None,
            }
            for s in signals
        ]
    }


# ============================================================================
# LIVE FEED WEBSOCKET
# ============================================================================

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    WebSocket endpoint for live lead feed
    
    Connect to this endpoint to receive real-time:
    - New signals from scrapers
    - Verified leads
    - System updates
    """
    await manager.connect(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Delta 9 Live Feed",
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        while True:
            # Wait for client messages (ping/keepalive)
            data = await websocket.receive_text()
            
            # Handle ping
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat(),
                })
            
            # Handle search requests from client
            elif data.startswith("search:"):
                query = data[7:]  # Remove "search:" prefix
                await websocket.send_json({
                    "type": "search_started",
                    "query": query,
                })
                
                # Run search and broadcast results
                scraper = get_scraper_manager()
                results = await scraper.search_all(query, expand=True, max_results_per_source=5)
                
                await websocket.send_json({
                    "type": "search_complete",
                    "query": query,
                    "results": {
                        "signals_found": results.get("total_signals", 0),
                        "leads_found": results.get("leads_found", 0),
                    }
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============================================================================
# STATS & ANALYTICS
# ============================================================================

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    return {
        "leads": {
            "total": db.query(Lead).count(),
            "new": db.query(Lead).filter(Lead.status == "new").count(),
            "contacted": db.query(Lead).filter(Lead.status == "contacted").count(),
            "converted": db.query(Lead).filter(Lead.status == "converted").count(),
        },
        "signals": {
            "total": db.query(Signal).count(),
            "today": db.query(Signal).filter(
                Signal.discovered_at >= datetime.utcnow().replace(hour=0, minute=0)
            ).count(),
        },
        "sources": {
            "reddit": db.query(Signal).filter(Signal.source == "reddit").count(),
            "twitter": db.query(Signal).filter(Signal.source == "twitter").count(),
            "forum": db.query(Signal).filter(Signal.source == "forum").count(),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if DEBUG else "An error occurred",
        },
    )


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def periodic_search_task():
    """Background task to periodically search for leads"""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            print("Running periodic search...")
            # Add periodic searches here
        except Exception as e:
            print(f"Periodic search error: {e}")


# Start background tasks on startup
@app.on_event("startup")
async def start_background_tasks():
    """Start background tasks"""
    # asyncio.create_task(periodic_search_task())
    pass
