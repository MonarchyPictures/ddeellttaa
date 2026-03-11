"""
Real-Time Leads API with Enrichment
Push verified and enriched leads to dashboard
"""
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func

from app.models.lead import get_db, Lead, Signal
from app.services.lead_verification import get_verification_service
from app.services.lead_enrichment import get_enrichment_service
from app.tasks.enrichment_tasks import enrich_lead_task, batch_enrich_leads

router = APIRouter(prefix="/api/leads", tags=["Real-Time Leads"])


class LeadFeedFormatter:
    """Format leads for dashboard feed"""
    
    @staticmethod
    def format_lead(lead: Lead, include_signals: bool = True) -> dict:
        """Format a single lead for the feed"""
        primary_signal = lead.intent_signals[0] if lead.intent_signals else None
        platform = lead.sources[0] if lead.sources else "unknown"
        profile_url = lead.profile_urls.get(platform) if lead.profile_urls else ""
        
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
    def format_enriched_lead(lead: Lead) -> dict:
        """Format lead with enrichment data"""
        base = LeadFeedFormatter.format_lead(lead)
        
        # Add enrichment data
        enrichment = lead.metadata.get("enrichment", {}) if lead.metadata else {}
        
        base.update({
            "name": lead.name,
            "company": lead.company,
            "title": lead.job_title,
            "company_size": enrichment.get("company_size"),
            "industry": enrichment.get("industry"),
            "linkedin": lead.profile_urls.get("linkedin") if lead.profile_urls else None,
            "enrichment_confidence": enrichment.get("confidence"),
            "enriched_at": enrichment.get("enriched_at"),
        })
        
        return base


