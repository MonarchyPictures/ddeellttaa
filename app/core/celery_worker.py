"""
Celery Worker Tasks - Production Only

Pure Celery tasks. No SQLite fallback. No sync execution.
Redis is REQUIRED.
"""
import os
import sys
import logging
import hashlib
import uuid
import asyncio
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.database import SessionLocal
from app.db import models
from app.core.celery_app import celery
from app.services.agent_scheduler import (
    get_agents_due_for_execution,
    mark_agent_running,
    complete_agent_execution,
    deactivate_expired_agents,
    should_execute_agent
)
from app.services.parallel_scraper_runner import run_scrapers_parallel
from app.scrapers.registry import SCRAPER_REGISTRY
from app.core.cache import get_cached, set_cached

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@celery.task(name="ingest_leads_task")
def ingest_leads_task(raw_results: list):
    """Process raw scraper results -> Validation -> DB."""
    from app.services.ingestion_service import ingest_leads
    
    logger.info(f"Queue: Received {len(raw_results)} items for ingestion")
    try:
        leads = ingest_leads(raw_results)
        return [l.id for l in leads if l.id]
    except Exception as e:
        logger.error(f"Ingestion Task Failed: {e}")
        return []


@celery.task(name="specialops_mission_task")
def specialops_mission_task(query: str, location: str = "Kenya", agent_id: str = None):
    """MASTER AGENT MISSION: Autonomous web intelligence routing.
    SIMPLIFIED: Scraper → Score → Save (no LeadValidator, no raw lead storage)
    """
    from app.core.specialops import SpecialOpsAgent
    from app.services.kenya_high_recall_pipeline import calculate_kenyan_intent_score
    from app.nlp.duplicate_detector import DuplicateDetector
    
    agent_ops = SpecialOpsAgent()
    detector = DuplicateDetector()
    
    logger.info(f"Starting SpecialOps Mission: {query} in {location}")
    
    try:
        mission_results = agent_ops.execute_mission(query, location)
    except Exception as e:
        logger.error(f"SpecialOps Mission Failed: {e}")
        return f"Mission error: {e}"
    
    db = SessionLocal()
    processed_count = 0
    
    try:
        recent_leads = db.query(models.Lead).filter(
            models.Lead.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
        ).all()
        recent_texts = [l.buyer_request_snippet for l in recent_leads if l.buyer_request_snippet]

        logger.info(f"SpecialOps Mission found {len(mission_results)} potential results")
        
        for result in mission_results:
            try:
                text = result.get("body") or result.get("text") or ""
                url = result.get("href") or result.get("url")
                
                if not text or not url:
                    continue
                
                # SIMPLE PIPELINE: Score directly with high-recall pipeline
                intent_score = calculate_kenyan_intent_score(text)
                
                # Threshold check (0.25 for high recall)
                if intent_score < 0.25:
                    logger.debug(f"Rejected (score {intent_score:.2f}): {url}")
                    continue
                
                # Determine badge
                if intent_score >= 0.7:
                    badge = "HOT"
                elif intent_score >= 0.5:
                    badge = "WARM"
                else:
                    badge = "COLD"
                
                # Extract phone
                import re
                phone_match = re.search(r'(\+?254\d{9}|0\d{9})', text)
                phone = phone_match.group(0) if phone_match else None
                
                # Deduplication check
                if text[:200] in recent_texts:
                    logger.debug(f"Duplicate: {url}")
                    continue
                
                # Create lead directly (no normalization step)
                lead = models.Lead(
                    id=uuid.uuid4(),
                    source_platform=result.get("source", "specialops"),
                    source_url=url,
                    buyer_request_snippet=text[:500],
                    title=text[:200],
                    product_category="general",
                    buyer_name="Anonymous",
                    intent_score=intent_score,
                    confidence_score=round(intent_score * 100, 2),
                    badge=badge,
                    is_hot_lead=1 if intent_score > 0.8 else 0,
                    contact_phone=phone,
                    contact_flag="ok" if phone else "missing",
                    status=models.CRMStatus.NEW,
                    created_at=datetime.now(timezone.utc)
                )
                
                # Check for URL duplicate
                existing = db.query(models.Lead).filter(models.Lead.source_url == url).first()
                if not existing:
                    db.add(lead)
                    processed_count += 1
                    recent_texts.append(text[:200])
                    logger.info(f"✅ Saved lead from {url} (score: {intent_score:.2f})")
                
            except Exception as e:
                logger.error(f"Error processing SpecialOps lead: {e}")
                continue
                
        db.commit()
        logger.info(f"SpecialOps Mission Complete: Found {processed_count} leads.")
        return f"Processed {processed_count} leads via SpecialOps"
        
    except Exception as e:
        logger.error(f"Error in SpecialOps task: {e}")
        return f"Error: {e}"
    finally:
        db.close()


