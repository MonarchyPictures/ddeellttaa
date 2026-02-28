"""
Celery Worker Tasks - Production Only

Pure Celery tasks. No SQLite fallback. No sync execution.
Redis is REQUIRED.

THE ONLY PIPELINE:
generate_high_recall_queries() → run_scrapers_parallel() → 
process_high_recall_results() → save_leads_to_db()
"""
import os
import sys
import logging
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
from app.services.kenya_high_recall_pipeline import (
    generate_high_recall_queries,
    process_high_recall_results
)
from app.services.lead_storage import save_leads_to_db
from app.scrapers.registry import SCRAPER_REGISTRY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@celery.task(name="run_all_agents")
def run_all_agents():
    """Trigger agents that are due for execution."""
    db = SessionLocal()
    try:
        deactivated = deactivate_expired_agents(db)
        if deactivated > 0:
            logger.info(f"Deactivated {deactivated} expired agents")
        
        due_agents = get_agents_due_for_execution(db)
        
        if not due_agents:
            return "No agents due"
        
        triggered = 0
        for agent in due_agents:
            if not should_execute_agent(agent):
                continue
            
            if not mark_agent_running(db, agent):
                continue
            
            logger.info(f"Triggering agent '{agent.name}'")
            run_agent_task.delay(str(agent.id))
            triggered += 1
        
        return f"Triggered {triggered} agents"
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {e}"
    finally:
        db.close()


def calculate_next_run(agent):
    """Calculate next run time based on interval."""
    return agent.last_run + timedelta(hours=agent.interval_hours)


@celery.task(name="run_agent_task")
def run_agent_task(agent_id: str):
    """
    Execute agent using THE ONLY PIPELINE:
    generate_high_recall_queries() → run_scrapers_parallel() → 
    process_high_recall_results() → save_leads_to_db()
    
    No validation layer.
    No competition scoring.
    No raw lead model.
    """
    db = SessionLocal()
    
    try:
        if isinstance(agent_id, str):
            agent_id = uuid.UUID(agent_id)
        
        agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
        
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return f"Agent not found"
        
        logger.info(f"Executing agent '{agent.name}'")
        
        # THE ONLY PIPELINE
        
        # 1. Generate queries
        queries = generate_high_recall_queries(agent.query, agent.location or "Kenya")
        logger.info(f"Generated {len(queries)} queries")
        
        # 2. Run scrapers
        all_results = []
        scrapers = list(SCRAPER_REGISTRY.values())
        logger.info(f"Using {len(scrapers)} scrapers")
        
        for q in queries:
            try:
                results = asyncio.run(
                    run_scrapers_parallel(scrapers, q, agent.location or "Kenya", 24)
                )
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Query failed: {e}")
                continue
        
        logger.info(f"Total raw results: {len(all_results)}")
        
        # 3. Score and filter
        leads = process_high_recall_results(all_results)
        logger.info(f"Processed {len(leads)} leads")
        
        # 4. Save to DB
        if leads:
            save_leads_to_db(leads, agent.query)
            logger.info(f"Saved {len(leads)} leads")
        
        # 5. Update agent schedule
        agent.last_run = datetime.utcnow()
        agent.next_run = calculate_next_run(agent)
        db.commit()
        
        return f"Agent {agent.name}: {len(leads)} leads"
        
    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()


@celery.task(name="cleanup_old_leads")
def cleanup_old_leads():
    """Remove leads older than 4 days."""
    db = SessionLocal()
    try:
        four_days_ago = datetime.now() - timedelta(days=4)
        deleted = db.query(models.Lead).filter(models.Lead.created_at < four_days_ago).delete()
        db.commit()
        logger.info(f"Cleaned up {deleted} old leads")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
    finally:
        db.close()


__all__ = [
    'celery',
    'run_all_agents',
    'run_agent_task',
    'cleanup_old_leads',
]
