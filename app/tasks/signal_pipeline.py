"""
Signal Pipeline Tasks with Lead Verification Layer
Process signals from the stream and convert to verified leads
"""
from datetime import datetime
from typing import Dict, List

from celery import chain, group

from app.core.celery_config import celery_app
from app.services.signal_stream import get_signal_stream, Signal, get_signal_producer
from app.services.intent_detection import get_intent_service
from app.services.lead_verification import get_verification_service, VerificationStatus, RejectionReason
from app.models.lead import SessionLocal, Signal as SignalModel, Lead


@celery_app.task(bind=True, max_retries=3)
def process_signal_stream(self, signal_data: Dict) -> Dict:
    """
    Process a single signal from the stream through verification layer
    
    Pipeline:
    1. Lead Verification Layer (spam, bot, duplicate, age checks)
    2. Intent Detection (buyer probability)
    3. Store in DB
    4. If verified + high intent -> Create lead
    """
    signal_id = signal_data.get('id', 'unknown')
    print(f"[Pipeline] Processing signal: {signal_id}")
    
    try:
        # STEP 1: LEAD VERIFICATION LAYER
        # This filters spam, bots, reposts, old posts
        verification_service = get_verification_service()
        verification = verification_service.verify(signal_data)
        
        # Add verification results to signal data
        signal_data['verification_score'] = verification.verification_score
        signal_data['verification_status'] = verification.status.value
        signal_data['verification_checks'] = verification.checks_passed
        signal_data['verification_warnings'] = verification.warnings
        signal_data['is_verified'] = verification.is_verified
        
        # Log verification results
        if verification.status == VerificationStatus.REJECTED:
            reasons = [r.value for r in verification.rejection_reasons]
            print(f"[Pipeline] ❌ Signal REJECTED: {reasons}")
            
            # Still store in DB for analytics, but mark as rejected
            db = SessionLocal()
            try:
                signal_record = SignalModel(
                    external_id=signal_data.get('id'),
                    source=signal_data.get('platform'),
                    title=signal_data.get('text', '')[:200],
                    content=signal_data.get('text', ''),
                    author=signal_data.get('author'),
                    source_url=signal_data.get('url'),
                    query_matched=signal_data.get('query'),
                    discovered_at=datetime.utcnow(),
                    is_processed=True,
                    is_lead=False,
                    metadata={
                        **signal_data.get('metadata', {}),
                        'rejected': True,
                        'rejection_reasons': reasons,
                        'verification': verification.metadata,
                    }
                )
                db.add(signal_record)
                db.commit()
            finally:
                db.close()
            
            return {
                "signal_id": signal_id,
                "status": "rejected",
                "reasons": reasons,
                "verification_score": verification.verification_score,
            }
        
        elif verification.status == VerificationStatus.SUSPICIOUS:
            print(f"[Pipeline] ⚠️ Signal SUSPICIOUS: {verification.warnings}")
            signal_data['is_suspicious'] = True
        
        else:
            print(f"[Pipeline] ✅ Signal VERIFIED (score: {verification.verification_score})")
        
        # STEP 2: INTENT DETECTION
        # Only check intent if signal passed basic verification
        intent_service = get_intent_service()
        text = signal_data.get('text', '')
        query = signal_data.get('query', '')
        
        intent = intent_service.analyze(text, query)
        
        # Add intent data
        signal_data['intent_score'] = intent.intent_score
        signal_data['intent_category'] = intent.intent_category
        signal_data['buying_urgency'] = intent.buying_urgency
        signal_data['keywords_matched'] = intent.keywords_matched
        signal_data['intent_confidence'] = intent.confidence
        signal_data['is_buyer'] = intent.is_buyer
        
        # STEP 3: STORE IN DATABASE
        db = SessionLocal()
        try:
            # Check for duplicate
            existing = db.query(SignalModel).filter(
                SignalModel.external_id == signal_data.get('id')
            ).first()
            
            if not existing:
                signal_record = SignalModel(
                    external_id=signal_data.get('id'),
                    source=signal_data.get('platform'),
                    title=text[:200] if len(text) > 200 else text,
                    content=text,
                    author=signal_data.get('author'),
                    source_url=signal_data.get('url'),
                    query_matched=query,
                    intent_score=intent.intent_score,
                    intent_category=intent.intent_category,
                    buying_urgency=intent.buying_urgency,
                    keywords_matched=intent.keywords_matched,
                    discovered_at=datetime.fromisoformat(signal_data.get('timestamp')) if signal_data.get('timestamp') else datetime.utcnow(),
                    is_processed=True,
                    is_lead=False,  # Will be updated if lead created
                    metadata={
                        **signal_data.get('metadata', {}),
                        'verification_score': verification.verification_score,
                        'verification_status': verification.status.value,
                        'verification_metadata': verification.metadata,
                    }
                )
                db.add(signal_record)
                db.commit()
                signal_data['db_id'] = signal_record.id
            else:
                signal_data['db_id'] = existing.id
                signal_data['duplicate'] = True
                
        finally:
            db.close()
        
        # STEP 4: CREATE LEAD IF VERIFIED + HIGH INTENT
        # Requirements:
        # - Must be verified (or suspicious but passing)
        # - Must have buyer intent (is_buyer = True)
        # - Intent score >= 0.5
        
        should_create_lead = (
            verification.is_verified and
            intent.is_buyer and
            intent.intent_score >= 0.5
        )
        
        if should_create_lead:
            print(f"[Pipeline] 🎯 Creating lead from verified signal")
            
            # Route to high_intent channel
            stream = get_signal_stream()
            stream.publish_signal(
                Signal(
                    id=signal_data.get('id'),
                    text=text,
                    platform=signal_data.get('platform'),
                    url=signal_data.get('url'),
                    author=signal_data.get('author'),
                    timestamp=signal_data.get('timestamp'),
                    query=query,
                    metadata={
                        **signal_data,
                        'verification': verification.metadata,
                        'intent': {
                            'score': intent.intent_score,
                            'category': intent.intent_category,
                            'urgency': intent.buying_urgency,
                        }
                    },
                ),
                channel='high_intent'
            )
            
            # Create lead
            lead_task = create_lead_from_signal.delay(signal_data)
            
            return {
                "signal_id": signal_id,
                "status": "lead_created",
                "intent_score": intent.intent_score,
                "verification_score": verification.verification_score,
                "lead_task_id": lead_task.id,
            }
        else:
            # Log why lead wasn't created
            reasons = []
            if not verification.is_verified:
                reasons.append("not_verified")
            if not intent.is_buyer:
                reasons.append("not_buyer")
            if intent.intent_score < 0.5:
                reasons.append("low_intent")
            
            print(f"[Pipeline] ℹ️ No lead created: {reasons}")
            
            return {
                "signal_id": signal_id,
                "status": "processed_no_lead",
                "intent_score": intent.intent_score,
                "verification_score": verification.verification_score,
                "reasons": reasons,
            }
        
    except Exception as exc:
        print(f"[Pipeline] ❌ Processing error: {exc}")
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=2)
def create_lead_from_signal(self, signal_data: Dict) -> Dict:
    """
    Create or update a lead from a verified high-intent signal
    """
    print(f"[Pipeline] Creating lead from signal: {signal_data.get('id')}")
    
    db = SessionLocal()
    try:
        author = signal_data.get('author')
        platform = signal_data.get('platform')
        
        # Check for existing lead
        existing = db.query(Lead).filter(Lead.username == author).first()
        
        if existing:
            # Update existing lead
            if signal_data.get('db_id') and signal_data.get('db_id') not in (existing.signal_ids or []):
                existing.signal_ids = (existing.signal_ids or []) + [signal_data.get('db_id')]
            
            existing.sources = list(set((existing.sources or []) + [platform]))
            existing.intent_signals = (existing.intent_signals or []) + [signal_data.get('text', '')[:300]]
            existing.intent_signals = existing.intent_signals[:10]  # Keep top 10
            existing.last_active = datetime.utcnow()
            
            # Update scores (weighted average)
            old_count = len(existing.signal_ids or [1])
            new_intent = signal_data.get('intent_score', 0)
            existing.intent_score = ((existing.intent_score * old_count) + new_intent) / (old_count + 1)
            
            # Add verification data
            existing.verification_score = max(
                existing.verification_score or 0,
                signal_data.get('verification_score', 0)
            )
            
            db.commit()
            
            # Route to leads channel
            stream = get_signal_stream()
            stream.publish_signal(
                Signal(
                    id=f"lead_{existing.id}",
                    text=f"Updated lead: {author}",
                    platform='lead_system',
                    url='',
                    author=author,
                    timestamp=datetime.utcnow().isoformat(),
                    query=signal_data.get('query', ''),
                    metadata={
                        'lead_id': existing.id,
                        'action': 'updated',
                        'intent_score': existing.intent_score,
                        'verification_score': existing.verification_score,
                    },
                ),
                channel='leads'
            )
            
            return {
                "action": "updated",
                "lead_id": existing.id,
                "username": author,
                "intent_score": existing.intent_score,
            }
        else:
            # Create new lead
            lead = Lead(
                signal_ids=[signal_data.get('db_id')] if signal_data.get('db_id') else [],
                sources=[platform],
                username=author,
                intent_score=signal_data.get('intent_score', 0),
                intent_category=signal_data.get('intent_category'),
                buying_urgency=signal_data.get('buying_urgency'),
                profile_urls={platform: signal_data.get('url')},
                intent_signals=[signal_data.get('text', '')[:300]],
                status="new",
                verification_score=signal_data.get('verification_score', 0),
                first_seen=datetime.utcnow(),
                last_active=datetime.utcnow(),
            )
            
            db.add(lead)
            db.flush()
            
            # Update signal to mark as lead
            if signal_data.get('db_id'):
                signal_record = db.query(SignalModel).filter(
                    SignalModel.id == signal_data.get('db_id')
                ).first()
                if signal_record:
                    signal_record.is_lead = True
                    signal_record.lead_id = lead.id
            
            db.commit()
            
            # Route to leads channel
            stream = get_signal_stream()
            stream.publish_signal(
                Signal(
                    id=f"lead_{lead.id}",
                    text=f"New verified lead: {author}",
                    platform='lead_system',
                    url='',
                    author=author,
                    timestamp=datetime.utcnow().isoformat(),
                    query=signal_data.get('query', ''),
                    metadata={
                        'lead_id': lead.id,
                        'action': 'created',
                        'intent_score': lead.intent_score,
                        'verification_score': lead.verification_score,
                    },
                ),
                channel='leads'
            )
            
            return {
                "action": "created",
                "lead_id": lead.id,
                "username": author,
                "intent_score": lead.intent_score,
                "verification_score": lead.verification_score,
            }
            
    except Exception as exc:
        db.rollback()
        print(f"[Pipeline] Lead creation error: {exc}")
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


