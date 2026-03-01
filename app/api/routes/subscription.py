# app/api/routes/subscription.py
# ============================================================
# SUBSCRIPTION API — SaaS Tier Management
# ============================================================
# Endpoints for:
# - Checking subscription status
# - Getting plan limits
# - Upgrading/downgrading plans
# - Webhook for payment processor (Stripe, etc.)
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from app.core.saas_config import (
    SubscriptionManager, PlanTier, get_subscription_manager,
    PLAN_CONFIG
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscription", tags=["subscription"])


class SubscriptionStatus(BaseModel):
    """User subscription status response."""
    tier: str
    limits: Dict[str, Any]
    usage: Dict[str, Any]
    upgrade_available: bool


class PlanComparison(BaseModel):
    """Plan comparison for pricing page."""
    plans: Dict[str, Dict[str, Any]]


class UpgradeRequest(BaseModel):
    """Plan upgrade request."""
    target_tier: str
    payment_method: Optional[str] = None


# Mock user database (replace with real DB)
USER_SUBSCRIPTIONS = {
    # "user_id": {"tier": "pro", "daily_searches": 3, "agents": 2}
}


def get_current_user_tier(user_id: str = "default") -> PlanTier:
    """Get current user's subscription tier."""
    # In production, fetch from database
    # For now, check environment or return Free
    user_sub = USER_SUBSCRIPTIONS.get(user_id, {"tier": "free"})
    try:
        return PlanTier(user_sub["tier"])
    except ValueError:
        return PlanTier.FREE


def get_user_usage(user_id: str = "default") -> Dict[str, Any]:
    """Get user's current usage stats."""
    # In production, query from database
    return {
        "daily_searches_used": USER_SUBSCRIPTIONS.get(user_id, {}).get("daily_searches", 0),
        "agents_created": USER_SUBSCRIPTIONS.get(user_id, {}).get("agents", 0),
        "leads_exported": 0,
    }


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    user_id: str = "default"
) -> SubscriptionStatus:
    """
    Get current user's subscription status and limits.
    
    Returns:
    - Current tier
    - Plan limits
    - Current usage
    - Upgrade availability
    """
    tier = get_current_user_tier(user_id)
    manager = SubscriptionManager(tier)
    usage = get_user_usage(user_id)
    
    return SubscriptionStatus(
        tier=tier.value,
        limits=manager.get_limits_dict(),
        usage=usage,
        upgrade_available=tier != PlanTier.ENTERPRISE
    )


@router.get("/plans", response_model=PlanComparison)
async def get_plan_comparison() -> PlanComparison:
    """
    Get all available plans with features and pricing.
    
    For frontend pricing page.
    """
    plans = {
        "free": {
            "name": "Free",
            "price": 0,
            "price_label": "Free forever",
            "description": "For individuals trying out Delta9",
            "features": {
                "daily_searches": "5",
                "max_leads": "10 per search",
                "agents": "Not included",
                "csv_export": False,
                "api_access": False,
                "webhooks": False,
                "retention": "7 days",
            },
            "cta": "Get Started",
            "popular": False,
        },
        "pro": {
            "name": "Pro",
            "price": 29,
            "price_label": "$29/month",
            "description": "For serious lead generation professionals",
            "features": {
                "daily_searches": "Unlimited",
                "max_leads": "50 per search",
                "agents": "Up to 5",
                "csv_export": True,
                "api_access": True,
                "webhooks": False,
                "retention": "30 days",
            },
            "cta": "Upgrade to Pro",
            "popular": True,
        },
        "enterprise": {
            "name": "Enterprise",
            "price": 99,
            "price_label": "$99/month",
            "description": "For teams and businesses",
            "features": {
                "daily_searches": "Unlimited",
                "max_leads": "100 per search",
                "agents": "Unlimited",
                "csv_export": True,
                "api_access": True,
                "webhooks": True,
                "retention": "1 year",
                "auto_dm_bot": True,
                "whatsapp_bot": True,
            },
            "cta": "Contact Sales",
            "popular": False,
        },
    }
    
    return PlanComparison(plans=plans)


