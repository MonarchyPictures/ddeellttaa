from celery import Celery
import os
import sys
import logging
import hashlib
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to sys.path for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from celery.schedules import crontab
from app.db.database import SessionLocal
from app.db import models

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Broker configuration with fallback to shared DB transport
BROKER_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./intent_radar_v3.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
FALLBACK_BROKER_URL = f"sqla+{DATABASE_URL}"
RESULT_BACKEND = os.getenv("REDIS_URL", f"db+{DATABASE_URL}")

celery_app = Celery(
    "intent_radar",
    broker=BROKER_URL,
    backend=RESULT_BACKEND
)

# Test connection and fallback if needed
try:
    import redis
    r = redis.from_url(BROKER_URL)
    r.ping()
except Exception:
    logger.warning("Redis not found. Falling back to shared DB broker/backend.")
    celery_app.conf.broker_url = FALLBACK_BROKER_URL

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Nairobi",
    enable_utc=True,
    beat_schedule={
        "check-agents-every-minute": {
            "task": "run_all_agents",
            "schedule": 60.0, # Run every minute
        },
        "cleanup-every-12-hours": {
            "task": "cleanup_old_leads",
            "schedule": 43200.0,
        },
    },
)

@celery_app.task(name="ingest_leads_task")
def ingest_leads_task(raw_results: list):
    """
    Async Task: Process raw scraper results -> Validation -> DB.
    Implements the Queue -> Database layer.
    """
    from app.services.ingestion_service import ingest_leads
    
    logger.info(f"Queue: Received {len(raw_results)} items for ingestion")
    try:
        # Ingestion handles Validation, Dedupe, DB Save
        leads = ingest_leads(raw_results)
        return [l.id for l in leads if l.id]
    except Exception as e:
        logger.error(f"Ingestion Task Failed: {e}")
        return []

@celery_app.task(name="specialops_mission_task")
def specialops_mission_task(query: str, location: str = "Kenya", agent_id: str = None):
    """
    MASTER AGENT MISSION: Autonomous web intelligence routing.
    Follows the SpecialOps decision logic for search, crawl, and extraction.
    """
    from app.core.specialops import SpecialOpsAgent
    from app.utils.normalization import LeadValidator
    from app.nlp.duplicate_detector import DuplicateDetector
    from app.services.market_classifier import is_valid_buyer, calculate_kenyan_intent_score
    
    agent_ops = SpecialOpsAgent()
    validator = LeadValidator()
    detector = DuplicateDetector()
    
    logger.info(f"Starting SpecialOps Mission: {query} in {location}")
    
    # 1. Execute Mission
    try:
        mission_results = agent_ops.execute_mission(query, location)
    except Exception as e:
        logger.error(f"SpecialOps Mission Failed: {e}")
        return f"Mission error: {e}"
    
    db = SessionLocal()
    processed_count = 0
    
    try:
        # Fetch recent leads for duplicate detection
        recent_leads = db.query(models.Lead).filter(
            models.Lead.request_timestamp >= datetime.now(timezone.utc) - timedelta(hours=24)
        ).all()
        recent_texts = [l.buyer_request_snippet for l in recent_leads if l.buyer_request_snippet]

        logger.info(f"SpecialOps Mission found {len(mission_results)} potential results")
        
        for result in mission_results:
            try:
                # Prepare for normalization
                # Fix structure mismatch with specialops.py
                raw = {
                    "source": result.get("source", "specialops"),
                    "link": result.get("href") or result.get("url"),
                    "text": result.get("body") or result.get("text") or result.get("data", {}).get("raw_text", ""),
                    "title": result.get("title") or result.get("data", {}).get("title", ""),
                    "location": location
                }
                
                # --- STRICT FILTERING FOR SPECIAL OPS ---
                # Even Special Ops must pass the Bulletproof Wall
                if not is_valid_buyer(raw['text'], raw['link']):
                    logger.info(f"SpecialOps Lead REJECTED (Strict Filter): {raw['link']}")
                    continue

                # Check Score
                intent_points, details = calculate_kenyan_intent_score(raw['text'])
                if intent_points < 50:
                    logger.info(f"SpecialOps Lead REJECTED (Score {intent_points} < 50): {raw['link']}")
                    continue
                
                logger.info(f"Normalizing lead from {raw['source']}: {raw['text'][:50]}...")
                normalized = validator.normalize_lead(raw, db=db)
                if not normalized:
                    logger.info(f"Lead rejected by normalization")
                    continue
                
                # Duplicate Detection
                snippet = normalized.get("buyer_request_snippet", "")
                if snippet and detector.is_duplicate(snippet, recent_texts):
                    continue

                # Create lead record
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
                    
                    # NEW: Special Ops Fields
                    is_hot_lead=1 if result.get("is_hot_lead") else 0,
                    whatsapp_ready_data=result.get("whatsapp_ready"),
                    
                    # Contact Verification
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