@celery_app.task
def batch_process_signals(signal_data_list: List[Dict]) -> Dict:
    """Process multiple signals in batch"""
    results = []
    
    for signal_data in signal_data_list:
        task = process_signal_stream.delay(signal_data)
        results.append({
            "signal_id": signal_data.get('id'),
            "task_id": task.id,
        })
    
    return {
        "batch_size": len(signal_data_list),
        "tasks_created": len(results),
        "results": results,
    }


@celery_app.task
def consume_signal_stream(duration: int = 60) -> Dict:
    """Consume signals from stream for a duration"""
    import time
    
    print(f"[Pipeline] Starting stream consumer for {duration}s")
    
    stream = get_signal_stream()
    start_time = time.time()
    processed = 0
    rejected = 0
    leads_created = 0
    
    r = stream._get_sync_redis()
    
    while time.time() - start_time < duration:
        try:
            messages = r.xread({f"stream:{stream.CHANNELS['raw']}": '$'}, count=10, block=1000)
            
            for stream_name, msgs in messages:
                for msg_id, data in msgs:
                    signal_data = {k.decode() if isinstance(k, bytes) else k: 
                                  v.decode() if isinstance(v, bytes) else v 
                                  for k, v in data.items()}
                    
                    result = process_signal_stream.delay(signal_data)
                    processed += 1
                    
            # Check results periodically
            # (In production, use callbacks or result polling)
                    
        except Exception as e:
            print(f"[Pipeline] Consumer error: {e}")
            time.sleep(1)
    
    return {
        "duration": duration,
        "signals_processed": processed,
        "status": "completed",
    }


