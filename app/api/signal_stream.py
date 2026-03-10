"""
Signal Stream API Endpoints
Monitor and interact with the real-time signal pipeline
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.services.signal_stream import get_signal_stream, Signal

router = APIRouter(prefix="/api/stream", tags=["Signal Stream"])


@router.get("/recent")
async def get_recent_signals(
    channel: str = Query("raw", description="Stream channel"),
    count: int = Query(50, description="Number of signals to return"),
):
    """Get recent signals from the stream (for replay)"""
    stream = get_signal_stream()
    signals = stream.get_recent_signals(channel, count)
    
    return {
        "channel": channel,
        "count": len(signals),
        "signals": signals,
    }


@router.get("/stats")
async def get_stream_stats():
    """Get signal stream statistics"""
    stream = get_signal_stream()
    stats = stream.get_signal_stats()
    
    return stats


@router.post("/clear/{channel}")
async def clear_stream(channel: str):
    """Clear a signal stream channel"""
    stream = get_signal_stream()
    success = stream.clear_stream(channel)
    
    if success:
        return {"message": f"Stream '{channel}' cleared"}
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to clear stream"}
        )


@router.websocket("/ws")
async def websocket_signal_stream(websocket: WebSocket):
    """
    WebSocket endpoint for live signal streaming
    
    Clients receive real-time signals as they flow through the pipeline:
    - raw: All scraped signals
    - high_intent: Signals with buying intent
    - processed: After intent detection
    - leads: Converted to leads
    """
    await websocket.accept()
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "message": "Connected to Signal Stream",
        "channels": ["raw", "high_intent", "processed", "leads"],
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    stream = get_signal_stream()
    
    try:
        # Subscribe to all channels
        import asyncio
        
        async def subscribe_channel(channel: str):
            """Subscribe to a single channel"""
            async for signal_data in stream.subscribe(channel):
                await websocket.send_json({
                    "type": "signal",
                    "channel": channel,
                    "data": signal_data,
                    "timestamp": datetime.utcnow().isoformat(),
                })
        
        # Start subscriptions in background
        tasks = [
            asyncio.create_task(subscribe_channel("raw")),
            asyncio.create_task(subscribe_channel("high_intent")),
            asyncio.create_task(subscribe_channel("leads")),
        ]
        
        # Handle client messages
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                
                if message == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                elif message.startswith("filter:"):
                    # Client wants to filter by platform
                    platform = message[7:]
                    await websocket.send_json({
                        "type": "filter_set",
                        "platform": platform,
                    })
                    
            except asyncio.TimeoutError:
                continue
            
    except WebSocketDisconnect:
        # Cancel subscriptions
        for task in tasks:
            task.cancel()
        print("Signal Stream WebSocket disconnected")
    except Exception as e:
        print(f"Signal Stream WebSocket error: {e}")
        for task in tasks:
            task.cancel()


@router.get("/channels")
async def get_channels():
    """Get available signal stream channels"""
    stream = get_signal_stream()
    
    return {
        "channels": {
            "raw": {
                "description": "All raw signals from scrapers",
                "count": stream.get_signal_stats().get("channels", {}).get("raw", 0),
            },
            "high_intent": {
                "description": "Signals with intent_score >= 0.6",
                "count": stream.get_signal_stats().get("channels", {}).get("high_intent", 0),
            },
            "processed": {
                "description": "Signals after intent detection",
                "count": stream.get_signal_stats().get("channels", {}).get("processed", 0),
            },
            "leads": {
                "description": "Signals converted to leads",
                "count": stream.get_signal_stats().get("channels", {}).get("leads", 0),
            },
        }
    }
