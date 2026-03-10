"""
Celery Tasks for Lead Enrichment
Background enrichment with email finder, company data, LinkedIn
"""
from datetime import datetime
from typing import Dict, Optional

from app.core.celery_config import celery_app
from app.services.lead_enrichment import get_enrichment_service
from app.models.lead import SessionLocal, Lead, Signal


@celery_app.task(bind=True, max_retries=3)
def enrich_lead_task(self, lead_id: int) -> Dict:
    """
    Enrich a lead with email, company data, LinkedIn
    
    This is the 'secret sauce' that turns raw signals into sales gold.
    """
    print(f"[Enrichment] Starting enrichment for lead {lead_id}")
    
    db = SessionLocal()
    try:
        # Get lead
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {"error": "Lead not found"}
        
        # Get primary signal text
        signal = db.query(Signal).filter(Signal.lead_id == lead_id).first()
        signal_text = signal.content if signal else ""
        
        # Prepare lead data
        lead_data = {
            "id": lead.id,
            "username": lead.username,
            "company": lead.company,
            "location": lead.location,
            "country": lead.country,
            "intent_score": lead.intent_score,
            "buying_urgency": lead.buying_urgency,
            "job_title": lead.job_title,
        }
        
        # Run enrichment
        enrichment_service = get_enrichment_service()
        enriched = enrichment_service.enrich(lead_data, signal_text)
        
        # Update lead with enriched data
        lead.name = enriched.name
        lead.email = enriched.email
        lead.phone = enriched.phone
        lead.company = enriched.company
        lead.job_title = enriched.title
        lead.location = enriched.location or lead.location
        lead.country = enriched.country
        
        # Add profile URLs
        if enriched.linkedin_url:
            lead.profile_urls = lead.profile_urls or {}
            lead.profile_urls["linkedin"] = enriched.linkedin_url
        
        # Update metadata
        lead.metadata = lead.metadata or {}
        lead.metadata["enrichment"] = {
            "sources": enriched.enrichment_sources,
            "confidence": enriched.enrichment_confidence,
            "enriched_at": enriched.enriched_at,
            "first_name": enriched.first_name,
            "last_name": enriched.last_name,
            "company_size": enriched.company_size,
            "industry": enriched.industry,
        }
        
        # Boost verification score if enrichment successful
        if enriched.enrichment_confidence > 0.6:
            lead.verification_score = max(lead.verification_score, 0.8)
        
        db.commit()
        
        print(f"[Enrichment] ✅ Lead {lead_id} enriched successfully")
        print(f"  Email: {enriched.email or 'Not found'}")
        print(f"  Company: {enriched.company or 'Not found'}")
        print(f"  LinkedIn: {enriched.linkedin_url or 'Not found'}")
        
        return {
            "lead_id": lead_id,
            "status": "enriched",
            "email_found": enriched.email is not None,
            "company_found": enriched.company is not None,
            "linkedin_found": enriched.linkedin_url is not None,
            "confidence": enriched.enrichment_confidence,
            "sources": enriched.enrichment_sources,
        }
        
    except Exception as exc:
        db.rollback()
        print(f"[Enrichment] ❌ Error enriching lead {lead_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task
def batch_enrich_leads(lead_ids: list, priority: str = "normal") -> Dict:
    """
    Enrich multiple leads in batch
    
    Args:
        lead_ids: List of lead IDs to enrich
        priority: "high" for urgent leads, "normal" for regular
    """
    results = []
    
    for lead_id in lead_ids:
        # For high priority, run immediately
        # For normal, queue with countdown to spread load
        countdown = 0 if priority == "high" else (lead_ids.index(lead_id) * 5)
        
        task = enrich_lead_task.apply_async(args=[lead_id], countdown=countdown)
        results.append({
            "lead_id": lead_id,
            "task_id": task.id,
        })
    
    return {
        "batch_size": len(lead_ids),
        "priority": priority,
        "tasks_created": len(results),
        "results": results,
    }


@celery_app.task
def auto_enrich_new_leads(min_intent_score: float = 0.7) -> Dict:
    """
    Automatically enrich high-intent leads that haven't been enriched
    
    Runs periodically to enrich new leads as they come in.
    """
    db = SessionLocal()
    try:
        # Find leads that need enrichment
        # Criteria: high intent, no email, not yet enriched
        leads = db.query(Lead).filter(
            Lead.intent_score >= min_intent_score,
            Lead.email.is_(None),  # No email yet
            Lead.status == "new",  # New leads only
        ).limit(50).all()
        
        if not leads:
            return {"message": "No leads need enrichment"}
        
        # Queue enrichment tasks
        lead_ids = [lead.id for lead in leads]
        result = batch_enrich_leads.delay(lead_ids, priority="high")
        
        return {
            "leads_queued": len(lead_ids),
            "batch_task_id": result.id,
            "lead_ids": lead_ids,
        }
        
    finally:
        db.close()


@celery_app.task
def enrich_by_search_query(query_id: int) -> Dict:
    """
    Enrich all leads from a specific search query
    
    Useful when you want to enrich all leads for a particular campaign.
    """
    db = SessionLocal()
    try:
        # Get all signals for this query
        signals = db.query(Signal).filter(
            Signal.search_query_id == query_id,
            Signal.is_lead == True
        ).all()
        
        lead_ids = [s.lead_id for s in signals if s.lead_id]
        
        if not lead_ids:
            return {"message": "No leads found for this query"}
        
        # Enrich all
        result = batch_enrich_leads.delay(lead_ids)
        
        return {
            "query_id": query_id,
            "leads_queued": len(lead_ids),
            "batch_task_id": result.id,
        }
        
    finally:
        db.close()
