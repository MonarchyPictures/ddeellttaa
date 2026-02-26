from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import logging
import io

from app.db.database import get_db
from app.api.deps import verify_api_key
from app.services.lead_service import export_leads_generator, get_recent_events, get_leads

from pydantic import BaseModel

class ExportRequest(BaseModel):
    ids: List[str]

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
def list_leads(
    limit: int = 20,
    type: str = Query(None, description="Filter type: active, high_intent, whatsapp"),
    db: Session = Depends(get_db)
):
    """
    Get recent leads.
    """
    try:
        leads = get_leads(limit, type)
        return {"leads": leads, "count": len(leads)}
    except Exception as e:
        logger.error(f"Error fetching leads: {e}")
        return {"leads": [], "error": str(e)}

@router.get("/export", dependencies=[Depends(verify_api_key)])
async def export_leads_by_type(
    type: str = Query(..., pattern="^(active|high_intent|bootstrap)$"),
    format: str = Query("txt", pattern="^txt$"),
    db: Session = Depends(get_db)
):
    """Export leads by intelligence tier as a .txt file."""
    try:
        filename = f"delta9-{type}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.txt"
        
        return StreamingResponse(
            export_leads_generator(db, type),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        # Soft failure: Return a text file with the error
        error_content = f"Error generating export: {str(e)}"
        return StreamingResponse(
            io.BytesIO(error_content.encode('utf-8')),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=error_log.txt"}
        )

@router.get("/events", dependencies=[Depends(verify_api_key)])
def get_events(
    type: str = Query(..., pattern="^(whatsapp|all)$"),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Fetch tracked events (e.g. WhatsApp taps)."""
    try:
        events = get_recent_events(db, type, limit)
        return [
            {
                "id": e.id,
                "event": e.event_type,
                "lead_id": e.lead_id,
                "timestamp": e.timestamp.isoformat(),
                "metadata": e.extra_metadata
            }
            for e in events
        ]
    except Exception as e:
        logger.error(f"Failed to fetch events: {str(e)}")
        # Soft failure: Return empty list
        return []

@router.post("/leads/export", dependencies=[Depends(verify_api_key)])
def export_leads_post(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    # This was empty in the original file, just defined.
    # We can implement basic functionality or return not implemented.
    return {"message": "Export by IDs not implemented yet"}
