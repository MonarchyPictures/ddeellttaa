# DEBUG BUILD: 2026-02-28T01:00:00Z - CACHE_BUSTER_V4
import logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("delta9")
_logger.info("="*60)
_logger.info("MAIN.PY LOADED - VERSION 2026-02-28-V3-ANTI429")
_logger.info("RAILWAY DEPLOY: Anti-429 hardened, Fast/Deep mode")
_logger.info("="*60)

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import FileResponse
import time

# Logging Setup
logger = logging.getLogger("delta9")

# Sentry Setup (Optional but Elite)
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

# Import routers - ONLY search.router for search endpoint
from app.api.routes import scrapers
from app.api.routes import pipeline
from app.api.routes import outreach
from app.api.routes import admin
from app.api.routes import agents
from app.api.routes import notifications
from app.api.routes import search  # Unified search endpoint

from app.middleware.geoip import KenyaLockingMiddleware
from app.db.init_db import init_db

app = FastAPI(title="Delta 9 API")


@app.on_event("startup")
async def startup():
    """Initialize database tables on application startup."""
    init_db()

# Mount static files (frontend build)
frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
frontend_enabled = os.path.exists(frontend_dist_path)

if frontend_enabled:
    # Mount all static files from dist
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")
    logger.info(f"Frontend static files mounted from: {frontend_dist_path}")

# Elite Engineering: Middleware
app.add_middleware(KenyaLockingMiddleware)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # DEBUG: Log every request
    logger.info(f"[REQUEST] {request.method} {request.url.path}")
    
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Simple Logging for Observability
    logger.info(f"[RESPONSE] {request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# CORS - Allow all origins for API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when using wildcard
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ============================================================
# ROUTER MOUNTS - CLEAN ARCHITECTURE
# ============================================================
# ONE search endpoint: POST /api/search
# ONE pipeline: Kenya High Recall Pipeline
# ONE scoring system: Weighted Kenya-optimized model

app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(scrapers.router, prefix="/api/scrapers", tags=["scrapers"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(outreach.router, prefix="/api/outreach", tags=["outreach"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])

# Telegram routes
from app.api.routes import telegram as telegram_routes
app.include_router(
    telegram_routes.router,
    prefix="/api/telegram",
    tags=["telegram"]
)

@app.get("/")
def read_root():
    """Serve the frontend UI."""
    frontend_index = os.path.join(frontend_dist_path, "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    return {"message": "Welcome to Delta 9 API", "status": "running", "frontend": "not built"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "delta-9",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }


@app.get("/api-test")
def api_test():
    """Quick API test endpoint."""
    return {
        "status": "ok",
        "message": "API is running",
        "search_endpoint": "POST /api/search",
        "docs": "/docs"
    }
