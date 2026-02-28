"""
Agent Scheduler - Deterministic DB-Based Scheduling

Makes the database the single source of truth for agent execution timing.
Prevents duplicate runs, missed runs, and handles worker restarts gracefully.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from app.db.database import SessionLocal
from app.db import models

logger = logging.getLogger(__name__)


def calculate_next_run(interval_hours: int, from_time: datetime = None) -> datetime:
    """
    Calculate the next run time based on interval.
    
    Args:
        interval_hours: Hours between runs
        from_time: Calculate from this time (default: now)
        
    Returns:
        datetime of next scheduled run
    """
    if from_time is None:
        from_time = datetime.utcnow()
    
    return from_time + timedelta(hours=interval_hours)


def should_execute_agent(agent: models.Agent) -> bool:
    """
    Check if an agent should be executed based on DB state.
    Prevents duplicate execution and respects schedule.
    
    Args:
        agent: Agent model instance
        
    Returns:
        True if agent should execute now
    """
    now = datetime.utcnow()
    
    # Basic checks
    if not agent:
        return False
    
    if not agent.active:
        logger.debug(f"Agent {agent.id} is not active")
        return False
    
    if agent.is_running:
        logger.debug(f"Agent {agent.id} is already running")
        return False
    
    # Check end time (expired agents)
    if agent.end_time and now >= agent.end_time:
        logger.info(f"Agent {agent.id} has reached end_time, deactivating")
        agent.active = False
        return False
    
    # Check next_run_at - this is the critical check
    if agent.next_run_at and agent.next_run_at > now:
        logger.debug(f"Agent {agent.id} next_run_at ({agent.next_run_at}) is in the future")
        return False
    
    return True


def get_agents_due_for_execution(db: SessionLocal) -> List[models.Agent]:
    """
    Query database for agents that are due to run.
    This is the SINGLE SOURCE OF TRUTH for scheduling.
    
    Args:
        db: Database session
        
    Returns:
        List of agents due for execution
    """
    now = datetime.utcnow()
    
    agents = db.query(models.Agent).filter(
        models.Agent.active == True,
        models.Agent.is_running == False,
        models.Agent.next_run_at <= now
    ).order_by(models.Agent.next_run_at.asc()).all()
    
    logger.info(f"Found {len(agents)} agents due for execution (next_run_at <= {now})")
    return agents


def mark_agent_running(db: SessionLocal, agent: models.Agent) -> bool:
    """
    Mark an agent as running to prevent duplicate execution.
    
    Args:
        db: Database session
        agent: Agent to mark
        
    Returns:
        True if successfully marked, False if another process got there first
    """
    try:
        # Re-query to get latest state (prevents race conditions)
        fresh_agent = db.query(models.Agent).filter(
            models.Agent.id == agent.id,
            models.Agent.is_running == False  # Only if not already running
        ).first()
        
        if not fresh_agent:
            logger.warning(f"Agent {agent.id} is already running (race condition detected)")
            return False
        
        fresh_agent.is_running = True
        fresh_agent.last_heartbeat = datetime.utcnow()
        db.commit()
        
        logger.info(f"Agent {agent.id} marked as running")
        return True
        
    except Exception as e:
        logger.error(f"Failed to mark agent {agent.id} as running: {e}")
        db.rollback()
        return False


def complete_agent_execution(
    db: SessionLocal, 
    agent_id: str, 
    success: bool = True,
    error_message: str = None
) -> None:
    """
    Mark agent execution as complete and schedule next run.
    
    Args:
        db: Database session
        agent_id: Agent UUID string
        success: Whether execution was successful
        error_message: Error message if failed
    """
    try:
        agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
        if not agent:
            logger.error(f"Cannot complete execution - agent {agent_id} not found")
            return
        
        now = datetime.utcnow()
        
        # Update timing
        agent.last_heartbeat = now
        agent.is_running = False
        
        if success:
            # Schedule next run based on interval
            agent.next_run_at = calculate_next_run(agent.interval_hours, now)
            logger.info(f"Agent {agent_id} completed successfully. Next run at {agent.next_run_at}")
        else:
            # If failed, retry sooner (in 15 minutes)
            agent.next_run_at = now + timedelta(minutes=15)
            logger.warning(f"Agent {agent_id} failed. Retry at {agent.next_run_at}. Error: {error_message}")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Failed to complete agent {agent_id} execution: {e}")
        db.rollback()


def initialize_agent_schedule(db: SessionLocal, agent: models.Agent) -> None:
    """
    Initialize scheduling for a newly created agent.
    Sets next_run_at to now so it runs immediately on next scan.
    
    Args:
        db: Database session
        agent: New agent instance
    """
    now = datetime.utcnow()
    
    agent.start_time = now
    agent.end_time = now + timedelta(days=agent.duration_days)
    agent.next_run_at = now  # Run immediately on next scan
    agent.active = True
    agent.is_running = False
    
    db.commit()
    
    logger.info(f"Agent {agent.id} schedule initialized. First run at {agent.next_run_at}")


def deactivate_expired_agents(db: SessionLocal) -> int:
    """
    Deactivate agents that have passed their end_time.
    
    Args:
        db: Database session
        
    Returns:
        Number of agents deactivated
    """
    now = datetime.utcnow()
    
    expired = db.query(models.Agent).filter(
        models.Agent.active == True,
        models.Agent.end_time <= now
    ).all()
    
    count = 0
    for agent in expired:
        logger.info(f"Deactivating expired agent {agent.id} (end_time: {agent.end_time})")
        agent.active = False
        agent.is_running = False
        count += 1
    
    if count > 0:
        db.commit()
    
    logger.info(f"Deactivated {count} expired agents")
    return count


def get_agent_execution_status(agent: models.Agent) -> dict:
    """
    Get human-readable execution status for an agent.
    
    Args:
        agent: Agent instance
        
    Returns:
        Dict with status information
    """
    now = datetime.utcnow()
    
    if not agent.active:
        status = "inactive"
    elif agent.is_running:
        status = "running"
    elif agent.next_run_at and agent.next_run_at > now:
        status = "scheduled"
    else:
        status = "due"
    
    time_until_next = None
    if agent.next_run_at:
        diff = agent.next_run_at - now
        if diff.total_seconds() > 0:
            hours = int(diff.total_seconds() / 3600)
            minutes = int((diff.total_seconds() % 3600) / 60)
            time_until_next = f"{hours}h {minutes}m"
    
    return {
        "status": status,
        "is_active": agent.active,
        "is_running": agent.is_running,
        "last_run": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
        "next_run": agent.next_run_at.isoformat() if agent.next_run_at else None,
        "time_until_next": time_until_next,
        "interval_hours": agent.interval_hours
    }
