from fastapi import APIRouter, Query
from app.api.routes import notifications, websocket

api_router = APIRouter()

# Existing routes
api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["notifications"]
)

api_router.include_router(
    websocket.router,
    tags=["websocket"]
)

# =========================================================================
# 🔍 SEARCH ENDPOINT — This was MISSING
# =========================================================================
# If you already have this in another route file, ignore this section.
# But if your frontend calls /api/search and gets 404, THIS is why.

from app.services.search_service import search as search_service

@api_router.get("/search", tags=["search"])
async def search_leads(
    q: str = Query(..., min_length=3, description="Search query (e.g. 'tank', 'toyota prado')"),
    location: str = Query("Kenya", description="Location to search in")
):
    """
    Search for leads matching the query.
    Returns people who are actively looking to buy the searched item.
    """
    result = await search_service(q, location)
    return result


@api_router.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "ok",
        "service": "lead-scraper",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }

