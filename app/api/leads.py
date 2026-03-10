"""
Real-Time Leads API
Push verified leads to dashboard
"""
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from app.models.lead import get_db, Lead, Signal
from app.services.lead_verification import get_verification_service

router = APIRouter(prefix="/api/leads", tags=["Real-Time Leads"])


class LeadFeedFormatter:
    """
    Format leads for dashboard feed
    
    Input: Lead database model
    Output: Clean, frontend-friendly format
    """
    
    @staticmethod
    def format_lead(lead: Lead, include_signals: bool = True) -> dict:
        """
        Format a single lead for the feed
        
        Returns:
            {
                "id": int,
                "text": str,           # Primary intent signal
                "platform": str,       # Source platform
                "url": str,            # Source URL
                "author": str,         # Username
                "intent_score": float, # 0-1 buyer probability
                "verification_score": float,
                "urgency": str,        # immediate, soon, future
                "location": str,
                "contact": {
                    "email": str,
                    "phone": str
                },
                "discovered_at": str,  # ISO timestamp
                "priority": str        # low, medium, high, urgent
            }
        """
        # Get primary signal (most recent or highest intent)
        primary_signal = None
        if lead.intent_signals:
            primary_signal = lead.intent_signals[0] if lead.intent_signals else None
        
        # Get primary platform
        platform = lead.sources[0] if lead.sources else "unknown"
        
        # Get profile URL for the platform
        profile_url = ""
        if lead.profile_urls and platform in lead.profile_urls:
            profile_url = lead.profile_urls[platform]
        
        return {
            "id": lead.id,
            "text": primary_signal or f"Lead from {platform}",
            "platform": platform,
            "url": profile_url,
            "author": lead.username,
            "intent_score": round(lead.intent_score, 2),
            "verification_score": round(lead.verification_score, 2),
            "urgency": lead.buying_urgency or "unknown",
            "location": lead.location or "Unknown",
            "contact": {
                "email": lead.email,
                "phone": lead.phone
            },
            "discovered_at": lead.first_seen.isoformat() if lead.first_seen else None,
            "priority": lead.priority or "medium",
            "status": lead.status or "new"
        }
    
    @staticmethod
    def format_signal_as_lead(signal: Signal) -> dict:
        """
        Format a high-intent signal as a lead preview
        
        Used for real-time feed before lead is fully created
        """
        return {
            "id": f"signal_{signal.id}",
            "text": signal.content[:300] if signal.content else "",
            "platform": signal.source,
            "url": signal.source_url or "",
            "author": signal.author,
            "intent_score": round(signal.intent_score, 2),
            "verification_score": round(signal.verification_score, 2),
            "urgency": signal.buying_urgency or "unknown",
            "location": "Unknown",
            "contact": {
                "email": None,
                "phone": None
            },
            "discovered_at": signal.discovered_at.isoformat() if signal.discovered_at else None,
            "priority": "high" if signal.intent_score >= 0.7 else "medium",
            "status": "signal",  # Not yet a full lead
            "is_preview": True
        }


@router.get("")
async def get_leads_feed(
    q: Optional[str] = Query(None, description="Search query to filter leads"),
    platform: Optional[str] = Query(None, description="Filter by platform (reddit, twitter, forum)"),
    min_intent: float = Query(0.5, description="Minimum intent score (0-1)"),
    min_verification: float = Query(0.5, description="Minimum verification score (0-1)"),
    status: Optional[str] = Query("new", description="Lead status filter"),
    limit: int = Query(50, description="Number of leads to return", ge=1, le=100),
    offset: int = Query(0, description="Pagination offset"),
    hours: Optional[int] = Query(None, description="Only leads from last N hours"),
    db: Session = Depends(get_db)
):
    """
    Get real-time leads feed
    
    Returns verified leads matching the query, sorted by priority.
    Perfect for dashboard display.
    
    Example:
        GET /api/leads?q=plumber&limit=10
        
    Response:
        {
            "query": "plumber",
            "total": 150,
            "returned": 10,
            "leads": [
                {
                    "id": 123,
                    "text": "Looking for plumber near me ASAP!",
                    "platform": "reddit",
                    "url": "https://reddit.com/...",
                    "author": "homeowner_ke",
                    "intent_score": 0.85,
                    "verification_score": 0.92,
                    "urgency": "immediate",
                    "location": "Nairobi",
                    "contact": {"email": null, "phone": null},
                    "discovered_at": "2026-03-10T14:30:00",
                    "priority": "urgent"
                }
            ]
        }
    """
    # Build query
    query = db.query(Lead)
    
    # Filter by search query (match in intent_signals or username)
    if q:
        search_filter = or_(
            Lead.username.ilike(f"%{q}%"),
            Lead.intent_category.ilike(f"%{q}%"),
            Lead.location.ilike(f"%{q}%")
        )
        
        # For PostgreSQL, we can search in array
        # For SQLite, we need to handle differently
        try:
            # Try PostgreSQL array search
            from sqlalchemy import func
            search_filter = or_(
                search_filter,
                func.array_to_string(Lead.intent_signals, ' ').ilike(f"%{q}%")
            )
        except:
            pass  # SQLite fallback
        
        query = query.filter(search_filter)
    
    # Filter by platform
    if platform:
        # Search in sources array
        from sqlalchemy import text
        query = query.filter(
            text(f"'{platform}' = ANY(sources)")
        )
    
    # Quality filters
    query = query.filter(Lead.intent_score >= min_intent)
    query = query.filter(Lead.verification_score >= min_verification)
    
    # Status filter
    if status:
        query = query.filter(Lead.status == status)
    
    # Time filter (recent only)
    if hours:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(Lead.first_seen >= cutoff)
    
    # Count total before pagination
    total = query.count()
    
    # Sort by priority score (highest first), then by recency
    query = query.order_by(
        desc(Lead.priority_score),
        desc(Lead.intent_score),
        desc(Lead.first_seen)
    )
    
    # Paginate
    leads = query.offset(offset).limit(limit).all()
    
    # Format leads
    formatter = LeadFeedFormatter()
    formatted_leads = [formatter.format_lead(lead) for lead in leads]
    
    return {
        "query": q,
        "filters": {
            "platform": platform,
            "min_intent": min_intent,
            "min_verification": min_verification,
            "status": status,
            "hours": hours
        },
        "total": total,
        "returned": len(formatted_leads),
        "offset": offset,
        "leads": formatted_leads
    }


