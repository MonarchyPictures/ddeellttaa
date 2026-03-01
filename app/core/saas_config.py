# app/core/saas_config.py
# ============================================================
# SAAS MONETIZATION ARCHITECTURE — Tiered Plans & Feature Flags
# ============================================================
# Defines subscription tiers and feature access:
# - Free: 5 searches/day, 10 leads max
# - Pro: Unlimited searches, agents, CSV export
# - Enterprise: API, webhooks, multi-user
# ============================================================

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
import os


class PlanTier(Enum):
    """Subscription plan tiers."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class PlanLimits:
    """Resource limits for each plan."""
    daily_searches: int
    max_leads_per_search: int
    max_agents: int
    retention_days: int
    csv_export: bool
    api_access: bool
    webhooks: bool
    multi_user: bool
    auto_dm_bot: bool
    whatsapp_bot: bool
    auto_vertical_classify: bool


# Plan Configuration
PLAN_CONFIG = {
    PlanTier.FREE: PlanLimits(
        daily_searches=5,
        max_leads_per_search=10,
        max_agents=0,
        retention_days=7,
        csv_export=False,
        api_access=False,
        webhooks=False,
        multi_user=False,
        auto_dm_bot=False,
        whatsapp_bot=False,
        auto_vertical_classify=False,
    ),
    PlanTier.PRO: PlanLimits(
        daily_searches=999999,  # Unlimited
        max_leads_per_search=50,
        max_agents=5,
        retention_days=30,
        csv_export=True,
        api_access=True,
        webhooks=False,
        multi_user=False,
        auto_dm_bot=False,
        whatsapp_bot=False,
        auto_vertical_classify=True,
    ),
    PlanTier.ENTERPRISE: PlanLimits(
        daily_searches=999999,  # Unlimited
        max_leads_per_search=100,
        max_agents=999999,  # Unlimited
        retention_days=365,
        csv_export=True,
        api_access=True,
        webhooks=True,
        multi_user=True,
        auto_dm_bot=True,
        whatsapp_bot=True,
        auto_vertical_classify=True,
    ),
}


class SubscriptionManager:
    """Manages user subscriptions and feature access."""
    
    def __init__(self, user_tier: PlanTier = PlanTier.FREE):
        self.tier = user_tier
        self.limits = PLAN_CONFIG[user_tier]
    
    def can_search(self, daily_count: int) -> tuple[bool, str]:
        """Check if user can perform search."""
        if daily_count >= self.limits.daily_searches:
            return False, f"Daily limit reached ({self.limits.daily_searches} searches). Upgrade to Pro."
        return True, ""
    
    def can_create_agent(self, current_agents: int) -> tuple[bool, str]:
        """Check if user can create agent."""
        if self.limits.max_agents == 0:
            return False, "Agents not available on Free plan. Upgrade to Pro."
        if current_agents >= self.limits.max_agents:
            return False, f"Agent limit reached ({self.limits.max_agents}). Upgrade for more."
        return True, ""
    
    def can_export_csv(self) -> tuple[bool, str]:
        """Check if user can export CSV."""
        if not self.limits.csv_export:
            return False, "CSV export requires Pro plan."
        return True, ""
    
    def can_use_api(self) -> tuple[bool, str]:
        """Check if user has API access."""
        if not self.limits.api_access:
            return False, "API access requires Pro plan."
        return True, ""
    
    def can_use_webhooks(self) -> tuple[bool, str]:
        """Check if user can use webhooks."""
        if not self.limits.webhooks:
            return False, "Webhooks require Enterprise plan."
        return True, ""
    
    def can_use_dm_bot(self) -> tuple[bool, str]:
        """Check if user can use auto-DM bot."""
        if not self.limits.auto_dm_bot:
            return False, "Auto-DM bot requires Enterprise plan."
        return True, ""
    
    def get_limits_dict(self) -> Dict[str, Any]:
        """Get limits as dictionary for API response."""
        return {
            "tier": self.tier.value,
            "daily_searches": self.limits.daily_searches if self.limits.daily_searches < 999999 else "unlimited",
            "max_leads_per_search": self.limits.max_leads_per_search,
            "max_agents": self.limits.max_agents if self.limits.max_agents < 999999 else "unlimited",
            "retention_days": self.limits.retention_days,
            "features": {
                "csv_export": self.limits.csv_export,
                "api_access": self.limits.api_access,
                "webhooks": self.limits.webhooks,
                "multi_user": self.limits.multi_user,
                "auto_dm_bot": self.limits.auto_dm_bot,
                "whatsapp_bot": self.limits.whatsapp_bot,
                "auto_vertical_classify": self.limits.auto_vertical_classify,
            }
        }


# Global subscription manager (default to Free)
def get_subscription_manager(user_tier: Optional[str] = None) -> SubscriptionManager:
    """Get subscription manager for user."""
    if user_tier:
        try:
            tier = PlanTier(user_tier.lower())
            return SubscriptionManager(tier)
        except ValueError:
            pass
    return SubscriptionManager(PlanTier.FREE)


# Feature flag helpers
def feature_enabled(feature: str, user_tier: PlanTier) -> bool:
    """Check if feature is enabled for tier."""
    limits = PLAN_CONFIG[user_tier]
    return getattr(limits, feature, False)
