"""
Celery Tasks for Lead Processing
Background lead verification and enrichment
"""
from datetime import datetime
from typing import List, Dict

from app.core.celery_config import celery_app
from app.models.lead import SessionLocal, Lead, Signal
from app.services.lead_verification import get_verification_service


@celery_app.task(bind=True, max_retries=2)
def create_lead_from_signals(self, signal_ids: List[int]) -> Dict:
    """
    Create or update a lead from multiple signals
    
    Args:
        signal_ids: List of signal database IDs
        
    Returns:
        Dict with lead creation result
    """
    print(f"[Worker] Creating lead from {len(signal_ids)} signals")
    
    db = SessionLocal()
    try:
        # Get all signals
        signals = db.query(Signal).filter(Signal.id.in_(signal_ids)).all()
        
        if not signals:
            return {"error": "No signals found"}
        
        # Get unique authors
        authors = set(s.author for s in signals if s.author)
        
        results = []
        for author in authors:
            author_signals = [s for s in signals if s.author == author]
            
            # Check for existing lead
            existing = db.query(Lead).filter(Lead.username == author).first()
            
            if existing:
                # Update existing
                existing.signal_ids = list(set(
                    (existing.signal_ids or []) + [s.id for s in author_signals]
                ))
                existing.sources = list(set(
                    (existing.sources or []) + [s.source for s in author_signals]
                ))
                
                # Update intent signals
                new_signals = [s.content[:300] for s in author_signals]
                existing.intent_signals = (existing.intent_signals or []) + new_signals
                existing.intent_signals = existing.intent_signals[:10]  # Keep top 10
                
                # Recalculate score
                all_signals = db.query(Signal).filter(Signal.author == author).all()
                if all_signals:
                    existing.intent_score = sum(s.intent_score for s in all_signals) / len(all_signals)
                
                existing.last_active = datetime.utcnow()
                
                # Mark signals as processed
                for s in author_signals:
                    s.is_processed = True
                    s.lead_id = existing.id
                    s.is_lead = True
                
                db.commit()
                
                results.append({
                    "action": "updated",
                    "lead_id": existing.id,
                    "username": author,
                })
            else:
                # Create new lead
                lead = Lead(
                    signal_ids=[s.id for s in author_signals],
                    sources=list(set(s.source for s in author_signals)),
                    username=author,
                    intent_score=sum(s.intent_score for s in author_signals) / len(author_signals),
                    intent_category=author_signals[0].intent_category,
                    buying_urgency=author_signals[0].buying_urgency,
                    profile_urls={s.source: s.source_url for s in author_signals},
                    intent_signals=[s.content[:300] for s in author_signals[:5]],
                    status="new",
                    verification_score=min(len(author_signals) * 0.2 + 0.3, 1.0),
                    first_seen=datetime.utcnow(),
                    last_active=datetime.utcnow(),
                )
                
                db.add(lead)
                db.flush()
                
                # Mark signals
                for s in author_signals:
                    s.is_processed = True
                    s.lead_id = lead.id
                    s.is_lead = True
                
                db.commit()
                
                results.append({
                    "action": "created",
                    "lead_id": lead.id,
                    "username": author,
                })
        
        return {
            "task_id": self.request.id,
            "signals_processed": len(signals),
            "leads_created": len([r for r in results if r["action"] == "created"]),
            "leads_updated": len([r for r in results if r["action"] == "updated"]),
            "results": results,
        }
        
    except Exception as exc:
        db.rollback()
        print(f"[Worker] Lead creation failed: {exc}")
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def verify_lead(self, lead_id: int) -> Dict:
    """
    Verify and enrich a lead's data
    
    This runs background checks on a lead:
    - Extract contact info from signals
    - Validate data quality
    - Update verification score
    """
    print(f"[Worker] Verifying lead {lead_id}")
    
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {"error": "Lead not found"}
        
        # Get all signals for this lead
        signals = db.query(Signal).filter(Signal.lead_id == lead_id).all()
        
        # Extract contact info from signal content
        verification_service = get_verification_service()
        
        emails = set()
        phones = set()
        locations = set()
        
        for signal in signals:
            content = signal.content or ""
            
            # Extract email
            email = verification_service._extract_email(content)
            if email:
                emails.add(email)
            
            # Extract phone
            phone = verification_service._extract_phone(content)
            if phone:
                phones.add(phone)
            
            # Extract location
            location = verification_service._extract_location(content)
            if location:
                locations.add(location)
        
        # Update lead
        if emails:
            lead.email = list(emails)[0]  # Use first found
        if phones:
            lead.phone = list(phones)[0]
        if locations:
            lead.location = list(locations)[0]
        
        # Recalculate verification score
        score = 0.3  # Base score
        score += min(len(signals) * 0.15, 0.4)
        if lead.email:
            score += 0.25
        if lead.phone:
            score += 0.25
        if lead.location:
            score += 0.1
        
        lead.verification_score = min(score, 1.0)
        
        # Calculate priority score
        lead.priority_score = min(
            (lead.intent_score * 0.4) +
            (lead.verification_score * 0.3) +
            (0.3 if lead.email else 0) +
            (0.2 if lead.phone else 0),
            1.0
        )
        
        db.commit()
        
        return {
            "task_id": self.request.id,
            "lead_id": lead_id,
            "verification_score": lead.verification_score,
            "priority_score": lead.priority_score,
            "contact_found": {
                "email": lead.email is not None,
                "phone": lead.phone is not None,
                "location": lead.location is not None,
            },
        }
        
    except Exception as exc:
        db.rollback()
        print(f"[Worker] Lead verification failed: {exc}")
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


