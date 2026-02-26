import logging
import uuid
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.notification import Notification

logger = logging.getLogger(__name__)

def notify_new_leads(agent_name: str, leads: list, agent_id=None):
    """
    Creates a notification for new leads found by an agent.
    If agent_id is provided, links it. Otherwise logs warning.
    """
    if not leads:
        return

    count = len(leads)
    logger.info(f"🔔 NOTIFY: Agent '{agent_name}' found {count} new leads.")

    db = SessionLocal()
    try:
        # Create notification record
        # Note: Ideally we should link to agent_id if available
        # The user snippet only passed agent.name, but we can update call site to pass ID or object
        
        notification = Notification(
            agent_id=agent_id,
            message=f"{count} new leads from {agent_name}",
            lead_count=count,
            read=False
        )
        db.add(notification)
        db.commit()
        db.refresh(notification) # Get ID
        logger.info(f"✅ Notification saved: {notification.id}")
        
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
    finally:
        db.close()
