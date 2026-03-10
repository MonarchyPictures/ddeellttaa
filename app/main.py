"""
Delta 9 - Main FastAPI Application
Production-ready deployment for Railway
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


# Get environment variables
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
PORT = int(os.getenv("PORT", "8000"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print(f"🚀 Starting Delta 9 in {ENVIRONMENT} mode on port {PORT}")
    yield
    # Shutdown
    print("👋 Shutting down Delta 9")


# Create FastAPI app
app = FastAPI(
    title="Delta 9",
    description="AI Buyer Discovery Engine",
    version="0.1.0",
    debug=DEBUG,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount assets only if directory exists (for Railway deployment)
if os.path.isdir("frontend/dist/assets"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
    print("✅ Mounted /assets from frontend/dist/assets")
else:
    print("⚠️  frontend/dist/assets not found - dashboard assets will not be served")


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the landing page"""
    return FileResponse("static/landing.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard UI"""
    if os.path.exists("frontend/dist/index.html"):
        return FileResponse("frontend/dist/index.html")
    # Fallback to landing page if dashboard not built
    return FileResponse("static/landing.html")


@app.get("/health")
def health():
    """Health check endpoint for Railway"""
    return {
        "status": "ok",
        "environment": ENVIRONMENT,
        "port": PORT,
    }


@app.get("/api/leads")
async def get_leads():
    """Get leads API endpoint"""
    return {
        "signals_scanned": 0,
        "buyers_found": 0,
        "leads": [],
    }


@app.get("/api/status")
async def get_status():
    """Get system status"""
    return {
        "status": "running",
        "environment": ENVIRONMENT,
        "version": "0.1.0",
        "features": {
            "dashboard": os.path.exists("frontend/dist/index.html"),
            "assets": os.path.isdir("frontend/dist/assets"),
        },
    }


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