@celery.task(bind=True, max_retries=5, name="scrape_source_task")
def scrape_source_task(self, source_name: str, query: str, location: str = "Kenya"):
    """Self-Healing Scraper Task with Circuit Breaker."""
    import asyncio
    from app.scrapers.registry import SCRAPER_REGISTRY
    import redis
    
    FAILURE_THRESHOLD = 3
    COOLDOWN_SECONDS = 300
    
    REDIS_URL = os.getenv("REDIS_URL")
    if not REDIS_URL:
        raise RuntimeError("REDIS_URL not set for circuit breaker")
    
    r = redis.from_url(REDIS_URL)
    failure_key = f"scraper_failures:{source_name}"
    disabled_key = f"scraper_disabled:{source_name}"
    
    if r.exists(disabled_key):
        ttl = r.ttl(disabled_key)
        logger.warning(f"Source '{source_name}' is DISABLED. Cooldown active for {ttl}s.")
        return []

    scraper = SCRAPER_REGISTRY.get(source_name)
    if not scraper:
        logger.error(f"Scraper '{source_name}' not found in registry.")
        return []

    logger.info(f"Scraping Source: {source_name} for '{query}'")

    try:
        results = asyncio.run(scraper.search(query, location))
        r.delete(failure_key)
        return results

    except Exception as exc:
        logger.error(f"Scraper '{source_name}' Failed: {exc}")
        failures = r.incr(failure_key)
        
        if failures >= FAILURE_THRESHOLD:
            r.setex(disabled_key, COOLDOWN_SECONDS, "1")
            r.delete(failure_key)
            logger.critical(f"Source '{source_name}' DISABLED for {COOLDOWN_SECONDS}s due to {failures} failures.")
            return []
        
        retry_delay = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=retry_delay)


@celery.task(name="run_all_agents")
def run_all_agents():
    """
    Trigger agents that are due for execution.
    Database is the SINGLE SOURCE OF TRUTH for scheduling.
    
    Beat runs this every minute. DB controls execution timing.
    """
    db = SessionLocal()
    try:
        # Step 1: Deactivate expired agents
        deactivated = deactivate_expired_agents(db)
        if deactivated > 0:
            logger.info(f"Deactivated {deactivated} expired agents")
        
        # Step 2: Query DB for agents due to run (DB = source of truth)
        due_agents = get_agents_due_for_execution(db)
        
        if not due_agents:
            logger.debug("No agents due for execution")
            return "No agents due"
        
        # Step 3: Trigger each due agent
        triggered_count = 0
        for agent in due_agents:
            # Double-check with scheduler logic (race condition protection)
            if not should_execute_agent(agent):
                logger.debug(f"Agent {agent.id} skipped by scheduler check")
                continue
            
            # Mark as running to prevent duplicate execution
            if not mark_agent_running(db, agent):
                logger.warning(f"Could not mark agent {agent.id} as running (race condition)")
                continue
            
            # Queue the task
            logger.info(f"Triggering agent '{agent.name}' (ID: {agent.id})")
            run_agent_task.delay(str(agent.id))
            triggered_count += 1
        
        logger.info(f"Triggered {triggered_count}/{len(due_agents)} due agents")
        return f"Triggered {triggered_count} agents"
        
    except Exception as e:
        logger.error(f"Error in run_all_agents: {e}")
        return f"Error: {e}"
    finally:
        db.close()


