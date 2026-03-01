"""
Database module.
Import all models here to ensure they are registered with SQLAlchemy.
"""
from app.db.base_class import Base
from app.db.models import (
    BuyerLead,
    AgentRunLog,
    BuyerIntent,
    SearchPattern,
    ActivityLog,
    ScraperMetric,
    CategoryMetric,
    SystemSetting,
    Cache,
)
from app.models.lead import Lead, ContactStatus, CRMStatus
from app.models.agent import Agent

# All models are now imported and registered with Base.metadata
__all__ = [
    "Base",
    "BuyerLead",
    "AgentRunLog",
    "BuyerIntent",
    "SearchPattern",
    "ActivityLog",
    "ScraperMetric",
    "CategoryMetric",
    "SystemSetting",
    "Cache",
    "Lead",
    "ContactStatus",
    "CRMStatus",
    "Agent",
]