@celery_app.task
def verify_existing_signals(min_verification_score: float = 0.5) -> Dict:
    """
    Re-verify existing unprocessed signals
    Useful for retroactive verification
    """
    db = SessionLocal()
    try:
        # Get unprocessed signals
        signals = db.query(SignalModel).filter(
            SignalModel.is_processed == False
        ).limit(100).all()
        
        verification_service = get_verification_service()
        verified_count = 0
        rejected_count = 0
        
        for signal in signals:
            signal_data = {
                'id': signal.external_id,
                'text': signal.content,
                'author': signal.author,
                'platform': signal.source,
                'posted_at': signal.discovered_at.isoformat() if signal.discovered_at else None,
                'metadata': signal.metadata or {},
            }
            
            verification = verification_service.verify(signal_data)
            
            # Update signal with verification data
            signal.is_processed = True
            signal.metadata = {
                **(signal.metadata or {}),
                'verification_score': verification.verification_score,
                'verification_status': verification.status.value,
                'rejection_reasons': [r.value for r in verification.rejection_reasons],
            }
            
            if verification.is_verified:
                verified_count += 1
                signal.is_lead = True  # Will be processed by lead task
            else:
                rejected_count += 1
                signal.is_lead = False
        
        db.commit()
        
        return {
            "signals_checked": len(signals),
            "verified": verified_count,
            "rejected": rejected_count,
        }
        
    finally:
        db.close()
