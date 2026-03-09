from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, FileResponse, JSONResponse
import io
import os
import tempfile
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List, Optional
import uuid
from app.db.database import get_db
from app.models.agent import Agent
from app.models.lead import Lead
from app.schemas.lead import LeadResponse
from app.schemas.agent import AgentCreate, AgentResponse, AgentExecutionStatus
from app.services.agent_scheduler import get_agent_execution_status

logger = logging.getLogger(__name__)

router = APIRouter()


def enrich_agent_data(agent: Agent, db: Session) -> AgentResponse:
    # Get total leads for this agent
    leads_count = db.query(Lead).filter(Lead.agent_id == agent.id).count()
    
    # Get high intent leads (ranked_score >= 0.7)
    high_intent_count = db.query(Lead).filter(
        Lead.agent_id == agent.id, 
        Lead.ranked_score >= 0.7
    ).count()
    
    # Get last run time from agent's last_heartbeat (set when agent runs)
    last_run = agent.last_heartbeat
    
    # Get execution status from scheduler
    exec_status = get_agent_execution_status(agent)
    
    # Create response object manually to inject extra fields
    agent_dict = agent.to_dict()
    return AgentResponse(
        id=uuid.UUID(agent_dict['id']),
        name=agent_dict['name'],
        query=agent_dict['query'],
        location=agent_dict['location'],
        interval_hours=agent_dict['interval_hours'],
        duration_days=agent_dict['duration_days'],
        start_time=agent_dict.get('start_time'),
        end_time=agent_dict.get('end_time'),
        next_run_at=agent_dict.get('next_run_at'),
        active=agent_dict.get('active', True),
        is_running=bool(agent.is_running) if agent.is_running is not None else False,
        leads_count=leads_count,
        high_intent_count=high_intent_count,
        last_run=last_run,
        execution_status=exec_status
    )


