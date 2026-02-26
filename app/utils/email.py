import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

def send_email(recipient_email: str, subject: str, body_html: str):
    """
    Sends a formatted HTML email to a recipient.
    In development, it logs the email content instead of sending.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL", "digest@delta-9.io")

    if not all([smtp_server, smtp_user, smtp_password]):
        logger.info(f"--- MOCK EMAIL SENT TO {recipient_email} ---")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body: {body_html[:200]}...")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email

        part = MIMEText(body_html, "html")
        msg.attach(part)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        
        logger.info(f"✅ Email successfully sent to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email to {recipient_email}: {str(e)}")
        return False