@celery_app.task
def enrich_lead_data(lead_id: int) -> Dict:
    """
    Enrich lead with additional data from external sources
    
    This could integrate with:
    - LinkedIn API
    - Clearbit
    - Hunter.io for email verification
    - etc.
    
    For now, does basic enrichment from signals
    """
    print(f"[Worker] Enriching lead {lead_id}")
    
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {"error": "Lead not found"}
        
        # Get all content from signals
        signals = db.query(Signal).filter(Signal.lead_id == lead_id).all()
        all_content = " ".join([s.content or "" for s in signals])
        
        # Try to extract company name
        company_patterns = [
            r'at\s+([A-Z][\w\s&]+(?:Ltd|Limited|Inc|Corp|Company)?)',
            r'work\s+(?:at|for)\s+([A-Z][\w\s&]+)',
        ]
        
        import re
        company = None
        for pattern in company_patterns:
            match = re.search(pattern, all_content)
            if match:
                company = match.group(1).strip()
                break
        
        if company:
            lead.company = company
        
        # Try to extract name
        name_patterns = [
            r"(?:i am|i'm|my name is)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
        ]
        
        name = None
        for pattern in name_patterns:
            match = re.search(pattern, all_content, re.IGNORECASE)
            if match:
                name = match.group(1)
                break
        
        if name:
            lead.name = name
        
        db.commit()
        
        return {
            "lead_id": lead_id,
            "enriched": {
                "company": lead.company is not None,
                "name": lead.name is not None,
            },
        }
        
    finally:
        db.close()


@celery_app.task
def process_unprocessed_signals() -> Dict:
    """
    Background task to process any unprocessed signals
    
    Runs periodically to catch any signals that weren't processed
    """
    print("[Worker] Processing unprocessed signals")
    
    db = SessionLocal()
    try:
        # Get unprocessed signals with high intent
        signals = db.query(Signal).filter(
            Signal.is_processed == False,
            Signal.intent_score >= 0.4
        ).limit(100).all()
        
        if not signals:
            return {"message": "No unprocessed signals"}
        
        # Group by author
        by_author = {}
        for signal in signals:
            author = signal.author
            if author not in by_author:
                by_author[author] = []
            by_author[author].append(signal.id)
        
        # Create tasks for each author
        results = []
        for author, signal_ids in by_author.items():
            task = create_lead_from_signals.delay(signal_ids)
            results.append({
                "author": author,
                "task_id": task.id,
                "signal_count": len(signal_ids),
            })
        
        return {
            "authors_processed": len(by_author),
            "total_signals": len(signals),
            "tasks_created": len(results),
            "results": results,
        }
        
    finally:
        db.close()


@celery_app.task
def cleanup_old_tasks():
    """
    Cleanup old task results from Redis
    
    Should be run periodically (daily)
    """
    from celery import current_app
    
    # Clean up results older than 24 hours
    current_app.backend.cleanup()
    
    return {"status": "cleanup_complete"}
