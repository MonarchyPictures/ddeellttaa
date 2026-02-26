import asyncio
import logging
import uuid
import signal
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import update
from sqlalchemy.sql import func
from app.db.database import SessionLocal
from app.models.agent import Agent
from app.services.pipeline import run_pipeline_for_query
from app.utils.notifications import notify_new_leads
from app.services.deduplication_service import upsert_lead_atomic

logger = logging.getLogger(__name__)

# Global control flags
STOP_SCHEDULER = False

# --- Helper Sync Functions (Run in Thread) ---

def reset_stale_agents(db: Session, timeout_minutes: int = 60):
    """
    Reset agents that have been 'is_running' for too long.
    This prevents deadlocks if a process crashes.
    """
    try:
        # Reset agents that are marked running but haven't updated in timeout_minutes
        # Using last_heartbeat if available
        now = datetime.utcnow()
        limit = now - timedelta(minutes=timeout_minutes)
        
        stmt = (
            update(Agent)
            .where(Agent.is_running == True)
            # If last_heartbeat is null, assume it's stale (crashed before first heartbeat)
            # OR if last_heartbeat is older than limit
            .where((Agent.last_heartbeat < limit) | (Agent.last_heartbeat == None))
            .values(is_running=False)
        )
        result = db.execute(stmt)
        db.commit()
        
        if result.rowcount > 0:
            logger.warning(f"🔄 Reset {result.rowcount} stale/stuck agents.")
            
    except Exception as e:
        logger.error(f"Error resetting stale agents: {e}")
        db.rollback()