@router.post("/upgrade")
async def upgrade_plan(
    request: UpgradeRequest,
    user_id: str = "default"
) -> Dict[str, Any]:
    """
    Upgrade user to a higher tier.
    
    In production, integrate with Stripe/PayPal.
    """
    try:
        target_tier = PlanTier(request.target_tier.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan tier")
    
    current_tier = get_current_user_tier(user_id)
    
    # Prevent downgrades through this endpoint
    if PLAN_CONFIG[target_tier].daily_searches <= PLAN_CONFIG[current_tier].daily_searches:
        raise HTTPException(status_code=400, detail="Cannot downgrade through upgrade endpoint")
    
    # Mock upgrade (replace with payment integration)
    USER_SUBSCRIPTIONS[user_id] = {
        "tier": target_tier.value,
        "daily_searches": 0,
        "agents": 0,
        "upgraded_at": "2024-01-01T00:00:00Z"
    }
    
    logger.info(f"User {user_id} upgraded from {current_tier.value} to {target_tier.value}")
    
    return {
        "status": "success",
        "message": f"Upgraded to {target_tier.value}",
        "new_tier": target_tier.value,
        "limits": SubscriptionManager(target_tier).get_limits_dict()
    }


@router.post("/webhook/stripe")
async def stripe_webhook(
    payload: Dict[str, Any],
    stripe_signature: str = Header(None, alias="Stripe-Signature")
) -> Dict[str, str]:
    """
    Stripe webhook for subscription events.
    
    Handles:
    - subscription.created
    - subscription.updated
    - subscription.cancelled
    - payment succeeded/failed
    """
    # Verify webhook signature (in production)
    # event = stripe.Webhook.construct_event(payload, stripe_signature, endpoint_secret)
    
    event_type = payload.get("type")
    
    if event_type == "customer.subscription.created":
        # Handle new subscription
        logger.info("New subscription created")
        
    elif event_type == "customer.subscription.deleted":
        # Handle cancellation
        logger.info("Subscription cancelled")
        
    elif event_type == "invoice.payment_failed":
        # Handle failed payment
        logger.warning("Payment failed")
    
    return {"status": "received"}


@router.get("/check/{feature}")
async def check_feature_access(
    feature: str,
    user_id: str = "default"
) -> Dict[str, Any]:
    """
    Check if user has access to a specific feature.
    
    Features: csv_export, api_access, webhooks, auto_dm_bot, etc.
    """
    tier = get_current_user_tier(user_id)
    manager = SubscriptionManager(tier)
    
    # Map feature names to check methods
    checks = {
        "csv_export": manager.can_export_csv,
        "api_access": manager.can_use_api,
        "webhooks": manager.can_use_webhooks,
        "auto_dm_bot": manager.can_use_dm_bot,
    }
    
    check_fn = checks.get(feature)
    if not check_fn:
        return {"feature": feature, "access": False, "error": "Unknown feature"}
    
    allowed, message = check_fn()
    
    return {
        "feature": feature,
        "access": allowed,
        "message": message,
        "current_tier": tier.value
    }


# Middleware helper for enforcing limits
async def enforce_search_limit(user_id: str = "default"):
    """Enforce daily search limit."""
    tier = get_current_user_tier(user_id)
    manager = SubscriptionManager(tier)
    usage = get_user_usage(user_id)
    
    allowed, message = manager.can_search(usage["daily_searches_used"])
    if not allowed:
        raise HTTPException(status_code=429, detail={
            "error": "Limit exceeded",
            "message": message,
            "current_tier": tier.value,
            "upgrade_url": "/subscription/plans"
        })


async def enforce_agent_limit(user_id: str = "default"):
    """Enforce agent creation limit."""
    tier = get_current_user_tier(user_id)
    manager = SubscriptionManager(tier)
    usage = get_user_usage(user_id)
    
    allowed, message = manager.can_create_agent(usage["agents_created"])
    if not allowed:
        raise HTTPException(status_code=429, detail={
            "error": "Limit exceeded",
            "message": message,
            "current_tier": tier.value,
            "upgrade_url": "/subscription/plans"
        })