@router.get("")
async def get_leads_feed(
    q: Optional[str] = Query(None, description="Search query"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    sources: Optional[List[str]] = Query(None, description="Filter by multiple sources"),
    freshness: Optional[List[str]] = Query(None, description="Filter by freshness: 24h, 3d, 7d"),
    min_intent: float = Query(0.5, description="Minimum intent score"),
    min_verification: float = Query(0.5, description="Minimum verification score"),
    status: Optional[str] = Query("new", description="Lead status"),
    enriched_only: bool = Query(False, description="Only enriched leads"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get real-time leads feed with source and freshness filtering"""
    from datetime import datetime, timedelta
    
    query = db.query(Lead)
    
    # Text search
    if q:
        search_filter = or_(
            Lead.username.ilike(f"%{q}%"),
            Lead.intent_category.ilike(f"%{q}%"),
            Lead.location.ilike(f"%{q}%")
        )
        query = query.filter(search_filter)
    
    # Single platform filter (backward compatibility)
    if platform:
        from sqlalchemy import text
        query = query.filter(text(f"'{platform}' = ANY(sources)"))
    
    # Multiple sources filter
    if sources and len(sources) > 0:
        from sqlalchemy import text
        source_conditions = [f"'{s}' = ANY(sources)" for s in sources]
        query = query.filter(text(" OR ".join(source_conditions)))
    
    # Freshness filter
    if freshness and len(freshness) > 0:
        now = datetime.utcnow()
        freshness_conditions = []
        
        for f in freshness:
            if f == "24h":
                freshness_conditions.append(Lead.first_seen >= now - timedelta(hours=24))
            elif f == "3d":
                freshness_conditions.append(Lead.first_seen >= now - timedelta(days=3))
            elif f == "7d":
                freshness_conditions.append(Lead.first_seen >= now - timedelta(days=7))
        
        if freshness_conditions:
            query = query.filter(or_(*freshness_conditions))
    
    if enriched_only:
        query = query.filter(Lead.email.isnot(None))
    
    query = query.filter(Lead.intent_score >= min_intent)
    query = query.filter(Lead.verification_score >= min_verification)
    
    if status:
        query = query.filter(Lead.status == status)
    
    total = query.count()
    
    query = query.order_by(
        desc(Lead.priority_score),
        desc(Lead.intent_score),
        desc(Lead.first_seen)
    )
    
    leads = query.offset(offset).limit(limit).all()
    
    formatter = LeadFeedFormatter()
    formatted_leads = [formatter.format_lead(lead) for lead in leads]
    
    return {
        "query": q,
        "filters": {
            "platform": platform,
            "sources": sources,
            "freshness": freshness,
            "min_intent": min_intent,
            "enriched_only": enriched_only,
        },
        "total": total,
        "returned": len(formatted_leads),
        "leads": formatted_leads
    }


@router.get("/enriched")
async def get_enriched_leads(
    min_confidence: float = Query(0.6, description="Minimum enrichment confidence"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get enriched leads - the sales gold!
    
    These leads have email, company, LinkedIn - ready for outreach.
    """
    query = db.query(Lead).filter(
        Lead.email.isnot(None),
        Lead.status == "new"
    )
    
    # Filter by enrichment confidence
    query = query.filter(
        Lead.metadata["enrichment"]["confidence"].as_float() >= min_confidence
    )
    
    query = query.order_by(desc(Lead.priority_score))
    
    leads = query.limit(limit).all()
    
    formatter = LeadFeedFormatter()
    
    return {
        "count": len(leads),
        "leads": [formatter.format_enriched_lead(lead) for lead in leads]
    }


@router.get("/{lead_id}")
async def get_lead_detail(lead_id: int, db: Session = Depends(get_db)):
    """Get detailed lead info"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    formatter = LeadFeedFormatter()
    signals = db.query(Signal).filter(Signal.lead_id == lead_id).all()
    
    return {
        "lead": formatter.format_enriched_lead(lead),
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
    }


@router.post("/{lead_id}/enrich")
async def enrich_lead(
    lead_id: int,
    background_tasks: bool = True,
    db: Session = Depends(get_db)
):
    """
    Trigger enrichment for a lead
    
    Finds email, company data, LinkedIn profile.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Queue enrichment task
    task = enrich_lead_task.delay(lead_id)
    
    return {
        "message": "Enrichment started",
        "lead_id": lead_id,
        "task_id": task.id,
        "status": "processing"
    }


@router.post("/batch-enrich")
async def batch_enrich(
    lead_ids: List[int],
    priority: str = Query("normal", description="high or normal priority")
):
    """
    Enrich multiple leads in batch
    """
    task = batch_enrich_leads.delay(lead_ids, priority)
    
    return {
        "message": f"Batch enrichment queued ({len(lead_ids)} leads)",
        "task_id": task.id,
        "priority": priority,
    }


@router.post("/{lead_id}/claim")
async def claim_lead(lead_id: int, user: str = Query(...), db: Session = Depends(get_db)):
    """Claim a lead"""
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
        "message": "Lead claimed",
        "lead_id": lead_id,
        "claimed_by": user,
    }


@router.get("/stats/enrichment")
async def get_enrichment_stats(db: Session = Depends(get_db)):
    """
    Get enrichment statistics
    
    Shows how many leads have been enriched with email, company, etc.
    """
    total = db.query(Lead).count()
    with_email = db.query(Lead).filter(Lead.email.isnot(None)).count()
    with_company = db.query(Lead).filter(Lead.company.isnot(None)).count()
    with_phone = db.query(Lead).filter(Lead.phone.isnot(None)).count()
    with_linkedin = db.query(Lead).filter(
        Lead.profile_urls.contains({"linkedin": ""})
    ).count()
    
    # Enrichment rate by source
    source_stats = db.query(
        func.unnest(Lead.sources).label("source"),
        func.count(Lead.id),
        func.sum(func.case([(Lead.email.isnot(None), 1)], else_=0))
    ).group_by("source").all()
    
    return {
        "total_leads": total,
        "enriched": {
            "with_email": with_email,
            "with_company": with_company,
            "with_phone": with_phone,
            "with_linkedin": with_linkedin,
        },
        "enrichment_rate": round(with_email / total * 100, 1) if total > 0 else 0,
        "by_source": [
            {
                "source": source,
                "total": total_count,
                "with_email": email_count,
                "rate": round(email_count / total_count * 100, 1) if total_count > 0 else 0
            }
            for source, total_count, email_count in source_stats
        ]
    }
