# app/api/routes/telegram.py
# ============================================================
# TELEGRAM API ROUTES
# ============================================================

import logging
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional

from app.telegram.service import TELEGRAM_SERVICE
from app.telegram.notifier import BUYER_NOTIFIER
from app.telegram.config import get_telegram_config_report

logger = logging.getLogger(__name__)
router = APIRouter()


class TelegramSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    hours_back: Optional[int] = 24
    max_groups: Optional[int] = 15


@router.get("/status")
async def telegram_status():
    """Check Telegram monitor status."""
    cfg = get_telegram_config_report()
    return {
        "available": TELEGRAM_SERVICE.is_available,
        "config": cfg,
        "stats": TELEGRAM_SERVICE.get_stats()
    }


@router.post("/search")
async def telegram_search(request: TelegramSearchRequest):
    """
    Search Telegram groups for buyers.
    
    POST /api/telegram/search
    Body: {"query": "2br kileleshwa", "hours_back": 24}
    """
    if not TELEGRAM_SERVICE.is_available:
        return {
            "results": [], "leads": [],
            "message": "Telegram not configured. Add credentials to .env",
            "count": 0,
            "status": "not_configured"
        }

    leads = await TELEGRAM_SERVICE.search_buyers(
        query=request.query,
        category=request.category,
        hours_back=request.hours_back,
        max_groups=request.max_groups
    )

    return {
        "results": leads,
        "leads": leads,
        "count": len(leads),
        "message": f"Found {len(leads)} buyers on Telegram",
        "status": "success" if leads else "no_results",
        "stats": TELEGRAM_SERVICE.get_stats()
    }


@router.post("/monitor/start")
async def start_monitor(
    query: str = Query(None),
    category: str = Query(None)
):
    """Start real-time Telegram monitoring (background task)."""
    if not TELEGRAM_SERVICE.is_available:
        return {"error": "Telegram not configured", "status": "not_configured"}

    import asyncio
    # Start monitoring in background
    asyncio.create_task(
        TELEGRAM_SERVICE.start_monitoring(query=query, category=category)
    )

    return {
        "message": "Real-time monitoring started",
        "status": "monitoring",
        "query": query,
        "category": category
    }


@router.post("/monitor/stop")
async def stop_monitor():
    """Stop real-time monitoring."""
    await TELEGRAM_SERVICE.stop_monitoring()
    return {"message": "Monitoring stopped", "status": "stopped"}


@router.get("/groups")
async def list_groups(category: str = Query(None)):
    """List available Telegram groups by category."""
    from app.telegram.config import KENYAN_GROUPS

    if category:
        groups = KENYAN_GROUPS.get(category, [])
        return {"category": category, "groups": groups, "count": len(groups)}

    return {
        "categories": {
            cat: {"count": len(groups), "groups": groups}
            for cat, groups in KENYAN_GROUPS.items()
        }
    }


@router.post("/groups/discover")
async def discover_groups(query: str = Query(...)):
    """Discover new Telegram groups for a query."""
    discovered = await TELEGRAM_SERVICE.group_manager.discover_new_groups(query)
    return {
        "query": query,
        "discovered": discovered,
        "count": len(discovered)
    }


@router.websocket("/ws")
async def telegram_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time buyer notifications.
    
    Connect: ws://localhost:8000/api/telegram/ws
    Receives: {"type": "new_buyer", "data": {...lead...}}
    """
    await websocket.accept()
    BUYER_NOTIFIER.register_websocket(websocket)

    logger.info("WebSocket client connected for Telegram notifications")

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Could handle commands here (e.g., "start", "stop", "filter")

    except WebSocketDisconnect:
        BUYER_NOTIFIER.unregister_websocket(websocket)
        logger.info("WebSocket client disconnected")
