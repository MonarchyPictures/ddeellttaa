from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio

router = APIRouter()

# Connected clients
active_connections = []

@router.websocket("/ws/leads")
async def websocket_leads(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_new_lead(lead_data: dict):
    """Call this from search_service when new leads arrive."""
    # Create a copy of the list to iterate over safely
    connections = active_connections.copy()
    for connection in connections:
        try:
            await connection.send_json({"type": "new_lead", "data": lead_data})
        except:
            if connection in active_connections:
                active_connections.remove(connection)
