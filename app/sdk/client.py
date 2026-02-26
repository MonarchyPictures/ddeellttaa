import os
import logging
import asyncio
from typing import List, Dict, Optional, Union, Any
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.pipeline import LeadPipeline
from app.scrapers import run_scrapers
from app.models.lead import Lead
from app.scrapers.registry import update_scraper_state, get_active_scrapers, SCRAPER_REGISTRY

# Configure logging to be less verbose for SDK users by default
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Delta9SDK")

class Delta9:
    """
    Delta9 Intelligence SDK
    
    Programmatic interface to the Delta9 lead generation engine.
    Allows running searches, managing scrapers, and retrieving leads.
    """
    
    def __init__(self, db: Session = None):
        """
        Initialize the Delta9 SDK.
        
        Args:
            db (Session, optional): SQLAlchemy database session. If None, a new session is created.
        """
        self._db = db or SessionLocal()
        self.pipeline = LeadPipeline(self._db)
        
    def search(self, query: str, location: str = "Kenya", save: bool = True, limit: int = 10, category: str = "general") -> List[Lead]:
        """
        Run a live search for leads.
        
        Args:
            query (str): The search query (e.g., "looking for maize").
            location (str): The target location.
            save (bool): Whether to save the found leads to the database.
            limit (int): Maximum number of leads to return.
            category (str): Product category.
            
        Returns:
            List[Lead]: A list of Lead objects found.
        """
        logger.info(f"SDK: Searching for '{query}' in '{location}'...")
        
        # Fetch raw results using the ingestion engine
        # We use Tier 2 (Full) by default for SDK to get best results
        raw_results = asyncio.run(run_scrapers(query, location))
        
        logger.info(f"SDK: Found {len(raw_results)} raw signals.")
        
        leads: List[Lead] = []
        for res in raw_results:
            lead = self.pipeline.process_raw_lead(res)
            if lead:
                leads.append(lead)
                
        if save and leads:
            self.pipeline.save_leads(leads)
            logger.info(f"SDK: Saved {len(leads)} leads to database.")
            
        return leads[:limit]

    def get_leads(self, limit: int = 100, verified_only: bool = False) -> List[Lead]:
        """
        Retrieve existing leads from the database.
        
        Args:
            limit (int): Max leads to return.
            verified_only (bool): If True, only return verified leads.
            
        Returns:
            List[Lead]: List of leads from DB.
        """
        query = self._db.query(Lead).order_by(Lead.created_at.desc())
        
        if verified_only:
            query = query.filter(Lead.is_verified_signal == 1)
            
        return query.limit(limit).all()

    def get_scrapers(self) -> Dict[str, Any]:
        """
        Get the status of all registered scrapers.
        """
        return SCRAPER_REGISTRY

    def enable_scraper(self, name: str) -> bool:
        """
        Enable a specific scraper.
        """
        success, msg = update_scraper_state(name, True)
        logger.info(msg)
        return success

    def disable_scraper(self, name: str) -> bool:
        """
        Disable a specific scraper.
        """
        success, msg = update_scraper_state(name, False)
        logger.info(msg)
        return success

    def close(self):
        """
        Close the database session.
        """
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
