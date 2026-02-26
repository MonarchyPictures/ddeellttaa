from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.outreach_service import get_whatsapp_link_data, generate_outreach_message

router = APIRouter(prefix="/outreach", tags=["outreach"])

@router.get("/{lead_id}/whatsapp")
def open_whatsapp(lead_id: str, db: Session = Depends(get_db)):
    """Generates a WhatsApp link for a lead with a prefilled message."""
    result = get_whatsapp_link_data(lead_id, db)
    if "error" in result:
        # Soft failure
        return result
    return result

@router.post("/{lead_id}")
def outreach(lead_id: str, db: Session = Depends(get_db)):
    return generate_outreach_message(lead_id, db)
