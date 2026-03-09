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

# Note: Lead and Agent models are defined in app.models.lead and app.models.agent
# Import them directly from there to avoid circular imports:
#   from app.models.lead import Lead
#   from app.models.agent import Agent

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
]
