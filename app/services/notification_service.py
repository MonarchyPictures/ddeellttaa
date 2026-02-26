from app.models.notification import Notification
import logging

logger = logging.getLogger(__name__)

def create_notification(db, agent, lead_count):
    """
    Creates a persistent notification record in the database.
    This is useful for in-app notification centers or history.
    """
    if lead_count == 0:
        return

    notification = Notification(
        agent_id=agent.id,
        message=f"{lead_count} new leads found for '{agent.name}'",
        lead_count=lead_count,
    )

    db.add(notification)
    db.commit()

def send_instant_notification(intent, match_data):
    """
    Triggers immediate notifications via configured channels (Email, SMS, WebSocket).
    
    Args:
        intent: BuyerIntent object containing contact info.
        match_data: Dictionary with match details (score, reasons, lead info).
    """
    try:
        channels = (intent.notification_preferences or "email").split(",")
        message = f"New Match Found! Score: {match_data['score']}. Reasons: {', '.join(match_data['reasons'])}"
        
        if "email" in channels and intent.email:
            _send_email(intent.email, "New Lead Match", message)
            
        if "sms" in channels and intent.phone:
            _send_sms(intent.phone, message)
            
        if "websocket" in channels:
            _send_websocket_update(intent.user_id, match_data)
            
    except Exception as e:
        logger.error(f"Failed to send instant notification: {e}")

def _send_email(to_email, subject, body):
    # TODO: Integrate SendGrid / Postmark
    logger.info(f"📧 EMAIL SENT to {to_email}: [{subject}] {body}")

def _send_sms(phone_number, body):
    # TODO: Integrate Twilio
    logger.info(f"📱 SMS SENT to {phone_number}: {body}")

def _send_websocket_update(user_id, data):
    # TODO: Push to Redis/Websocket server
    logger.info(f"⚡ WEBSOCKET UPDATE for {user_id}: {data}")