@celery_app.task(bind=True, max_retries=5, name="scrape_source_task")
def scrape_source_task(self, source_name: str, query: str, location: str = "Kenya"):
    """
    Real Engineering Self-Healing Scraper Task:
    1. Retries with exponential backoff.
    2. Tracks failure counts per source (Redis).
    3. Auto-disables source after X failures (Circuit Breaker).
    4. Reactivates after cooldown.
    """
    import asyncio
    from app.scrapers.registry import SCRAPER_REGISTRY
    import redis
    
    # Configuration
    FAILURE_THRESHOLD = 3
    COOLDOWN_SECONDS = 300 # 5 minutes
    
    # Redis Connection (Reuse broker URL if possible)
    try:
        r = redis.from_url(BROKER_URL)
    except Exception:
        logger.warning("Redis not available for circuit breaker. Skipping self-healing logic.")
        r = None

    # Circuit Breaker Keys
    failure_key = f"scraper_failures:{source_name}"
    disabled_key = f"scraper_disabled:{source_name}"
    
    # 1. Check Circuit Breaker
    if r and r.exists(disabled_key):
        ttl = r.ttl(disabled_key)
        logger.warning(f"🚫 Source '{source_name}' is DISABLED. Cooldown active for {ttl}s.")
        return []

    scraper = SCRAPER_REGISTRY.get(source_name)
    if not scraper:
        logger.error(f"Scraper '{source_name}' not found in registry.")
        return []

    logger.info(f"🕵️Scraping Source: {source_name} for '{query}'")

    try:
        # 2. Run Scraper (Async to Sync)
        # Note: Scrapers are async, so we run them in a new event loop
        results = asyncio.run(scraper.search(query, location))
        
        # 3. Success! Reset failure count
        if r:
            r.delete(failure_key)
            
        return results

    except Exception as exc:
        logger.error(f"❌ Scraper '{source_name}' Failed: {exc}")
        
        if r:
            # 4. Track Failures
            failures = r.incr(failure_key)
            
            # 5. Trip Circuit Breaker
            if failures >= FAILURE_THRESHOLD:
                r.setex(disabled_key, COOLDOWN_SECONDS, "1")
                r.delete(failure_key) # Reset count for next cycle
                logger.critical(f"🔥🔥 Source '{source_name}' DISABLED for {COOLDOWN_SECONDS}s due to {failures} failures.")
                # We do NOT retry if circuit is broken, just fail hard or return empty
                return []
        
        # 6. Retry (if circuit not broken yet)
        # Exponential backoff: 60s, 120s, ...
        retry_delay = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=retry_delay)

@celery_app.task(name="run_all_agents")
def run_all_agents():
    """Trigger active agents that are due for discovery."""
    db = SessionLocal()
    try:
        now = datetime.now()
        # Find active agents where next_run_at is reached or never set
        active_agents = db.query(models.Agent).filter(
            models.Agent.active == True,
            (models.Agent.next_run_at <= now) | (models.Agent.next_run_at == None)
        ).all()
        
        triggered_count = 0
        for agent in active_agents:
            # Check self-termination condition (end_time reached)
            if agent.end_time and now >= agent.end_time:
                logger.info(f"Agent '{agent.name}' (ID: {agent.id}) has reached end_time. Self-terminating.")
                agent.active = False
                agent.next_run_at = None # Clear schedule
                db.commit()
                continue
            
            # Fallback for older agents without end_time: Calculate from duration
            elif not agent.end_time and agent.created_at:
                expiry_time = agent.created_at + timedelta(days=agent.duration_days)
                if now > expiry_time:
                    logger.info(f"Agent '{agent.name}' (ID: {agent.id}) has expired (duration). Deactivating.")
                    agent.active = False
                    agent.next_run_at = None
                    db.commit()
                    continue
            
            # Dispatch task
            run_agent_task.delay(str(agent.id))
            
            # Update next run timestamp IMMEDIATELY to prevent duplicate runs
            # This locks the agent until the next cycle
            agent.next_run_at = now + timedelta(hours=agent.interval_hours or 2)
            db.commit()
            triggered_count += 1
            
        return f"Triggered {triggered_count} agents"
    except Exception as e:
        logger.error(f"Error in run_all_agents: {e}")
        return f"Error: {e}"
    finally:
        db.close()