def _get_due_agents_sync():
    """Fetch agents due for execution."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        # Only fetch agents that are active, due, and NOT running
        agents = db.query(Agent).filter(
            Agent.active == True, 
            Agent.next_run_at <= now,
            Agent.is_running == False
        ).all()
        # Return IDs to avoid detached instance issues
        return [str(agent.id) for agent in agents]
    finally:
        db.close()

def _lock_agent_atomic_sync(agent_id_str):
    """
    Atomically lock the agent. 
    Returns dict of agent data if successful, None otherwise.
    """
    db = SessionLocal()
    try:
        agent_uuid = uuid.UUID(agent_id_str)
        
        # ATOMIC UPDATE: Set is_running=True ONLY if currently False
        # This prevents race conditions where two workers grab the same agent
        stmt = (
            update(Agent)
            .where(Agent.id == agent_uuid, Agent.is_running == False, Agent.active == True)
            .values(is_running=True, last_heartbeat=func.now())
        )
        result = db.execute(stmt)
        db.commit()
        
        if result.rowcount == 1:
            # Successfully locked - now fetch data
            agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
            return {
                "id": str(agent.id),
                "name": agent.name,
                "query": agent.query,
                "location": agent.location,
                "interval_hours": agent.interval_hours,
                "next_run_at": agent.next_run_at
            }
        else:
            # Failed to lock (already running or inactive)
            return None
            
    except Exception as e:
        logger.error(f"Error locking agent {agent_id_str}: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def _heartbeat_sync(agent_id_str):
    """Update agent heartbeat."""
    db = SessionLocal()
    try:
        agent_uuid = uuid.UUID(agent_id_str)
        stmt = update(Agent).where(Agent.id == agent_uuid).values(last_heartbeat=func.now())
        db.execute(stmt)
        db.commit()
    except Exception as e:
        logger.error(f"Heartbeat failed for {agent_id_str}: {e}")
    finally:
        db.close()

def _save_results_and_unlock_sync(agent_id_str, leads, agent_data):
    """Save leads, notify, and update next run time."""
    db = SessionLocal()
    try:
        agent_uuid = uuid.UUID(agent_id_str)
        agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
        
        if not agent:
            return
            
        # Save leads ATOMICALLY
        saved_count = 0
        if leads:
            for lead in leads:
                # Use Atomic Upsert
                saved_lead = upsert_lead_atomic(db, lead)
                if saved_lead:
                    saved_count += 1
                
        # Update Agent Schedule
        # Handle next_run_at being None or offset-naive
        base_time = agent_data['next_run_at']
        if not base_time:
             base_time = datetime.now(timezone.utc)
        elif base_time.tzinfo is None:
             base_time = base_time.replace(tzinfo=timezone.utc)
             
        # Calculate next run
        next_run = datetime.now(timezone.utc) + timedelta(hours=agent_data['interval_hours'])
        # Ensure we don't schedule in the past if processing took long
        if next_run < datetime.now(timezone.utc):
            next_run = datetime.now(timezone.utc) + timedelta(minutes=10)

        agent.next_run_at = next_run
        agent.is_running = False
        
        db.commit()
        
        # Notify (Sync but fast usually)
        if saved_count > 0:
            try:
                notify_new_leads(agent.name, leads, agent_id=agent.id)
            except Exception as n_err:
                logger.error(f"[NOTIFY ERROR] {n_err}")
                
        logger.info(f"[AGENT DONE] {agent.name} -> {saved_count} leads saved. Next run: {next_run}")
        
    except Exception as e:
        logger.error(f"[AGENT ERROR] Save/Unlock failed: {e}")
        db.rollback()
        # Try to force unlock
        try:
            _unlock_on_error_sync(agent_id_str)
        except:
            pass
    finally:
        db.close()

def _unlock_on_error_sync(agent_id_str):
    """Unlock agent on error."""
    db = SessionLocal()
    try:
        agent_uuid = uuid.UUID(agent_id_str)
        stmt = (
            update(Agent)
            .where(Agent.id == agent_uuid)
            .values(is_running=False)
        )
        db.execute(stmt)
        db.commit()
    except Exception as e:
        logger.error(f"Error unlocking agent {agent_id_str}: {e}")
    finally:
        db.close()

def reset_agents_on_startup():
    """Reset stuck agents."""
    db = SessionLocal()
    reset_stale_agents(db)
    db.close()

# --- Async Functions ---

async def heartbeat_loop(agent_id: str, stop_event: asyncio.Event):
    """Keep the agent alive in DB."""
    while not stop_event.is_set():
        try:
            await asyncio.to_thread(_heartbeat_sync, agent_id)
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")
        
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            continue
        except Exception:
            break

async def execute_agent(agent_id: str):
    """
    Execute a single agent cycle with timeout protection.
    """
    # 1. Atomic Lock (Thread)
    agent_data = await asyncio.to_thread(_lock_agent_atomic_sync, agent_id)
    if not agent_data:
        # Could not lock (already running), skip
        return

    logger.info(f"[AGENT START] {agent_data['name']}")
    
    # Start Heartbeat
    stop_heartbeat = asyncio.Event()
    heartbeat_task = asyncio.create_task(heartbeat_loop(agent_id, stop_heartbeat))

    try:
        # 2. Run Pipeline (Async) with TIMEOUT
        # agent_data['location'] might be None
        location = agent_data['location'] or "Kenya"
        
        # Enforce timeout (e.g., 10 minutes max per agent)
        results = await asyncio.wait_for(
            run_pipeline_for_query(agent_data['query'], location=location),
            timeout=600 # 10 minutes
        )
        
        # Stop heartbeat before saving
        stop_heartbeat.set()
        await heartbeat_task

        # 3. Save & Unlock (Thread)
        await asyncio.to_thread(_save_results_and_unlock_sync, agent_id, results, agent_data)

    except asyncio.TimeoutError:
        logger.error(f"[AGENT TIMEOUT] Agent {agent_data['name']} timed out after 600s")
        stop_heartbeat.set()
        await heartbeat_task
        await asyncio.to_thread(_unlock_on_error_sync, agent_id)
        
    except Exception as e:
        logger.error(f"[AGENT ERROR] {e}")
        stop_heartbeat.set()
        await heartbeat_task
        # Unlock (Thread)
        await asyncio.to_thread(_unlock_on_error_sync, agent_id)

async def scheduler_loop():
    """
    Main scheduler loop.
    """
    global STOP_SCHEDULER
    logger.info("--- Agent Scheduler Engine Started ---")
    
    # Reset stale agents on startup
    await asyncio.to_thread(reset_agents_on_startup)
    
    while not STOP_SCHEDULER:
        try:
            # Fetch due agents (Thread)
            agent_ids = await asyncio.to_thread(_get_due_agents_sync)
            
            if agent_ids:
                logger.info(f"Found {len(agent_ids)} agents due for execution.")
            
            tasks = []
            for agent_id in agent_ids:
                # Run concurrently using create_task
                # We track tasks to ensure we don't spawn too many if needed, 
                # but for now we let them run freely as they are IO bound.
                task = asyncio.create_task(execute_agent(agent_id))
                tasks.append(task)
            
            # Optional: Wait for batch to finish or just continue?
            # Continuing allows overlapping schedules which is fine as long as we have resources.
            # But to be safe and avoid "orphan" tasks if loop crashes, we could track them.
            
        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled. Shutting down...")
            STOP_SCHEDULER = True
            break
        except Exception as e:
            logger.error(f"[SCHEDULER ERROR] {e}")
            
        # Sleep for 60 seconds before next check
        # Use smaller sleeps to check for STOP_SCHEDULER more often?
        # Or just sleep and rely on CancelledError
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break

def stop_scheduler():
    global STOP_SCHEDULER
    STOP_SCHEDULER = True
