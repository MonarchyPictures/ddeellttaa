"""
Signal Pipeline Tasks
Process signals from the stream and convert to leads
"""
from datetime import datetime
from typing import Dict, List

from celery import chain, group

from app.core.celery_config import celery_app
from app.services.signal_stream import get_signal_stream, Signal, get_signal_producer
from app.services.intent_detection import get_intent_service
from app.models.lead import SessionLocal, Signal as SignalModel, Lead


@celery_app.task(bind=True, max_retries=3)
def process_signal_stream(self, signal_data: Dict) -> Dict:
    """
    Process a single signal from the stream
    
    Pipeline:
    1. Intent Detection
    2. Score calculation
    3. Store in DB
    4. If high intent -> Route to leads channel
    5. Create lead if threshold met
    """
    print(f"[Pipeline] Processing signal: {signal_data.get('id')}")
    
    try:
        # Step 1: Intent Detection
        intent_service = get_intent_service()
        text = signal_data.get('text', '')
        query = signal_data.get('query', '')
        
        intent = intent_service.analyze(text, query)
        
        # Step 2: Enrich signal with intent data
        signal_data['intent_score'] = intent.intent_score
        signal_data['intent_category'] = intent.intent_category
        signal_data['buying_urgency'] = intent.buying_urgency
        signal_data['keywords_matched'] = intent.keywords_matched
        signal_data['confidence'] = intent.confidence
        signal_data['processed_at'] = datetime.utcnow().isoformat()
        
        # Step 3: Store in database
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
                    discovered_at=datetime.fromisoformat(signal_data.get('timestamp')),
                    metadata=signal_data.get('metadata', {}),
                    is_processed=True,
                    is_lead=intent.intent_score >= 0.5,
                )
                db.add(signal_record)
                db.commit()
                
                signal_data['db_id'] = signal_record.id
            else:
                signal_data['db_id'] = existing.id
                signal_data['duplicate'] = True
                
        finally:
            db.close()
        
        # Step 4: Route to appropriate channel
        stream = get_signal_stream()
        
        if intent.intent_score >= 0.6:
            # High intent - route to leads channel
            stream.publish_signal(
                Signal(
                    id=signal_data.get('id'),
                    text=text,
                    platform=signal_data.get('platform'),
                    url=signal_data.get('url'),
                    author=signal_data.get('author'),
                    timestamp=signal_data.get('timestamp'),
                    query=query,
                    metadata=signal_data,
                ),
                channel='high_intent'
            )
            
            # Trigger lead creation
            create_lead_from_signal.delay(signal_data)
        
        return {
            "signal_id": signal_data.get('id'),
            "intent_score": intent.intent_score,
            "intent_category": intent.intent_category,
            "is_high_intent": intent.intent_score >= 0.6,
            "status": "processed",
        }
        
    except Exception as exc:
        print(f"[Pipeline] Processing error: {exc}")
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=2)
def create_lead_from_signal(self, signal_data: Dict) -> Dict:
    """
    Create or update a lead from a high-intent signal
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
            
            # Recalculate score
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
                    metadata={'lead_id': existing.id, 'action': 'updated'},
                ),
                channel='leads'
            )
            
            return {
                "action": "updated",
                "lead_id": existing.id,
                "username": author,
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
                verification_score=0.3,
                first_seen=datetime.utcnow(),
                last_active=datetime.utcnow(),
            )
            
            db.add(lead)
            db.commit()
            
            # Route to leads channel
            stream = get_signal_stream()
            stream.publish_signal(
                Signal(
                    id=f"lead_{lead.id}",
                    text=f"New lead: {author}",
                    platform='lead_system',
                    url='',
                    author=author,
                    timestamp=datetime.utcnow().isoformat(),
                    query=signal_data.get('query', ''),
                    metadata={'lead_id': lead.id, 'action': 'created'},
                ),
                channel='leads'
            )
            
            return {
                "action": "created",
                "lead_id": lead.id,
                "username": author,
            }
            
    except Exception as exc:
        db.rollback()
        print(f"[Pipeline] Lead creation error: {exc}")
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


@celery_app.task
def batch_process_signals(signal_data_list: List[Dict]) -> Dict:
    """
    Process multiple signals in batch
    """
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
    """
    Consume signals from stream for a duration (in seconds)
    
    This is a long-running task that consumes from Redis Pub/Sub
    """
    import time
    
    print(f"[Pipeline] Starting stream consumer for {duration}s")
    
    stream = get_signal_stream()
    start_time = time.time()
    processed = 0
    
    # This is a simplified version - in production use async consumer
    # For Celery, we'll poll the Redis stream
    r = stream._get_sync_redis()
    
    while time.time() - start_time < duration:
        try:
            # Read from stream (non-blocking)
            messages = r.xread({f"stream:{stream.CHANNELS['raw']}": '$'}, count=10, block=1000)
            
            for stream_name, msgs in messages:
                for msg_id, data in msgs:
                    # Convert bytes to dict
                    signal_data = {k.decode() if isinstance(k, bytes) else k: 
                                  v.decode() if isinstance(v, bytes) else v 
                                  for k, v in data.items()}
                    
                    # Process signal
                    process_signal_stream.delay(signal_data)
                    processed += 1
                    
        except Exception as e:
            print(f"[Pipeline] Consumer error: {e}")
            time.sleep(1)
    
    return {
        "duration": duration,
        "signals_processed": processed,
        "status": "completed",
    }