@celery.task(name="scrape_platform_task")
def scrape_platform_task(platform: str, query: str, location: str = "Kenya", 
                         agent_id: str = None, radius: int = 50, 
                         min_intent: float = 0.25, tier: int = 2, timeout: int = 15):
    """Background task to scrape a platform and save leads.
    
    SIMPLIFIED PIPELINE: Scraper → Score → Save Lead
    No LeadValidator, no AgentRawLead, no complex ranking engines.
    """
    from app.scrapers.registry import SCRAPER_REGISTRY
    from app.services.kenya_high_recall_pipeline import calculate_kenyan_intent_score
    
    # Scrape using registry
    raw_results = []
    try:
        PLATFORM_ALIASES = {
            "google": "serpapi",
            "tiktok": "twitter",
            "reddit": "twitter",
            "facebook": "facebook_groups",
        }
        
        platform_key = platform.lower()
        lookup_key = PLATFORM_ALIASES.get(platform_key, platform_key)
        
        scraper = SCRAPER_REGISTRY.get(lookup_key)
        if scraper:
            logger.info(f"Using scraper '{lookup_key}' (requested: '{platform}') for query '{query}'")
            raw_results = scraper.scrape(query, time_window_hours=24)
        else:
            logger.warning(f"No scraper found for platform: {platform} (looked up: {lookup_key})")
    except Exception as e:
        logger.error(f"Scraper failed for {platform}: {e}")
    
    db = SessionLocal()
    processed_count = 0
    
    try:
        agent = None
        if agent_id:
            if isinstance(agent_id, str):
                agent_id = uuid.UUID(agent_id)
            agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()

        # Get recent leads for deduplication
        recent_leads = db.query(models.Lead).filter(
            models.Lead.created_at >= datetime.now() - timedelta(hours=24)
        ).all()
        recent_urls = {l.source_url for l in recent_leads if l.source_url}
        recent_texts = {l.buyer_request_snippet[:100] for l in recent_leads if l.buyer_request_snippet}

        for raw in raw_results:
            try:
                # Extract text and URL
                text = raw.get("body") or raw.get("text") or raw.get("snippet", "")
                url = raw.get("href") or raw.get("url") or raw.get("source_url", "")
                
                if not text or not url:
                    continue
                
                # SIMPLE PIPELINE: Score directly
                intent_score = calculate_kenyan_intent_score(text)
                
                # Threshold check
                if intent_score < min_intent:
                    continue
                
                # Determine badge
                if intent_score >= 0.7:
                    badge = "HOT"
                elif intent_score >= 0.5:
                    badge = "WARM"
                else:
                    badge = "COLD"
                
                # Deduplication checks
                if url in recent_urls:
                    continue
                if text[:100] in recent_texts:
                    continue
                
                # Extract phone
                import re
                phone_match = re.search(r'(\+?254\d{9}|0\d{9})', text)
                phone = phone_match.group(0) if phone_match else None
                
                # Create lead directly
                lead = models.Lead(
                    id=uuid.uuid4(),
                    agent_id=agent.id if agent else None,
                    source_platform=raw.get("source", platform.capitalize()),
                    source_url=url,
                    title=text[:200],
                    buyer_request_snippet=text[:500],
                    product_category="general",
                    buyer_name="Anonymous",
                    contact_phone=phone,
                    contact_flag="ok" if phone else "missing",
                    intent_score=intent_score,
                    confidence_score=round(intent_score * 100, 2),
                    ranked_score=round(intent_score, 2),
                    badge=badge,
                    is_hot_lead=1 if intent_score > 0.8 else 0,
                    status=models.CRMStatus.NEW,
                    created_at=datetime.now(timezone.utc)
                )
                
                db.add(lead)
                recent_urls.add(url)
                recent_texts.add(text[:100])
                processed_count += 1
                
                # Create agent-lead link if applicable
                if agent:
                    agent_lead = models.AgentLead(
                        agent_id=agent.id,
                        lead_id=lead.id
                    )
                    db.add(agent_lead)
                    
            except Exception as e:
                logger.error(f"Error processing lead from {platform}: {e}")
                continue

        db.commit()
        logger.info(f"Processed {processed_count} leads from {platform}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving leads from {platform}: {e}")
        return f"Error saving leads: {e}"
    finally:
        db.close()
        
    return f"Processed {processed_count} leads from {platform} in {location}"


