"""
Delta 9 - AI Buyer Discovery Engine
Distributed Scraper Workers with Celery + Redis
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
from celery import chain, group, chord

# Database
from app.models.lead import init_db, get_db, Lead, Signal, SearchQuery, SessionLocal

# Services
from app.services.query_expansion import get_expansion_service
from app.services.intent_detection import get_intent_service
from app.services.lead_verification import get_verification_service

# Scraper Manager (for sync operations)
from app.scrapers.scraper_manager import get_scraper_manager

# Celery Tasks (for distributed operations)
from app.tasks.scraper_tasks import (
    scrape_reddit,
    scrape_twitter,
    scrape_forum,
    scrape_all_sources,
    process_signal,
    search_and_process,
)
from app.tasks.lead_tasks import (
    create_lead_from_signals,
    verify_lead,
    enrich_lead_data,
    process_unprocessed_signals,
)

# Celery App
from app.core.celery_config import celery_app, check_celery_health

# Worker Manager
from app.workers.worker_manager import get_worker_manager

# Signal Stream
from app.services.signal_stream import get_signal_stream, get_signal_producer
from app.api.signal_stream import router as signal_stream_router

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
        
        for conn in disconnected:
            self.disconnect(conn)

# Global connection manager
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    print(f"🚀 Delta 9 Starting...")
    print(f"   Environment: {ENVIRONMENT}")
    print(f"   Port: {PORT}")
    
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    # Check Celery/Redis connection
    health = check_celery_health()
    if health["status"] == "ok":
        print("✅ Celery/Redis connected")
    else:
        print(f"⚠️  Celery/Redis: {health.get('message', 'not connected')}")
    
    yield
    
    print("👋 Delta 9 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Delta 9",
    description="AI Buyer Discovery Engine - Distributed Scraper Workers",
    version="2.0.0",
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

if os.path.isdir("frontend/dist/assets"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
    print("✅ Mounted /assets")

# Include Signal Stream API routes
app.include_router(signal_stream_router)


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
    celery_health = check_celery_health()
    
    return {
        "status": "ok",
        "service": "delta-9",
        "version": "2.0.0",
        "environment": ENVIRONMENT,
        "celery": celery_health,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/status")
async def get_status():
    """Get system status"""
    worker_manager = get_worker_manager()
    worker_stats = worker_manager.get_worker_stats()
    
    return {
        "status": "running",
        "environment": ENVIRONMENT,
        "version": "2.0.0",
        "features": {
            "dashboard": os.path.exists("frontend/dist/index.html"),
            "assets": os.path.isdir("frontend/dist/assets"),
            "live_feed": True,
            "distributed_workers": True,
            "scrapers": ["reddit", "twitter", "forum"],
        },
        "workers": worker_stats,
        "websocket_connections": len(manager.active_connections),
    }


# ============================================================================
# QUERY EXPANSION
# ============================================================================

@app.get("/api/expand")
async def expand_query(
    q: str = Query(..., description="Search query to expand"),
    category: str = Query("general", description="Industry category"),
):
    """Expand a query into buyer-intent search phrases"""
    service = get_expansion_service()
    phrases = service.expand(q, category)
    
    return {
        "original": q,
        "category": category,
        "expanded_count": len(phrases),
        "phrases": phrases[:20],
    }


# ============================================================================
# DISTRIBUTED SEARCH API (Celery Tasks)
# ============================================================================

@app.post("/api/search/async")
async def search_async(
    query: str,
    expand: bool = True,
    background_tasks: BackgroundTasks = None,
):
    """
    Launch distributed search across all scrapers
    
    Uses Celery to run scrapers in parallel across worker nodes.
    Returns task IDs for polling status.
    """
    print(f"[API] Launching async search for: {query}")
    
    # Launch the Celery task
    task = search_and_process.delay(query, expand)
    
    return {
        "workflow": "distributed_search",
        "query": query,
        "task_id": task.id,
        "status": "queued",
        "poll_url": f"/api/tasks/{task.id}/status",
    }


@app.get("/api/search/async")
async def search_async_get(
    q: str = Query(..., description="Search query"),
    expand: bool = Query(True, description="Expand query"),
):
    """GET version of async search"""
    task = search_and_process.delay(q, expand)
    
    return {
        "workflow": "distributed_search",
        "query": q,
        "task_id": task.id,
        "status": "queued",
        "poll_url": f"/api/tasks/{task.id}/status",
    }


@app.post("/api/search/source/{source}")
async def search_single_source(
    source: str,  # reddit, twitter, forum
    query: str,
):
    """Search a single source using a Celery worker"""
    
    task_mapping = {
        "reddit": scrape_reddit,
        "twitter": scrape_twitter,
        "forum": scrape_forum,
    }
    
    if source not in task_mapping:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown source: {source}. Use: {list(task_mapping.keys())}"}
        )
    
    # Launch task
    task = task_mapping[source].delay(query)
    
    return {
        "source": source,
        "query": query,
        "task_id": task.id,
        "status": "queued",
        "poll_url": f"/api/tasks/{task.id}/status",
    }


# ============================================================================
# SYNC SEARCH (Direct - for quick testing)
# ============================================================================

@app.get("/api/search")
async def search_sync(
    q: str = Query(..., description="Search query"),
    expand: bool = Query(True, description="Expand query"),
    limit: int = Query(10, description="Max results per source"),
):
    """
    Synchronous search (runs directly, not distributed)
    
    Use /api/search/async for distributed processing.
    """
    scraper = get_scraper_manager()
    
    try:
        results = await scraper.search_all(
            query=q,
            expand=expand,
            max_results_per_source=limit
        )
        
        # Broadcast to live feed
        for signal in results.get("signals", [])[:5]:
            await manager.broadcast({
                "type": "signal",
                "data": signal,
                "timestamp": datetime.utcnow().isoformat(),
            })
        
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


# ============================================================================
# TASK MONITORING API
# ============================================================================

@app.get("/api/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """Get the status of a Celery task"""
    worker_manager = get_worker_manager()
    return worker_manager.get_task_status(task_id)


@app.get("/api/tasks/bulk-status")
async def get_bulk_task_status(task_ids: List[str] = Query(...)):
    """Get status for multiple tasks at once"""
    worker_manager = get_worker_manager()
    return {
        "tasks": [worker_manager.get_task_status(tid) for tid in task_ids]
    }


@app.get("/api/workers/status")
async def get_workers_status():
    """Get Celery worker status"""
    worker_manager = get_worker_manager()
    return worker_manager.get_worker_stats()


@app.get("/api/workers/ping")
async def ping_workers():
    """Ping all workers to check connectivity"""
    worker_manager = get_worker_manager()
    return worker_manager.broadcast_ping()


@app.get("/api/queues/status")
async def get_queue_status():
    """Get task queue lengths"""
    worker_manager = get_worker_manager()
    return worker_manager.get_queue_lengths()


@app.post("/api/tasks/{task_id}/revoke")
async def revoke_task(task_id: str, terminate: bool = False):
    """Revoke/cancel a running task"""
    worker_manager = get_worker_manager()
    return worker_manager.revoke_task(task_id, terminate)


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


@app.post("/api/leads/{lead_id}/verify")
async def verify_lead_async(lead_id: int):
    """Launch async lead verification task"""
    task = verify_lead.delay(lead_id)
    
    return {
        "lead_id": lead_id,
        "task_id": task.id,
        "status": "queued",
        "poll_url": f"/api/tasks/{task.id}/status",
    }


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


@app.post("/api/signals/{signal_id}/process")
async def process_signal_async(signal_id: int):
    """Launch async signal processing task"""
    task = process_signal.delay(signal_id)
    
    return {
        "signal_id": signal_id,
        "task_id": task.id,
        "status": "queued",
        "poll_url": f"/api/tasks/{task.id}/status",
    }


# ============================================================================
# LIVE FEED WEBSOCKET
# ============================================================================

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """WebSocket endpoint for live lead feed"""
    await manager.connect(websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Delta 9 Live Feed",
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        while True:
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat(),
                })
            elif data.startswith("search:"):
                query = data[7:]
                await websocket.send_json({
                    "type": "search_started",
                    "query": query,
                })
                
                # Launch async search
                task = search_and_process.delay(query)
                
                await websocket.send_json({
                    "type": "search_queued",
                    "query": query,
                    "task_id": task.id,
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
    # Get queue status
    worker_manager = get_worker_manager()
    queues = worker_manager.get_queue_lengths()
    
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
        "queues": queues,
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
