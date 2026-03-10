"""
Celery Tasks for Scraper Workers
Distributed scraping with Redis task queue
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from celery import chain, group, chord

from app.core.celery_config import celery_app
from app.services.query_expansion import get_expansion_service
from app.services.intent_detection import get_intent_service
from app.services.lead_verification import get_verification_service
from app.scrapers.reddit_scraper import RedditScraper
from app.scrapers.twitter_scraper import TwitterScraper
from app.scrapers.forum_scraper import ForumScraper
from app.models.lead import SessionLocal, Signal, Lead, SearchQuery


@celery_app.task(bind=True, max_retries=3)
def scrape_reddit(self, query: str, search_query_id: Optional[int] = None) -> Dict:
    """
    Celery task to scrape Reddit
    
    Args:
        query: Search query
        search_query_id: Optional database ID for tracking
        
    Returns:
        Dict with scraped signals
    """
    print(f"[Worker] Scraping Reddit for: {query}")
    
    try:
        # Run async scraper in sync context
        scraper = RedditScraper()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(scraper.search(query, limit=25))
        finally:
            loop.run_until_complete(scraper.close())
            loop.close()
        
        # Process results
        signals = []
        intent_service = get_intent_service()
        
        for result in results:
            # Analyze intent
            full_text = f"{result.title} {result.content}"
            intent = intent_service.analyze(full_text, query)
            
            signal_data = {
                "external_id": result.external_id,
                "source": "reddit",
                "title": result.title,
                "content": result.content[:1000],
                "raw_content": result.content,
                "author": result.author,
                "source_url": result.url,
                "query_matched": query,
                "subreddit": result.subreddit,
                "posted_at": result.posted_at.isoformat() if result.posted_at else None,
                "intent_score": intent.intent_score,
                "intent_category": intent.intent_category,
                "buying_urgency": intent.buying_urgency,
                "keywords_matched": intent.keywords_matched,
                "discovered_at": datetime.utcnow().isoformat(),
                "metadata": result.metadata or {},
                "is_processed": False,
                "is_lead": intent.intent_score >= 0.5,
            }
            signals.append(signal_data)
        
        # Store in database
        db = SessionLocal()
        try:
            for signal_data in signals:
                # Check for duplicates
                existing = db.query(Signal).filter(
                    Signal.external_id == signal_data["external_id"]
                ).first()
                
                if not existing:
                    signal = Signal(**signal_data)
                    db.add(signal)
            
            db.commit()
        finally:
            db.close()
        
        return {
            "task_id": self.request.id,
            "source": "reddit",
            "query": query,
            "signals_found": len(signals),
            "high_intent_signals": len([s for s in signals if s["intent_score"] >= 0.5]),
            "status": "completed",
        }
        
    except Exception as exc:
        print(f"[Worker] Reddit scrape failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def scrape_twitter(self, query: str, search_query_id: Optional[int] = None) -> Dict:
    """Celery task to scrape Twitter"""
    print(f"[Worker] Scraping Twitter for: {query}")
    
    try:
        scraper = TwitterScraper()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(scraper.search(query, limit=20))
        finally:
            loop.run_until_complete(scraper.close())
            loop.close()
        
        signals = []
        intent_service = get_intent_service()
        
        for result in results:
            full_text = f"{result.title} {result.content}"
            intent = intent_service.analyze(full_text, query)
            
            signal_data = {
                "external_id": result.external_id,
                "source": "twitter",
                "title": result.title,
                "content": result.content[:1000],
                "raw_content": result.content,
                "author": result.author,
                "source_url": result.url,
                "query_matched": query,
                "posted_at": result.posted_at.isoformat() if result.posted_at else None,
                "intent_score": intent.intent_score,
                "intent_category": intent.intent_category,
                "buying_urgency": intent.buying_urgency,
                "keywords_matched": intent.keywords_matched,
                "discovered_at": datetime.utcnow().isoformat(),
                "metadata": result.metadata or {},
                "is_processed": False,
                "is_lead": intent.intent_score >= 0.5,
            }
            signals.append(signal_data)
        
        # Store in database
        db = SessionLocal()
        try:
            for signal_data in signals:
                existing = db.query(Signal).filter(
                    Signal.external_id == signal_data["external_id"]
                ).first()
                
                if not existing:
                    signal = Signal(**signal_data)
                    db.add(signal)
            
            db.commit()
        finally:
            db.close()
        
        return {
            "task_id": self.request.id,
            "source": "twitter",
            "query": query,
            "signals_found": len(signals),
            "high_intent_signals": len([s for s in signals if s["intent_score"] >= 0.5]),
            "status": "completed",
        }
        
    except Exception as exc:
        print(f"[Worker] Twitter scrape failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def scrape_forum(self, query: str, search_query_id: Optional[int] = None) -> Dict:
    """Celery task to scrape Forums"""
    print(f"[Worker] Scraping Forums for: {query}")
    
    try:
        scraper = ForumScraper()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(scraper.search(query, limit=15))
        finally:
            loop.run_until_complete(scraper.close())
            loop.close()
        
        signals = []
        intent_service = get_intent_service()
        
        for result in results:
            full_text = f"{result.title} {result.content}"
            intent = intent_service.analyze(full_text, query)
            
            signal_data = {
                "external_id": result.external_id,
                "source": "forum",
                "title": result.title,
                "content": result.content[:1000],
                "raw_content": result.content,
                "author": result.author,
                "source_url": result.url,
                "query_matched": query,
                "subreddit": result.subreddit,  # Used as forum name
                "posted_at": result.posted_at.isoformat() if result.posted_at else None,
                "intent_score": intent.intent_score,
                "intent_category": intent.intent_category,
                "buying_urgency": intent.buying_urgency,
                "keywords_matched": intent.keywords_matched,
                "discovered_at": datetime.utcnow().isoformat(),
                "metadata": result.metadata or {},
                "is_processed": False,
                "is_lead": intent.intent_score >= 0.5,
            }
            signals.append(signal_data)
        
        # Store in database
        db = SessionLocal()
        try:
            for signal_data in signals:
                existing = db.query(Signal).filter(
                    Signal.external_id == signal_data["external_id"]
                ).first()
                
                if not existing:
                    signal = Signal(**signal_data)
                    db.add(signal)
            
            db.commit()
        finally:
            db.close()
        
        return {
            "task_id": self.request.id,
            "source": "forum",
            "query": query,
            "signals_found": len(signals),
            "high_intent_signals": len([s for s in signals if s["intent_score"] >= 0.5]),
            "status": "completed",
        }
        
    except Exception as exc:
        print(f"[Worker] Forum scrape failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task
def scrape_all_sources(query: str, expand: bool = True) -> Dict:
    """
    Launch parallel scraper tasks for all sources
    
    This uses Celery's group to run all scrapers in parallel
    """
    print(f"[Worker] Launching parallel scrape for: {query}")
    
    # Expand query if enabled
    if expand:
        expansion_service = get_expansion_service()
        expanded = expansion_service.expand(query, limit=3)
        queries = expanded[:3]
    else:
        queries = [query]
    
    results = {
        "query": query,
        "expanded_queries": queries,
        "tasks": [],
    }
    
    # Create parallel task groups for each query
    for q in queries:
        # Create a group of tasks to run in parallel
        job = group(
            scrape_reddit.s(q),
            scrape_twitter.s(q),
            scrape_forum.s(q),
        )
        
        # Execute the group
        result = job.apply_async()
        
        results["tasks"].append({
            "query": q,
            "group_id": result.id,
            "task_ids": [r.id for r in result.results],
        })
    
    return results


@celery_app.task
def process_signal(signal_id: int) -> Dict:
    """
    Process a single signal to create/update lead
    
    This is called after signals are scraped
    """
    db = SessionLocal()
    try:
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if not signal:
            return {"error": "Signal not found"}
        
        # Check if author already has a lead
        existing_lead = db.query(Lead).filter(
            Lead.username == signal.author
        ).first()
        
        if existing_lead:
            # Update existing lead
            existing_lead.signal_ids = existing_lead.signal_ids or []
            if signal.id not in existing_lead.signal_ids:
                existing_lead.signal_ids.append(signal.id)
            
            existing_lead.sources = list(set(
                (existing_lead.sources or []) + [signal.source]
            ))
            
            # Recalculate scores
            signals_for_author = db.query(Signal).filter(
                Signal.author == signal.author
            ).all()
            
            avg_intent = sum(s.intent_score for s in signals_for_author) / len(signals_for_author)
            existing_lead.intent_score = avg_intent
            
            signal.is_processed = True
            signal.lead_id = existing_lead.id
            db.commit()
            
            return {
                "action": "updated",
                "lead_id": existing_lead.id,
                "signal_id": signal_id,
            }
        else:
            # Create new lead
            lead = Lead(
                signal_ids=[signal.id],
                sources=[signal.source],
                username=signal.author,
                intent_score=signal.intent_score,
                intent_category=signal.intent_category,
                buying_urgency=signal.buying_urgency,
                profile_urls={signal.source: signal.source_url},
                intent_signals=[signal.content[:300]],
                status="new",
                verification_score=0.3,  # Initial score
            )
            
            db.add(lead)
            db.flush()  # Get lead.id
            
            signal.is_processed = True
            signal.lead_id = lead.id
            signal.is_lead = True
            
            db.commit()
            
            return {
                "action": "created",
                "lead_id": lead.id,
                "signal_id": signal_id,
            }
    finally:
        db.close()


@celery_app.task
def search_and_process(query: str, expand: bool = True) -> Dict:
    """
    Complete search workflow:
    1. Scrape all sources in parallel
    2. Process high-intent signals into leads
    3. Return results
    """
    print(f"[Worker] Full workflow for: {query}")
    
    # Step 1: Scrape all sources
    scrape_result = scrape_all_sources(query, expand)
    
    # Wait for scrape tasks to complete (in production, use callback)
    # For now, return the task IDs for polling
    
    return {
        "workflow": "search_and_process",
        "query": query,
        "scrape_tasks": scrape_result,
        "status": "initiated",
        "message": "Scraping tasks launched. Check /api/tasks/status for progress.",
    }
