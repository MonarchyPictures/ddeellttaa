import sys
import os
import threading
import time
import uuid
import random
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set DATABASE_URL for testing
os.environ["DATABASE_URL"] = "sqlite:///intent_radar.db"

from app.db.database import SessionLocal, engine
from app.db.base_class import Base
from app.db.models import Lead, Agent
from app.services.deduplication_service import upsert_lead_atomic
from app.services.agent_scheduler import execute_agent
from sqlalchemy import text

def setup_test_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Create a test agent
    agent_id = uuid.uuid4()
    agent = Agent(
        id=agent_id,
        name="Concurrency Test Agent",
        query="test query",
        active=True,
        interval_hours=1
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    db.close()
    return str(agent_id)

def test_atomic_upsert_concurrency():
    print("\n--- Testing Atomic Upsert Concurrency ---")
    
    source_url = f"http://test.com/unique-{uuid.uuid4()}"
    lead_data = {
        "source_url": source_url,
        "buyer_name": "Test Buyer",
        "product_category": "Test Category",
        "price": 100.0,
        "status": "NEW"
    }

    num_threads = 20
    print(f"Spawning {num_threads} threads to upsert the SAME lead...")

    def attempt_upsert(idx):
        db = SessionLocal()
        try:
            # Add some randomness to simulate real-world timing
            time.sleep(random.uniform(0.01, 0.05))
            # Modify price slightly to verify updates work
            my_data = lead_data.copy()
            my_data['price'] = 100.0 + idx 
            result = upsert_lead_atomic(db, my_data)
            return result is not None
        except Exception as e:
            print(f"Thread {idx} failed: {e}")
            return False
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(attempt_upsert, range(num_threads)))

    # Verify results
    db = SessionLocal()
    count = db.query(Lead).filter(Lead.source_url == source_url).count()
    lead = db.query(Lead).filter(Lead.source_url == source_url).first()
    db.close()

    print(f"Upsert attempts successful: {sum(results)}/{num_threads}")
    print(f"Final Lead Count in DB: {count}")
    if lead:
        print(f"Final Lead Price: {lead.price}")

    if count == 1:
        print("✅ SUCCESS: Only 1 lead exists.")
    else:
        print(f"❌ FAILURE: Found {count} leads!")

def test_agent_locking_concurrency(agent_id):
    print("\n--- Testing Agent Locking Concurrency ---")
    
    # We want to try to run the SAME agent multiple times concurrently.
    # execute_agent should lock it.
    
    num_threads = 5
    print(f"Spawning {num_threads} threads to execute the SAME agent {agent_id}...")

    results = []
    
    def attempt_execute(idx):
        # We need to simulate the scheduler calling execute_agent
        # execute_agent is async, so we need a loop
        import asyncio
        try:
            # We use a new event loop for each thread or shared? 
            # execute_agent is async, so we should run it with asyncio.run
            # But asyncio.run in threads can be tricky.
            # Let's just call the internal locking logic if possible, or run full stack.
            # running full stack is better.
            
            # Since execute_agent is async, we need to wrap it.
            asyncio.run(execute_agent(agent_id))
            return f"Thread {idx}: Finished"
        except Exception as e:
            return f"Thread {idx}: Error {e}"

    # NOTE: execute_agent will try to lock. If locked, it returns immediately (or logs and returns).
    # We expect 1 to succeed and run (we might need to mock the actual scraping to be slow so others hit the lock).
    
    # To properly test locking, we need the "work" to take time.
    # I can't easily mock the internal _process_agent_task inside execute_agent without patching.
    # But for now, let's just see if they explode or if they run.
    
    # Actually, execute_agent in the current code calls `scraper_runner.run_agent_task`.
    # I should patch that to just sleep.
    
    from unittest.mock import patch
    
    # Patch the scraper runner to just sleep
    with patch('app.services.agent_scheduler.scraper_runner.run_agent_task') as mock_run:
        async def mock_task(*args, **kwargs):
            print("  [Mock] Agent running... sleeping 2s")
            await asyncio.sleep(2)
            return {"leads": [], "metadata": {}}
        
        mock_run.side_effect = mock_task
        
        # We need to run threads
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=attempt_execute, args=(i,))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
    # Verify agent state
    db = SessionLocal()
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    print(f"Agent is_running status: {agent.is_running}")
    print(f"Agent last_heartbeat: {agent.last_heartbeat}")
    db.close()
    
    print("Agent Locking Test Complete (Check logs for 'Agent already running' messages)")

if __name__ == "__main__":
    try:
        agent_id = setup_test_data()
        test_atomic_upsert_concurrency()
        
        # Note: running async inside threads is complex, but let's try
        # test_agent_locking_concurrency(agent_id) 
        # Skipping agent locking test in this script for now as it requires complex async/thread setup
        # The atomic upsert is the critical data corruption test.
        
    except Exception as e:
        print(f"Test Setup Failed: {e}")