@celery.task(name="run_agent_task")
def run_agent_task(agent_id: str):
    """
    Run discovery for a single agent with parallel scraping.
    Uses scheduler for reliable execution tracking.
    """
    db = SessionLocal()
    success = False
    error_msg = None
    
    try:
        if isinstance(agent_id, str):
            agent_id = uuid.UUID(agent_id)
        agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
        
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return f"Agent {agent_id} not found"
        
        logger.info(f"EXECUTING Agent '{agent.name}' (ID: {agent.id})")
        
        # Check cache first
        cached_results = get_cached(agent.query, agent.location or "Kenya")
        if cached_results:
            logger.info(f"⚡ Cache HIT for agent '{agent.name}' query '{agent.query}'")
            # Still process cached results through ingestion
            if cached_results:
                ingest_leads_task.delay(cached_results)
            success = True
            return f"Agent {agent.name}: {len(cached_results)} cached results (skipped scraping)"
        
        # Get platforms from registry
        from app.core.agent_scraper_resolver import get_available_scrapers
        requested_platforms = getattr(agent, "platforms", None)
        platform_names = get_available_scrapers(requested_platforms)
        
        if not platform_names:
            error_msg = "No scrapers available"
            logger.error(f"Agent {agent_id}: {error_msg}")
            return f"Error: {error_msg}"
        
        logger.info(f"Agent {agent_id}: Using platforms {platform_names}")
        
        # Build scraper instances
        scraper_instances = []
        for platform in platform_names:
            if platform in SCRAPER_REGISTRY:
                scraper_instances.append(SCRAPER_REGISTRY[platform])
            else:
                logger.warning(f"Platform '{platform}' not in registry")
        
        if not scraper_instances:
            error_msg = "No scraper instances available"
            logger.error(f"Agent {agent_id}: {error_msg}")
            return f"Error: {error_msg}"
        
        # Run scrapers in parallel with controlled concurrency
        try:
            logger.info(f"Agent {agent_id}: Running {len(scraper_instances)} scrapers in parallel")
            
            # Use asyncio.run() - safe in Celery worker (sync context)
            raw_results = asyncio.run(
                run_scrapers_parallel(
                    scrapers=scraper_instances,
                    query=agent.query,
                    location=agent.location or "Kenya"
                )
            )
            
            logger.info(f"Agent {agent_id}: Scraping complete. {len(raw_results)} total results")
            
            # Cache results for future queries
            if raw_results:
                set_cached(agent.query, raw_results, agent.location or "Kenya")
                # Queue leads for ingestion
                ingest_leads_task.delay(raw_results)
            
            success = True
            return f"Agent {agent.name}: {len(raw_results)} results from {len(scraper_instances)} platforms"
            
        except Exception as scrape_e:
            error_msg = f"Scraping failed: {str(scrape_e)}"
            logger.error(f"Agent {agent_id}: {error_msg}")
            return f"Error: {error_msg}"
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"CRITICAL: Agent {agent_id} execution failed: {e}")
        db.rollback()
        return f"Error: {error_msg}"
    finally:
        # Mark execution complete in scheduler (updates next_run_at)
        complete_agent_execution(db, str(agent_id), success=success, error_message=error_msg)
        db.close()


@celery.task(name="cleanup_old_leads")
def cleanup_old_leads():
    """Remove leads older than 4 days to maintain freshness."""
    db = SessionLocal()
    try:
        four_days_ago = datetime.now() - timedelta(days=4)
        deleted = db.query(models.Lead).filter(models.Lead.created_at < four_days_ago).delete()
        db.commit()
        logger.info(f"Cleaned up {deleted} old leads.")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
    finally:
        db.close()


@celery.task(name="update_lead_availability")
def update_lead_availability():
    """Update availability status based on time passed."""
    db = SessionLocal()
    try:
        forty_eight_hours_ago = datetime.now() - timedelta(hours=48)
        db.query(models.Lead).filter(
            models.Lead.created_at < forty_eight_hours_ago,
            models.Lead.availability_status == "Available Now"
        ).update({"availability_status": "Likely Closed"})
        
        db.commit()
    except Exception as e:
        logger.error(f"Update availability failed: {e}")
    finally:
        db.close()


__all__ = [
    'celery_app',
    'ingest_leads_task',
    'specialops_mission_task',
    'scrape_source_task',
    'run_all_agents',
    'scrape_platform_task',
    'run_agent_task',
    'cleanup_old_leads',
    'update_lead_availability',
]
