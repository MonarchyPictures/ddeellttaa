from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
import uuid
from app.db.database import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse

router = APIRouter()


@router.get("/count")
def count_notifications(unread_only: bool = False, db: Session = Depends(get_db)):
    """Get count of notifications."""
    query = db.query(Notification)
    if unread_only:
        query = query.filter(Notification.read == False)
    return {"count": query.count()}

@router.get("/", response_model=List[NotificationResponse])
def list_notifications(db: Session = Depends(get_db)):
    try:
        return (
            db.query(Notification)
            .order_by(Notification.created_at.desc())
            .all()
        )
    except Exception as e:
        # Graceful fallback if table missing or DB error
        print(f"Notifications Error: {e}")
        return []


@router.post("/{notification_id}/read")
def mark_as_read(notification_id: str, db: Session = Depends(get_db)):
    try:
        notification_uuid = uuid.UUID(notification_id)
    except ValueError:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Invalid notification ID format"})

    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_uuid)
        .first()
    )

    if not notification:
        # Soft failure: if it's not found, maybe it was already deleted. Just say ok or error.
        return JSONResponse(status_code=200, content={"status": "error", "message": "Notification not found"})

    notification.read = True
    db.commit()

    return {"status": "ok"}


@router.delete("/")
def clear_all_notifications(db: Session = Depends(get_db)):
    db.query(Notification).delete(synchronize_session=False)
    db.commit()
    return {"status": "ok", "message": "All notifications cleared"}