@router.get("/live")
async def get_live_feed(
    limit: int = Query(20, description="Number of recent items", ge=1, le=50),
    include_signals: bool = Query(True, description="Include high-intent signals not yet leads"),
    db: Session = Depends(get_db)
):
    """
    Get live feed of leads and high-intent signals
    
    Combines verified leads with fresh high-intent signals
    for real-time dashboard updates.
    """
    formatter = LeadFeedFormatter()
    feed_items = []
    
    # Get recent high-quality leads
    leads = db.query(Lead).filter(
        Lead.status == "new",
        Lead.intent_score >= 0.6
    ).order_by(
        desc(Lead.first_seen)
    ).limit(limit).all()
    
    feed_items.extend([formatter.format_lead(lead) for lead in leads])
    
    # Get high-intent signals not yet processed
    if include_signals and len(feed_items) < limit:
        signals = db.query(Signal).filter(
            Signal.is_lead == False,
            Signal.intent_score >= 0.7,
            Signal.verification_score >= 0.6
        ).order_by(
            desc(Signal.discovered_at)
        ).limit(limit - len(feed_items)).all()
        
        feed_items.extend([formatter.format_signal_as_lead(signal) for signal in signals])
    
    # Sort by discovered time
    feed_items.sort(
        key=lambda x: x.get("discovered_at", ""),
        reverse=True
    )
    
    return {
        "feed_type": "live",
        "count": len(feed_items),
        "updated_at": datetime.utcnow().isoformat(),
        "leads": feed_items[:limit]
    }


@router.get("/{lead_id}")
async def get_lead_detail(
    lead_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific lead
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    formatter = LeadFeedFormatter()
    
    # Get all signals for this lead
    signals = db.query(Signal).filter(Signal.lead_id == lead_id).all()
    
    return {
        "lead": formatter.format_lead(lead),
        "all_signals": [
            {
                "text": s.content,
                "platform": s.source,
                "url": s.source_url,
                "intent_score": s.intent_score,
                "discovered_at": s.discovered_at.isoformat() if s.discovered_at else None
            }
            for s in signals
        ],
        "signal_count": len(signals)
    }


@router.post("/{lead_id}/claim")
async def claim_lead(
    lead_id: int,
    user: str = Query(..., description="User claiming this lead"),
    db: Session = Depends(get_db)
):
    """
    Claim a lead (mark as contacted and assign to user)
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if lead.status != "new":
        raise HTTPException(status_code=400, detail=f"Lead already {lead.status}")
    
    lead.status = "contacted"
    lead.assigned_to = user
    lead.contacted_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Lead claimed successfully",
        "lead_id": lead_id,
        "claimed_by": user,
        "claimed_at": lead.contacted_at.isoformat()
    }


@router.get("/stats/overview")
async def get_leads_stats(
    hours: int = Query(24, description="Stats for last N hours"),
    db: Session = Depends(get_db)
):
    """
    Get leads statistics for dashboard
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Total leads
    total_leads = db.query(Lead).count()
    new_leads = db.query(Lead).filter(Lead.status == "new").count()
    
    # Recent leads
    recent_leads = db.query(Lead).filter(Lead.first_seen >= cutoff).count()
    
    # By platform
    from sqlalchemy import func
    platform_stats = db.query(
        func.unnest(Lead.sources).label("platform"),
        func.count(Lead.id)
    ).group_by("platform").all()
    
    # By urgency
    urgency_stats = db.query(
        Lead.buying_urgency,
        func.count(Lead.id)
    ).filter(Lead.buying_urgency != None).group_by(Lead.buying_urgency).all()
    
    # Average scores
    avg_intent = db.query(func.avg(Lead.intent_score)).scalar() or 0
    avg_verification = db.query(func.avg(Lead.verification_score)).scalar() or 0
    
    return {
        "period_hours": hours,
        "totals": {
            "all_time": total_leads,
            "new": new_leads,
            "recent": recent_leads
        },
        "by_platform": {platform: count for platform, count in platform_stats},
        "by_urgency": {urgency: count for urgency, count in urgency_stats},
        "quality": {
            "avg_intent_score": round(float(avg_intent), 2),
            "avg_verification_score": round(float(avg_verification), 2)
        }
    }