@router.get("/", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    """List all agents with stats."""
    agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    return [enrich_agent_data(agent, db) for agent in agents]


@router.post("/", response_model=AgentResponse)
def create_agent(agent_in: AgentCreate, db: Session = Depends(get_db)):
    """Create a new agent and queue it for immediate execution."""
    logger.info(f"[AGENT CREATE] Received request: {agent_in.model_dump()}")
    
    try:
        agent = Agent(
            name=agent_in.name,
            query=agent_in.query,
            location=agent_in.location,
            interval_hours=agent_in.interval_hours,
            duration_days=agent_in.duration_days,
        )

        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        # Initialize schedule using scheduler (sets next_run_at = now)
        from app.services.agent_scheduler import initialize_agent_schedule
        initialize_agent_schedule(db, agent)
        
        logger.info(f"[AGENT CREATE] Success: Agent {agent.id} created")
        
        # Queue agent for immediate execution via Celery
        logger.info(f"[AGENT CREATE] Queueing agent {agent.id} for execution...")
        try:
            from app.core.celery_worker import run_agent_task
            task = run_agent_task.delay(str(agent.id))
            logger.info(f"[AGENT CREATE] Agent queued. Task ID: {task.id}")
            
        except Exception as run_e:
            logger.error(f"[AGENT CREATE] Failed to queue agent: {run_e}")
            # Don't fail the creation if queueing fails
        
        return enrich_agent_data(agent, db)
        
    except Exception as e:
        logger.error(f"[AGENT CREATE] Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.post("/{agent_id}/run")
def run_agent_now(agent_id: str, db: Session = Depends(get_db)):
    """
    Trigger an agent to run immediately via Celery.
    Returns immediately - execution happens in background.
    """
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid agent ID format"})
    
    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
    if not agent:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Agent not found"})
    
    try:
        from app.core.celery_worker import run_agent_task
        task = run_agent_task.delay(str(agent.id))
        
        return {
            "status": "success", 
            "message": f"Agent '{agent.name}' queued for execution",
            "task_id": task.id,
        }
    except Exception as e:
        logger.error(f"Error triggering agent {agent_id}: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/{agent_id}/run-sync")
def run_agent_sync(agent_id: str, db: Session = Depends(get_db)):
    """
    Trigger an agent to run synchronously (blocking execution).
    Waits for result and returns leads found.
    """
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid agent ID format"})
    
    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
    if not agent:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Agent not found"})
    
    try:
        from app.services.search_service import search
        import asyncio
        
        # Run search synchronously
        logger.info(f"[AGENT SYNC] Running agent {agent_id} sync execution")
        result = asyncio.run(search(agent.query, agent.location))
        
        leads_found = len(result.get("leads", []))
        logger.info(f"[AGENT SYNC] Agent {agent_id} found {leads_found} leads")
        
        return {
            "status": "success", 
            "message": f"Agent executed successfully",
            "leads_found": leads_found,
            "result": f"Found {leads_found} leads"
        }
    except Exception as e:
        logger.error(f"[AGENT SYNC] Error running agent {agent_id}: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get agent details."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid agent ID format"})

    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()

    if not agent:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Agent not found"})

    return enrich_agent_data(agent, db)


@router.get("/{agent_id}/leads", response_model=List[LeadResponse])
def get_agent_leads(
    agent_id: str,
    min_score: Optional[float] = None,
    from_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return []

    query = db.query(Lead).filter(Lead.agent_id == agent_uuid)

    if min_score is not None:
        query = query.filter(Lead.confidence_score >= min_score)

    if from_date is not None:
        query = query.filter(Lead.created_at >= from_date)

    leads = (
        query
        .order_by(Lead.ranked_score.desc(), Lead.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return leads


@router.post("/{agent_id}/export")
def export_agent_leads(agent_id: str, db: Session = Depends(get_db)):
    """Export leads for an agent as a text file (POST method)."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return PlainTextResponse("Invalid agent ID format", media_type="text/plain")

    leads = db.query(Lead).filter(Lead.agent_id == agent_uuid).all()
    
    # Create a temp file
    fd, filepath = tempfile.mkstemp(suffix=".txt", prefix=f"{agent_id}_leads_")
    os.close(fd)
    
    with open(filepath, "w", encoding="utf-8") as f:
        for lead in leads:
            # Map fields: signal_text -> buyer_request_snippet (or query), phone -> contact_phone
            signal_text = lead.buyer_request_snippet or lead.query or "N/A"
            phone = lead.contact_phone or "N/A"
            f.write(f"{signal_text} | {phone}\n")

    return FileResponse(filepath, media_type="text/plain", filename=f"{agent_id}_leads.txt")


@router.post("/{agent_id}/stop")
def stop_agent(agent_id: str, db: Session = Depends(get_db)):
    """Stop/Deactivate an agent."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid agent ID format"})
        
    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
    if not agent:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Agent not found"})
        
    agent.active = False  # type: ignore
    db.commit()
    
    return {"status": "success", "message": f"Agent {agent.name} stopped."}


@router.get("/{agent_id}/export")
def export_agent_leads_get(agent_id: str, db: Session = Depends(get_db)):
    """Export leads found by this agent as a .txt file download (GET method)."""
    # Reuse the same logic as POST for consistency
    return export_agent_leads(agent_id, db)


def export_agent_leads_internal(agent_id: str, db: Session):
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return PlainTextResponse("Invalid agent ID format", media_type="text/plain")

    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
    if not agent:
        return PlainTextResponse("Agent not found", media_type="text/plain")

    leads = db.query(Lead).filter(Lead.agent_id == agent_uuid).order_by(Lead.created_at.desc()).all()

    output = io.StringIO()
    output.write(f"--- Leads Export for Agent: {agent.name} ---\n")
    output.write(f"Query: {agent.query}\n")
    output.write(f"Export Date: {datetime.utcnow().isoformat()}\n")
    output.write("-" * 50 + "\n\n")

    for lead in leads:
        output.write(f"Date: {lead.created_at}\n")
        output.write(f"Lead: {lead.title or lead.description}\n")
        output.write(f"URL: {lead.source_url}\n")
        contact = lead.contact_phone or lead.whatsapp_link or "N/A"
        output.write(f"Contact: {contact}\n")
        output.write("-" * 30 + "\n")

    output.seek(0)
    return PlainTextResponse(output.read(), media_type="text/plain", headers={
        "Content-Disposition": f"attachment; filename=leads_{agent.name.replace(' ', '_')}.txt"
    })


@router.delete("/{agent_id}")
def delete_agent(agent_id: str, db: Session = Depends(get_db)):
    """Delete an agent."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid agent ID format"})
        
    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
    if not agent:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Agent not found"})
        
    db.delete(agent)
    db.commit()
    
    return {"status": "success", "message": f"Agent {agent.name} deleted."}
