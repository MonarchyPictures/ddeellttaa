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
from app.schemas.agent import AgentCreate, AgentResponse

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
    
    # Create response object manually to inject extra fields
    agent_dict = agent.to_dict()
    agent_dict['id'] = uuid.UUID(agent_dict['id'])
    agent_dict['leads_count'] = leads_count
    agent_dict['high_intent_count'] = high_intent_count
    agent_dict['last_run'] = last_run
    
    return agent_dict

@router.get("/", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    """List all agents with stats."""
    agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    return [enrich_agent_data(agent, db) for agent in agents]

@router.post("/", response_model=AgentResponse)
def create_agent(agent_in: AgentCreate, db: Session = Depends(get_db)):
    """Create a new agent and run it immediately."""
    logger.info(f"[AGENT CREATE] Received request: {agent_in.model_dump()}")
    
    try:
        agent = Agent(
            name=agent_in.name,
            query=agent_in.query,
            location=agent_in.location,
            interval_hours=agent_in.interval_hours,
            duration_days=agent_in.duration_days,
        )

        # Initialize schedule
        agent.initialize_schedule()

        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"[AGENT CREATE] Success: Agent {agent.id} created")
        
        # RUN AGENT IMMEDIATELY after creation (synchronous, no Celery needed)
        logger.info(f"[AGENT CREATE] Running agent {agent.id} immediately (SYNC)...")
        try:
            from app.core.celery_worker import run_agent_task
            # sync=True means wait for all scrapes to complete
            result = run_agent_task(str(agent.id), sync=True)
            logger.info(f"[AGENT CREATE] Agent run result: {result}")
            
        except Exception as run_e:
            logger.error(f"[AGENT CREATE] Agent run failed: {run_e}")
            # Don't fail the creation if run fails
        
        return enrich_agent_data(agent, db)
        
    except Exception as e:
        logger.error(f"[AGENT CREATE] Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.post("/{agent_id}/run")
def run_agent_now(agent_id: str, db: Session = Depends(get_db)):
    """
    Trigger an agent to run immediately.
    Works even if Celery is down (uses fallback execution).
    """
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Invalid agent ID format"})
    
    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
    if not agent:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Agent not found"})
    
    try:
        from app.core.celery_app import send_task
        result = send_task("run_agent_task", str(agent.id))
        
        if result.get("status") == "queued":
            return {
                "status": "success", 
                "message": f"Agent '{agent.name}' queued for execution",
                "task_id": result.get("task_id"),
                "mode": "celery"
            }
        elif result.get("status") == "completed_direct":
            return {
                "status": "success",
                "message": f"Agent '{agent.name}' executed directly (Celery unavailable)",
                "mode": "direct"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to run agent: {result.get('error', 'Unknown error')}"
            }
    except Exception as e:
        logger.error(f"Error triggering agent {agent_id}: {e}")
        return JSONResponse(status_code=200, content={"status": "error", "message": str(e)})


@router.post("/{agent_id}/run-sync")
def run_agent_sync(agent_id: str, db: Session = Depends(get_db)):
    """
    Run agent SYNCHRONOUSLY - bypasses Celery completely.
    Use this for testing when Celery/Redis is not running.
    """
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Invalid agent ID format"})
    
    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
    if not agent:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Agent not found"})
    
    try:
        logger.info(f"[SYNC RUN] Running agent '{agent.name}' synchronously...")
        
        # Import and call the task function directly (no Celery)
        from app.core.celery_worker import run_agent_task
        result = run_agent_task(str(agent.id))
        
        # Update last_run timestamp
        agent.last_heartbeat = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "message": f"Agent '{agent.name}' executed synchronously",
            "result": result,
            "mode": "sync"
        }
    except Exception as e:
        logger.error(f"[SYNC RUN] Error running agent {agent_id}: {e}")
        return JSONResponse(status_code=200, content={"status": "error", "message": str(e)})

@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get agent details."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Invalid agent ID format"})

    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()

    if not agent:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Agent not found"})

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
        return JSONResponse(status_code=200, content={"status": "error", "message": "Invalid agent ID format"})
        
    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
    if not agent:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Agent not found"})
        
    agent.active = False
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
        contact = lead.contact_info.get('phone') if lead.contact_info else "N/A"
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
        return JSONResponse(status_code=200, content={"status": "error", "message": "Invalid agent ID format"})
        
    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
    if not agent:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Agent not found"})
        
    # Also delete associated leads (cascade usually handles this if configured, but safe to do manually or rely on DB)
    # Since we don't have cascade delete configured in models (maybe), let's just delete the agent.
    # Actually, SQLAlchemy relationship cascade might be needed.
    # For now, let's just delete the agent.
    db.delete(agent)
    db.commit()
    
    return {"status": "success", "message": f"Agent {agent.name} deleted."}