@celery_app.task(name="scrape_platform_task")
def scrape_platform_task(platform: str, query: str, location: str = "Kenya", agent_id: str = None, radius: int = 50, min_intent: float = 0.7, tier: int = 2, timeout: int = 15):
    """Background task to scrape a platform and save leads."""
    from app.scrapers.scraper import LeadScraper
    from app.utils.normalization import LeadValidator
    from app.intelligence.ranking import RankingEngine
    from app.nlp.duplicate_detector import DuplicateDetector
    from app.utils.outreach import OutreachEngine
    from app.core.compliance import ComplianceManager
    
    scraper = LeadScraper()
    validator = LeadValidator()
    ranking_engine = RankingEngine()
    outreach_engine = OutreachEngine()
    detector = DuplicateDetector()
    compliance = ComplianceManager()
    
    # 1. Platform Compliance (Throttling)
    try:
        compliance.wait_for_rate_limit(platform.lower())
    except Exception as e:
        logger.error(f"Compliance check failed for {platform}: {e}")
    
    # 2. Scrape
    try:
        # Pass radius to scraper if supported
        # Tier 2 = Full Deep Scrape (API + Playwright) for Agents
        # Timeout = 15s per scraper to prevent blocking
        raw_results = scraper.scrape_platform(platform.lower(), query, location, radius=radius, tier=tier, timeout=timeout)
    except Exception as e:
        logger.error(f"Scraper failed for {platform}: {e}")
        return f"Scraper error on {platform}"
    
    db = SessionLocal()
    processed_count = 0
    alert_count = 0
    
    # NEW: Accumulate high-value leads for a single summary notification
    high_value_leads = []
    
    try:
        # Fetch agent if id provided
        agent = None
        if agent_id:
            agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()

        # Fetch recent leads for duplicate detection (last 24h)
        recent_leads = db.query(models.Lead).filter(
            models.Lead.created_at >= datetime.now() - timedelta(hours=24)
        ).all()
        recent_texts = [l.buyer_request_snippet for l in recent_leads]

        for raw in raw_results:
            try:
                if "source" not in raw:
                    raw["source"] = platform.capitalize()
                
                # -------------------------------------------------------------------------
                # NEW: SAVE EVERYTHING TO AGENT_RAW_LEADS (Before any processing)
                # -------------------------------------------------------------------------
                raw_lead = None
                try:
                    # 1. Prepare Data
                    raw_text = raw.get("body") or raw.get("text") or raw.get("data", {}).get("raw_text", "") or "N/A"
                    phone = raw.get("phone") or raw.get("contact", {}).get("phone")
                    
                    # 2. Compute Hash (Normalized)
                    # We use MD5 for speed/size. Collisions are rare enough for this text data.
                    content_hash = hashlib.md5(raw_text.strip().lower().encode('utf-8')).hexdigest()
                    
                    # 3. Deduplication Check (Per Agent)
                    # "Avoid storing same signal twice per agent"
                    is_duplicate = False
                    if agent_id:
                        # Check content hash
                        existing_hash = db.query(models.AgentRawLead).filter(
                            models.AgentRawLead.agent_id == agent_id,
                            models.AgentRawLead.content_hash == content_hash
                        ).first()
                        
                        if existing_hash:
                            is_duplicate = True
                            logger.info(f"Duplicate signal (hash) for agent {agent_id}. Skipping storage.")
                            
                        # Check phone (if valid)
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
                    # We commit raw leads immediately to ensure they are captured even if processing fails later
                    db.commit()
                    db.refresh(raw_lead)
                except Exception as raw_e:
                    logger.error(f"Failed to save AgentRawLead: {raw_e}")
                    # Don't stop processing, but log the error. 
                    # In a strict "save everything" mode, this is critical, but we continue to try and process.
                    
                normalized = validator.normalize_lead(raw, db=db)
                if not normalized:
                    logger.info(f"Skipping empty normalization for lead from {platform}")
                    continue
                
                # Update Raw Lead with analysis data
                if raw_lead:
                    raw_lead.geo_score = normalized.get("geo_score", 0.0)
                    raw_lead.intent_score = normalized.get("intent_score", 0.0)
                    raw_lead.confidence_score = normalized.get("confidence_score", 0.0)
                    # We'll calculate ranked_score below and update it
                    raw_lead.processed = 1
                    # db.add(raw_lead) -> Wait to add with ranked_score
                
                # 🎯 RANKING ENGINE (Runs After Save/Normalization)
                ranked_score = ranking_engine.calculate_score(normalized)
                priority_class = ranking_engine.classify_lead(ranked_score)
                
                if raw_lead:
                    raw_lead.ranked_score = ranked_score
                    db.add(raw_lead)
                
                logger.info(f"Lead Ranked: Score={ranked_score}, Class={priority_class}")

                # Metadata check (Replaces hard skip)
                if normalized.get("intent_score", 0) < min_intent:
                    logger.info(f"Signal recorded with low intent score: {normalized.get('intent_score')} < {min_intent} (threshold for agent {agent_id})")

                # 3. Duplicate Detection
                if detector.is_duplicate(normalized["buyer_request_snippet"], recent_texts):
                    logger.info(f"Skipping duplicate lead from {platform}: {normalized['buyer_request_snippet'][:50]}...")
                    continue

                # Metadata check for Kenya (Replaces hard skip)
                loc = normalized.get("location_raw", "").lower()
                is_kenya = "kenya" in loc or any(city.lower() in loc for city in ["nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", "naivasha"])
                
                if not is_kenya:
                    other_countries = ["nigeria", "uganda", "tanzania", "usa", "uk", "india", "ghana", "south africa"]
                    mentions_other = any(c in loc for c in other_countries)
                    if not mentions_other and (location.lower() == "kenya" or "kenya" in query.lower()):
                        is_kenya = True
                
                if not is_kenya:
                    logger.info(f"Signal recorded from outside primary geo: {loc}")
                    # We save it anyway, but we might want to flag it

                # Check for history of non-response
                has_bad_history = outreach_engine.check_non_response_history(
                    db, 
                    phone=normalized.get("contact_phone"), 
                    email=normalized.get("contact_email")
                )

                # Create lead record
                lead = models.Lead(
                    id=normalized["id"],
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
                    
                    # Hyper-Specific Intent Intelligence
                    readiness_level=normalized.get("readiness_level"),
                    urgency_score=normalized.get("urgency_score"),
                    budget_info=normalized.get("budget_info"),
                    product_specs=normalized.get("product_specs"),
                    deal_probability=normalized.get("deal_probability"),
                    intent_type=normalized.get("intent_type", "BUYER"),
                    
                    # NEW: Smart Matching
                    match_score=normalized.get("match_score", 0.0),
                    compatibility_status=normalized.get("compatibility_status"),
                    match_details=normalized.get("match_details"),
                    
                    # NEW: Intent Analysis Extensions
                    quantity_requirement=normalized.get("quantity_requirement"),
                    payment_method_preference=normalized.get("payment_method_preference"),
                    
                    # NEW: Local Advantage
                    delivery_range_score=normalized.get("delivery_range_score", 0.0),
                    neighborhood=normalized.get("neighborhood"),
                    local_pickup_preference=normalized.get("local_pickup_preference", 0),
                    delivery_constraints=normalized.get("delivery_constraints"),
                    
                    # 🎯 RANKING ENGINE
                    ranked_score=ranked_score,
                    
                    # NEW: Deal Readiness
                    decision_authority=normalized.get("decision_authority", 0),
                    prior_research_indicator=normalized.get("prior_research_indicator", 0),
                    comparison_indicator=normalized.get("comparison_indicator", 0),
                    upcoming_deadline=normalized.get("upcoming_deadline"),
                    
                    # Real-Time & Competitive Intelligence
                    availability_status=normalized.get("availability_status"),
                    competition_count=normalized.get("competition_count"),
                    is_unique_request=normalized.get("is_unique_request"),
                    optimal_response_window=normalized.get("optimal_response_window"),
                    peak_response_time=normalized.get("peak_response_time"),
                    
                    # Contact Verification & Reliability
                    is_contact_verified=normalized.get("is_contact_verified", 0),
                    contact_reliability_score=normalized.get("contact_reliability_score", 0.0),
                    preferred_contact_method=normalized.get("preferred_contact_method"),
                    disposable_email_flag=normalized.get("disposable_email_flag", 0),
                    contact_metadata=normalized.get("contact_metadata", {}),
                    
                    # Response Tracking System
                    response_count=normalized.get("response_count", 0),
                    average_response_time_mins=normalized.get("average_response_time_mins"),
                    conversion_rate=normalized.get("conversion_rate", 0.0),
                    
                    # NEW: Comprehensive Lead Intelligence
                    buyer_history=normalized.get("buyer_history"),
                    platform_activity_level=normalized.get("platform_activity_level"),
                    past_response_rate=normalized.get("past_response_rate", 0.0),
                    market_price_range=normalized.get("market_price_range"),
                    seasonal_demand=normalized.get("seasonal_demand"),
                    supply_status=normalized.get("supply_status"),
                    conversion_signals=normalized.get("conversion_signals", []),
                    talking_points=normalized.get("talking_points", []),
                    competitive_advantages=normalized.get("competitive_advantages", []),
                    pricing_strategy=normalized.get("pricing_strategy"),
                    
                    verification_badges=normalized.get("verification_badges", []),
                    is_genuine_buyer=normalized.get("is_genuine_buyer", 1),
                    last_activity=normalized.get("last_activity"),
                    status=models.CRMStatus.NEW,
                    notes=normalized.get("notes", "")
                )
                
                # Check if lead exists by link
                existing = db.query(models.Lead).filter(models.Lead.source_url == lead.source_url).first()
                
                if existing:
                    # Update existing lead with new info if better
                    if lead.intent_score > existing.intent_score:
                        existing.intent_score = lead.intent_score
                        existing.ranked_score = lead.ranked_score
                        existing.buyer_request_snippet = lead.buyer_request_snippet
                        logger.info(f"Updated existing lead {existing.id} with better score")
                    # We still use 'lead' as reference for notification logic below, but mapped to 'existing.id'
                    lead = existing
                else:
                    db.add(lead)
                    # Must flush to get ID if we generated it, but normalized["id"] should be set
                    # db.flush() 

                
                # Check if this phone already exists for this agent (Duplicate Prevention)
                is_phone_duplicate = False
                if agent and lead.contact_phone:
                    # Check across all leads this agent has found
                    existing_agent_leads = db.query(models.AgentLead).join(models.Lead).filter(
                        models.AgentLead.agent_id == agent.id,
                        models.Lead.contact_phone == lead.contact_phone
                    ).first()
                    if existing_agent_leads:
                        is_phone_duplicate = True
                        logger.info(f"Skipping lead for agent {agent.id}: Phone {lead.contact_phone} already discovered by this agent.")

                if not existing and not is_phone_duplicate:
                    # 🎯 RANKING ENGINE: PRIORITY ROUTING
                    # High = Immediate Notification
                    # Medium = Badge Only (Silent Store with visual indicator)
                    # Low = Silent (Archive)
                    
                    if agent:
                        if priority_class == "HIGH":
                            # Update notes with alert info
                            lead.notes = f"🚨 URGENT MATCH: '{agent.query}' in {agent.location}. Score: {ranked_score:.2f}\n" + (lead.notes or "")
                            
                            # Add to batch for summary notification
                            high_value_leads.append(lead)
                            
                            # Mark raw lead as notified (so we know it's been handled)
                            if raw_lead:
                                raw_lead.notified = 1
                            
                        elif priority_class == "MEDIUM":
                            # Update notes
                            lead.notes = f"✨ STANDARD MATCH: '{agent.query}' in {agent.location}. Score: {ranked_score:.2f}\n" + (lead.notes or "")
                            
                            # Add to batch for summary notification
                            high_value_leads.append(lead)
                            
                            if raw_lead:
                                raw_lead.notified = 1
                            
                        elif priority_class == "LOW":
                            # Mark as low priority / archive
                            lead.notes = f"[LOW PRIORITY] Score {ranked_score:.2f}. " + (lead.notes or "")
                            
                        # Always link to agent
                        agent_lead = models.AgentLead(
                            agent_id=agent.id,
                            lead_id=lead.id
                        )
                        db.add(agent_lead)
                    
                    db.add(lead)
                    processed_count += 1
                elif existing and not is_phone_duplicate:
                    # Lead exists in system but first time for this specific agent
                    if agent:
                        # Check if agent already has this specific lead record
                        already_linked = db.query(models.AgentLead).filter(
                            models.AgentLead.agent_id == agent.id,
                            models.AgentLead.lead_id == existing.id
                        ).first()
                        
                        if not already_linked:
                            # 🎯 RANKING ENGINE: PRIORITY ROUTING (Existing Lead)
                            if priority_class in ["HIGH", "MEDIUM"]:
                                # Add to batch for summary notification
                                high_value_leads.append(existing)
                                
                                if raw_lead:
                                    raw_lead.notified = 1
                            
                            # Store link
                            agent_lead = models.AgentLead(
                                agent_id=agent.id,
                                lead_id=existing.id
                            )
                            db.add(agent_lead)
            except Exception as e:
                logger.error(f"Error processing lead from {platform}: {e}")
                continue
        
        # -------------------------------------------------------------------------
        # NEW: BATCH NOTIFICATION (Per Scrape Run)
        # -------------------------------------------------------------------------
        if agent and high_value_leads:
            count = len(high_value_leads)
            # Create ONE summary notification for this run
            # e.g. "Agent 'Water Tanks': 3 New High-Intent Leads"
            notification = models.Notification(
                lead_id=high_value_leads[0].id, # Link to the first one for reference
                agent_id=agent.id,
                message=f"Agent '{agent.name}': {count} New High-Intent Leads found on {platform}."
            )
            db.add(notification)
            alert_count = 1 # One notification sent

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving leads from {platform}: {e}")
        return f"Error saving leads: {e}"
    finally:
        db.close()
        
    return f"Processed {processed_count} leads ({alert_count} alerts) from {platform} in {location}"

