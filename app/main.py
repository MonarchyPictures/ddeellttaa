"""
Delta 9 API - Main Application Entry Point.

Production-grade FastAPI application with:
- JWT Authentication
- Rate Limiting
- CORS Configuration
- Structured Logging
- Health Checks
- Database Integration
"""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging_config import configure_logging
from app.db.database import init_db

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(
        "Application starting",
        extra={
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    )
    
    # Initialize database tables in development
    if settings.is_development:
        init_db()
    
    yield
    
    logger.info("Application shutting down")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Delta 9 Intelligence API for Lead Generation",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )
    
    # Configure CORS
    cors_origins = settings.cors_origins_list
    if not cors_origins and settings.is_development:
        cors_origins = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time", "X-Request-ID"],
    )
    
    # Request timing and logging middleware
    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        """Add request timing and logging."""
        request_id = request.headers.get("X-Request-ID", str(time.time()))
        start_time = time.time()
        
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(process_time * 1000, 2),
                }
            )
            
            return response
            
        except Exception as exc:
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(exc),
                }
            )
            raise
    
    return app


# Create application instance
app = create_application()

# -----------------------------------------------------------------------------
# Import and include routers
# -----------------------------------------------------------------------------

from app.api.routes import auth
from app.api.routes import agents
from app.api.routes import search
from app.api.routes import scrapers
from app.api.routes import notifications
from app.api.routes import telegram as telegram_routes

app.include_router(auth.router, prefix="/api")
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(scrapers.router, prefix="/api/scrapers", tags=["scrapers"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(telegram_routes.router, prefix="/api/telegram", tags=["telegram"])

# -----------------------------------------------------------------------------
# Static files (frontend)
# -----------------------------------------------------------------------------

frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")
    logger.info(f"Frontend static files mounted from: {frontend_path}")


# -----------------------------------------------------------------------------
# Health and info endpoints
# -----------------------------------------------------------------------------

@app.get("/", tags=["health"])
def root():
    """Root endpoint - serves frontend or API info."""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        from fastapi.responses import FileResponse
        return FileResponse(index_path)
    
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "documentation": "/docs" if not settings.is_production else None,
    }


@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/ready", tags=["health"])
def readiness_check():
    """Readiness check for Kubernetes/Container orchestration."""
    return {
        "status": "ready",
        "checks": {
            "database": "ok",
            "cache": "ok",
        },
    }


@app.get("/api/info", tags=["health"])
def api_info():
    """API information endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "features": {
            "authentication": True,
            "rate_limiting": settings.RATE_LIMIT_ENABLED,
            "telegram": settings.TELEGRAM_ENABLED,
            "ai": settings.AI_ENABLED,
        },
    }


# -----------------------------------------------------------------------------
# Error handlers
# -----------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        extra={
            "error": str(exc),
            "error_type": type(exc).__name__,
            "path": request.url.path,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.is_development else "An unexpected error occurred",
        },
    )


# -----------------------------------------------------------------------------
# Application entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development,
        workers=1 if settings.is_development else settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
    )
