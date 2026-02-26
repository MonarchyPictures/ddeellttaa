from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, FileResponse, JSONResponse
import io
import os
import tempfile
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

router = APIRouter()

def enrich_agent_data(agent: Agent, db: Session) -> AgentResponse:
    # Get total leads
    leads_count = db.query(Lead).filter(Lead.agent_id == agent.id).count()
    
    # Get high intent leads (ranked_score >= 0.7)
    high_intent_count = db.query(Lead).filter(
        Lead.agent_id == agent.id, 
        Lead.ranked_score >= 0.7
    ).count()
    
    # Get last run time (latest lead creation)
    last_run = db.query(func.max(Lead.created_at)).filter(Lead.agent_id == agent.id).scalar()
    
    # Create response object manually to inject extra fields
    # Since AgentResponse is a Pydantic model, we can instantiate it with the dict from agent + extra fields
    agent_dict = agent.to_dict()
    agent_dict['id'] = uuid.UUID(agent_dict['id']) # Convert string back to UUID for Pydantic
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
    """Create a new agent."""
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

    return enrich_agent_data(agent, db)

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
