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
    """MASTER AGENT MISSION: Autonomous web intelligence routing."""
    from app.core.specialops import SpecialOpsAgent
    from app.utils.normalization import LeadValidator
    from app.nlp.duplicate_detector import DuplicateDetector
    from app.services.market_classifier import is_valid_buyer, calculate_kenyan_intent_score
    
    agent_ops = SpecialOpsAgent()
    validator = LeadValidator()
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
            models.Lead.request_timestamp >= datetime.now(timezone.utc) - timedelta(hours=24)
        ).all()
        recent_texts = [l.buyer_request_snippet for l in recent_leads if l.buyer_request_snippet]

        logger.info(f"SpecialOps Mission found {len(mission_results)} potential results")
        
        for result in mission_results:
            try:
                raw = {
                    "source": result.get("source", "specialops"),
                    "link": result.get("href") or result.get("url"),
                    "text": result.get("body") or result.get("text") or result.get("data", {}).get("raw_text", ""),
                    "title": result.get("title") or result.get("data", {}).get("title", ""),
                    "location": location
                }
                
                if not is_valid_buyer(raw['text'], raw['link']):
                    logger.info(f"SpecialOps Lead REJECTED (Strict Filter): {raw['link']}")
                    continue

                intent_points, details = calculate_kenyan_intent_score(raw['text'])
                if intent_points < 50:
                    logger.info(f"SpecialOps Lead REJECTED (Score {intent_points} < 50): {raw['link']}")
                    continue
                
                logger.info(f"Normalizing lead from {raw['source']}: {raw['text'][:50]}...")
                normalized = validator.normalize_lead(raw, db=db)
                if not normalized:
                    logger.info(f"Lead rejected by normalization")
                    continue
                
                snippet = normalized.get("buyer_request_snippet", "")
                if snippet and detector.is_duplicate(snippet, recent_texts):
                    continue

                lead = models.Lead(
                    id=normalized["id"],
                    source_platform=normalized["source_platform"],
                    post_link=normalized["post_link"],
                    timestamp=normalized.get("timestamp", datetime.now()),
                    location_raw=normalized.get("location_raw"),
                    property_country="Kenya",
                    latitude=normalized.get("latitude"),
                    longitude=normalized.get("longitude"),
                    buyer_request_snippet=normalized["buyer_request_snippet"],
                    product_category=normalized["product_category"],
                    buyer_name=normalized.get("buyer_name", "Anonymous"),
                    intent_score=normalized["intent_score"],
                    confidence_score=normalized["confidence_score"],
                    readiness_level=normalized.get("readiness_level"),
                    urgency_score=normalized.get("urgency_score"),
                    budget_info=normalized.get("budget_info"),
                    product_specs=normalized.get("product_specs"),
                    deal_probability=normalized.get("deal_probability"),
                    intent_type=normalized.get("intent_type", "BUYER"),
                    is_hot_lead=1 if result.get("is_hot_lead") else 0,
                    whatsapp_ready_data=result.get("whatsapp_ready"),
                    is_contact_verified=normalized.get("is_contact_verified", 0),
                    contact_phone=normalized.get("contact_phone"),
                    contact_email=normalized.get("contact_email"),
                    contact_flag=normalized.get("contact_flag", "ok"),
                    contact_reliability_score=normalized.get("contact_reliability_score", 0.0),
                    preferred_contact_method=normalized.get("preferred_contact_method")
                )
                
                db.merge(lead)
                processed_count += 1
                if snippet:
                    recent_texts.append(snippet)
                
            except Exception as e:
                logger.error(f"Error processing SpecialOps lead: {e}")
                continue
                
        db.commit()
        logger.info(f"SpecialOps Mission Complete: Found {processed_count} high-confidence leads.")
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
                         min_intent: float = 0.7, tier: int = 2, timeout: int = 15):
    """Background task to scrape a platform and save leads."""
    from app.scrapers.registry import SCRAPER_REGISTRY
    from app.utils.normalization import LeadValidator
    from app.intelligence.ranking import RankingEngine
    from app.nlp.duplicate_detector import DuplicateDetector
    from app.utils.outreach import OutreachEngine
    from app.core.compliance import ComplianceManager
    
    validator = LeadValidator()
    ranking_engine = RankingEngine()
    outreach_engine = OutreachEngine()
    detector = DuplicateDetector()
    compliance = ComplianceManager()
    
    # Platform Compliance (Throttling)
    try:
        compliance.wait_for_rate_limit(platform.lower())
    except Exception as e:
        logger.error(f"Compliance check failed for {platform}: {e}")
    
    # Scrape using registry
    raw_results = []
    try:
        scraper = SCRAPER_REGISTRY.get(platform.lower())
        if scraper:
            logger.info(f"Using scraper '{platform}' for query '{query}'")
            raw_results = scraper.scrape(query, time_window_hours=24)
        else:
            logger.warning(f"No scraper found for platform: {platform}")
    except Exception as e:
        logger.error(f"Scraper failed for {platform}: {e}")
    
    db = SessionLocal()
    processed_count = 0
    alert_count = 0
    high_value_leads = []
    
    try:
        agent = None
        if agent_id:
            if isinstance(agent_id, str):
                agent_id = uuid.UUID(agent_id)
            agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()

        recent_leads = db.query(models.Lead).filter(
            models.Lead.created_at >= datetime.now() - timedelta(hours=24)
        ).all()
        recent_texts = [l.buyer_request_snippet for l in recent_leads]

        for raw in raw_results:
            try:
                if "source" not in raw:
                    raw["source"] = platform.capitalize()
                
                # Save raw lead
                raw_lead = None
                try:
                    raw_text = raw.get("body") or raw.get("text") or raw.get("data", {}).get("raw_text", "") or "N/A"
                    phone = raw.get("phone") or raw.get("contact", {}).get("phone")
                    content_hash = hashlib.md5(raw_text.strip().lower().encode('utf-8')).hexdigest()
                    
                    is_duplicate = False
                    if agent_id:
                        existing_hash = db.query(models.AgentRawLead).filter(
                            models.AgentRawLead.agent_id == agent_id,
                            models.AgentRawLead.content_hash == content_hash
                        ).first()
                        
                        if existing_hash:
                            is_duplicate = True
                            logger.info(f"Duplicate signal (hash) for agent {agent_id}. Skipping storage.")
                        elif phone and len(str(phone)) > 5:
                            existing_phone = db.query(models.AgentRawLead).filter(
                                models.AgentRawLead.agent_id == agent_id,
                                models.AgentRawLead.phone == str(phone)
                            ).first()
                            if existing_phone:
                                is_duplicate = True
                                logger.info(f"Duplicate signal (phone) for agent {agent_id}. Skipping storage.")
                    
                    if is_duplicate:
                        continue

                    raw_lead = models.AgentRawLead(
                        agent_id=agent_id,
                        raw_text=raw_text,
                        content_hash=content_hash,
                        phone=phone,
                        source=raw["source"],
                        source_url=raw.get("href") or raw.get("url") or raw.get("post_link"),
                        processed=0
                    )
                    db.add(raw_lead)
                    db.commit()
                    db.refresh(raw_lead)
                except Exception as raw_e:
                    logger.error(f"Failed to save AgentRawLead: {raw_e}")
                    
                normalized = validator.normalize_lead(raw, db=db)
                if not normalized:
                    logger.info(f"Skipping empty normalization for lead from {platform}")
                    continue
                
                # Update Raw Lead with analysis data
                if raw_lead:
                    raw_lead.geo_score = normalized.get("geo_score", 0.0)
                    raw_lead.intent_score = normalized.get("intent_score", 0.0)
                    raw_lead.confidence_score = normalized.get("confidence_score", 0.0)
                    raw_lead.processed = 1
                
                # Ranking
                ranked_score = ranking_engine.calculate_score(normalized)
                priority_class = ranking_engine.classify_lead(ranked_score)
                
                if raw_lead:
                    raw_lead.ranked_score = ranked_score
                    db.add(raw_lead)
                
                logger.info(f"Lead Ranked: Score={ranked_score}, Class={priority_class}")

                if normalized.get("intent_score", 0) < min_intent:
                    logger.info(f"Signal recorded with low intent score: {normalized.get('intent_score')} < {min_intent}")

                # Duplicate Detection
                if detector.is_duplicate(normalized["buyer_request_snippet"], recent_texts):
                    logger.info(f"Skipping duplicate lead from {platform}")
                    continue

                # Check for history of non-response
                has_bad_history = outreach_engine.check_non_response_history(
                    db, 
                    phone=normalized.get("contact_phone"), 
                    email=normalized.get("contact_email")
                )

                # Create lead record
                lead = models.Lead(
                    id=normalized["id"],
                    agent_id=agent.id if agent else None,
                    source_platform=normalized["source_platform"],
                    source_url=normalized["source_url"],
                    location_raw=normalized.get("location_raw"),
                    buyer_request_snippet=normalized["buyer_request_snippet"],
                    product_category=normalized["product_category"],
                    buyer_name=normalized.get("buyer_name", "Anonymous"),
                    contact_phone=normalized.get("contact_phone"),
                    contact_email=normalized.get("contact_email"),
                    intent_score=normalized["intent_score"],
                    confidence_score=normalized["confidence_score"],
                    non_response_flag=1 if has_bad_history else 0,
                    readiness_level=normalized.get("readiness_level"),
                    urgency_score=normalized.get("urgency_score"),
                    budget_info=normalized.get("budget_info"),
                    product_specs=normalized.get("product_specs"),
                    deal_probability=normalized.get("deal_probability"),
                    intent_type=normalized.get("intent_type", "BUYER"),
                    ranked_score=ranked_score,
                    decision_authority=normalized.get("decision_authority", 0),
                    prior_research_indicator=normalized.get("prior_research_indicator", 0),
                    comparison_indicator=normalized.get("comparison_indicator", 0),
                    is_contact_verified=normalized.get("is_contact_verified", 0),
                    status=models.CRMStatus.NEW,
                )
                
                existing = db.query(models.Lead).filter(models.Lead.source_url == lead.source_url).first()
                
                if existing:
                    if lead.intent_score > existing.intent_score:
                        existing.intent_score = lead.intent_score
                        existing.ranked_score = lead.ranked_score
                        existing.buyer_request_snippet = lead.buyer_request_snippet
                        logger.info(f"Updated existing lead {existing.id} with better score")
                    lead = existing
                else:
                    db.add(lead)

                # Check phone duplicate for agent
                is_phone_duplicate = False
                if agent and lead.contact_phone:
                    existing_agent_leads = db.query(models.AgentLead).join(models.Lead).filter(
                        models.AgentLead.agent_id == agent.id,
                        models.Lead.contact_phone == lead.contact_phone
                    ).first()
                    if existing_agent_leads:
                        is_phone_duplicate = True
                        logger.info(f"Skipping lead for agent {agent.id}: Phone {lead.contact_phone} already discovered.")

                if not existing and not is_phone_duplicate:
                    if agent:
                        if priority_class == "HIGH":
                            lead.notes = f"URGENT MATCH: '{agent.query}' in {agent.location}. Score: {ranked_score:.2f}\n" + (lead.notes or "")
                            high_value_leads.append(lead)
                            if raw_lead:
                                raw_lead.notified = 1
                        elif priority_class == "MEDIUM":
                            lead.notes = f"STANDARD MATCH: '{agent.query}' in {agent.location}. Score: {ranked_score:.2f}\n" + (lead.notes or "")
                            high_value_leads.append(lead)
                            if raw_lead:
                                raw_lead.notified = 1
                        elif priority_class == "LOW":
                            lead.notes = f"[LOW PRIORITY] Score {ranked_score:.2f}. " + (lead.notes or "")
                        
                        agent_lead = models.AgentLead(
                            agent_id=agent.id,
                            lead_id=lead.id
                        )
                        db.add(agent_lead)
                
                    db.add(lead)
                    processed_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing lead from {platform}: {e}")
                continue
        
        # Batch notification
        if agent and high_value_leads:
            count = len(high_value_leads)
            notification = models.Notification(
                lead_id=high_value_leads[0].id,
                agent_id=agent.id,
                message=f"Agent '{agent.name}': {count} New High-Intent Leads found on {platform}."
            )
            db.add(notification)
            alert_count = 1

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving leads from {platform}: {e}")
        return f"Error saving leads: {e}"
    finally:
        db.close()
        
    return f"Processed {processed_count} leads ({alert_count} alerts) from {platform} in {location}"


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
