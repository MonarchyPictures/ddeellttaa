import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import FileResponse
import time

# Logging Setup
logging.basicConfig(level=logging.INFO)
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

# Import routers
from app.api.api import api_router
from app.api.routes import leads
from app.api.routes import scrapers
from app.api.routes import pipeline
from app.api.routes import outreach
from app.api.routes import admin

from app.api.routes import agents
from app.api.routes import core
from app.api.routes import notifications
from app.middleware.geoip import KenyaLockingMiddleware
from app.db.database import engine
from app.db.base_class import Base
from app.db import models

# Create database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Delta 9 API")

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

# Include API Router (v1)
app.include_router(api_router, prefix="/api/v1")

# Include notifications directly at /api/notifications to match frontend
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])

# Include other routers
app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
# app.include_router(search.router, prefix="/api/search", tags=["search"]) # Removed in favor of core.router
app.include_router(scrapers.router, prefix="/api/scrapers", tags=["scrapers"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(outreach.router, prefix="/api/outreach", tags=["outreach"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# Include agents and core
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(core.router, prefix="/api/core", tags=["core"])
# Compatibility: Frontend expects /api/search
app.include_router(core.router, prefix="/api", tags=["search_root"])

# ── TELEGRAM ROUTES ──────────────────────────────────
from app.api.routes import telegram as telegram_routes
app.include_router(
    telegram_routes.router,
    prefix="/api/telegram",
    tags=["telegram"]
)

# Legacy/Frontend compatibility: Expose core routes (like /success/stats) at root /api
# core.router is already mounted on /api above; avoid duplicate route registration

@app.get("/")
def read_root():
    """Serve the frontend UI."""
    frontend_index = os.path.join(frontend_dist_path, "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    return {"message": "Welcome to Delta 9 API", "status": "running", "frontend": "not built"}

@app.get("/api/ping")
def ping():
    """Simple ping endpoint for connectivity testing."""
    return {"status": "ok", "message": "pong"}

@app.get("/api-test")
def api_test_page():
    """Serve API test page for debugging."""
    test_page = os.path.join(frontend_dist_path, "api-test.html")
    if os.path.exists(test_page):
        return FileResponse(test_page)
    return {"error": "api-test.html not found. Build frontend first."}

@app.get("/health")
def health_check():
    """
    Production Health Check.
    Railway uses this to know if the app is alive.
    """
    db_ok = True
    scrapers_ok = True
    telegram_ok = True
    scraper_count = 0
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    try:
        from app.scrapers.registry import ACTIVE_SCRAPERS
        scraper_count = len(ACTIVE_SCRAPERS)
        scrapers_ok = scraper_count > 0
    except Exception:
        scrapers_ok = False
    try:
        from app.telegram.config import get_telegram_config_report
        report = get_telegram_config_report()
        require_telegram = os.environ.get("REQUIRE_TELEGRAM", "false").lower() == "true"
        telegram_ok = report["enabled"] if require_telegram else True
    except Exception:
        telegram_ok = False if os.environ.get("REQUIRE_TELEGRAM", "false").lower() == "true" else True

    healthy = db_ok and scrapers_ok and telegram_ok
    return {
        "status": "healthy" if healthy else "degraded",
        "service": "delta-9-api",
        "version": "1.0.0",
        "environment": os.environ.get("RAILWAY_ENVIRONMENT", "development"),
        "checks": {
            "database": "ok" if db_ok else "failed",
            "scrapers": "ok" if scrapers_ok else "failed",
            "telegram": "ok" if telegram_ok else "failed",
            "active_scrapers": scraper_count
        }
    }


# Startup event: Print all registered routes
@app.on_event("startup")
async def print_routes():
    """Print all registered routes at startup for debugging."""
    logger.info("=" * 60)
    logger.info("REGISTERED FASTAPI ROUTES:")
    logger.info("=" * 60)
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            methods = ",".join(route.methods)
            logger.info(f"  {methods} {route.path}")
    logger.info("=" * 60)


# SPA Catch-all: Serve index.html for any unmatched routes (client-side routing)
@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    """Serve frontend SPA for all unmatched routes."""
    # Don't interfere with API routes
    if full_path.startswith("api/") or full_path.startswith("assets/"):
        return {"detail": "Not Found"}
    
    frontend_index = os.path.join(frontend_dist_path, "index.html")
    if frontend_enabled and os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    
    return {"detail": "Not Found"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
