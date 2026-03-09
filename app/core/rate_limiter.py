"""
Rate limiting configuration and utilities.

Provides rate limiting for API endpoints using SlowAPI.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def get_limiter() -> Limiter:
    """
    Create and configure the rate limiter.
    
    Returns:
        Configured Limiter instance
    """
    if not settings.RATE_LIMIT_ENABLED:
        # Return a no-op limiter when disabled
        return Limiter(
            key_func=get_remote_address,
            enabled=False,
        )
    
    return Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.RATE_LIMIT_REQUESTS} per {settings.RATE_LIMIT_WINDOW} seconds"],
    )


# Global limiter instance
limiter = get_limiter()


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    
    Args:
        request: The incoming request
        exc: The rate limit exceeded exception
        
    Returns:
        JSON response with 429 status code
    """
    logger.warning(
        "Rate limit exceeded",
        client_ip=get_remote_address(request),
        path=request.url.path,
    )
    return _rate_limit_exceeded_handler(request, exc)


# Decorator for specific rate limits
def rate_limit(limit: str):
    """
    Decorator to apply a specific rate limit to an endpoint.
    
    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")
        
    Example:
        @app.get("/search")
        @rate_limit("30/minute")
        def search():
            pass
    """
    return limiter.limit(limit)
