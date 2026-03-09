"""
Application models.
"""

from app.models.agent import Agent
from app.models.lead import Lead, ContactStatus, CRMStatus
from app.models.notification import Notification
from app.models.user import User

__all__ = [
    "Agent",
    "Lead",
    "ContactStatus",
    "CRMStatus",
    "Notification",
    "User",
]