@celery_app.task(name="run_agent_task")
def run_agent_task(agent_id: str):
    """
    Run discovery for a single agent following the strict flow:
    1. Call search pipeline (Tier 2 Deep Scrape)
    2. Save ALL raw leads (handled in scrape_platform_task)
    3. Score & Rank leads (handled in scrape_platform_task)
    4. Mark high score as notified (handled in scrape_platform_task)
    5. Update next_run_at (handled in scheduler to prevent race conditions)
    """
    db = SessionLocal()
    try:
        agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
        if not agent:
            logger.error(f"Agent {agent_id} not found in database.")
            return f"Agent {agent_id} not found"
        
        logger.info(f"EXECUTING Agent Flow for '{agent.name}' (ID: {agent.id})")
        logger.info(f"1. Calling Search Pipeline (Tier 2, Async)...")
        
        platforms = ["google", "facebook", "reddit", "tiktok", "twitter"]
        for platform in platforms:
            # We trigger the platform scrape task which handles:
            # -> Save Raw -> Score -> Rank -> Notify
            scrape_platform_task.delay(
                platform, 
                agent.query, 
                agent.location, 
                str(agent.id),
                radius=50, 
                min_intent=0.0, # Save everything (Rank Later)
                tier=2, # 🐢 FULL DEEP SCRAPE (Tier 1 + Tier 2)
                timeout=15 # 15s Timeout per scraper
            )
            
        # Note: next_run_at is updated in run_all_agents BEFORE calling this 
        # to prevent scheduler race conditions.
        
        return f"Agent {agent.name} discovery initiated on {len(platforms)} platforms."
    except Exception as e:
        db.rollback()
        logger.error(f"CRITICAL: Agent {agent_id} execution failed. Error: {e}")
        return f"Error: {e}"
    finally:
        db.close()

@celery_app.task(name="cleanup_old_leads")
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

@celery_app.task(name="update_lead_availability")
def update_lead_availability():
    """Update availability status based on time passed."""
    db = SessionLocal()
    try:
        # Leads older than 48 hours are "Likely Closed"
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

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Run cleanup every 12 hours
    sender.add_periodic_task(43200.0, cleanup_old_leads.s(), name='cleanup-every-12-hours')
    # Update availability every hour
    sender.add_periodic_task(3600.0, update_lead_availability.s(), name='update-availability-hourly')
