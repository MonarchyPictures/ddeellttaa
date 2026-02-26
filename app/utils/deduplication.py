import hashlib
import logging

logger = logging.getLogger(__name__)

def generate_lead_hash(agent_id, title, content, url):
    """
    Generate a unique hash for a lead based on its core content.
    This helps in identifying duplicate leads.
    """
    # Create a string combining the fields
    # Use empty strings for None values to ensure stability
    unique_string = f"{agent_id}-{title or ''}-{content or ''}-{url or ''}"
    
    # Generate SHA-256 hash
    return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()

def is_duplicate(db, agent_id, url=None, phone=None, lead_hash=None):
    """
    Check if a lead already exists based on:
    1. URL + Agent ID
    2. Phone + Agent ID
    3. Content Hash
    """
    from app.models.lead import Lead
    
    # Check 1: URL + Agent ID (if URL exists)
    if url:
        existing = db.query(Lead).filter(
            Lead.agent_id == agent_id,
            Lead.source_url == url
        ).first()
        if existing:
            return True, "URL duplicate"

    # Check 2: Phone + Agent ID (if Phone exists)
    if phone:
        existing = db.query(Lead).filter(
            Lead.agent_id == agent_id,
            Lead.contact_phone == phone
        ).first()
        if existing:
            return True, "Phone duplicate"

    # Check 3: Content Hash (if Hash provided)
    if lead_hash:
        existing = db.query(Lead).filter(
            Lead.content_hash == lead_hash
        ).first()
        if existing:
            return True, "Content duplicate"
            
    return False, None

class Deduplicator:
    def deduplicate(self, leads):
        """
        Deduplicate a list of lead dictionaries in memory.
        """
        if not leads:
            return []
            
        seen_hashes = set()
        seen_urls = set()
        unique_leads = []
        
        for lead in leads:
            # Generate a temporary hash for in-memory dedupe if not present
            # Assuming lead is a dict here
            lead_url = lead.get('url') or lead.get('source_url')
            
            if lead_url and lead_url in seen_urls:
                continue
                
            # If we have a hash, check it
            # If not, generate one
            # Note: agent_id might not be in lead dict yet if it's raw scraper output
            # But we can use title/content
            
            # Simple content hash for in-memory
            content_sig = f"{lead.get('title')}-{lead.get('content')}"
            content_hash = hashlib.md5(content_sig.encode()).hexdigest()
            
            if content_hash in seen_hashes:
                continue
                
            seen_hashes.add(content_hash)
            if lead_url:
                seen_urls.add(lead_url)
                
            unique_leads.append(lead)
            
        logger.info(f"Deduplicated {len(leads)} leads to {len(unique_leads)}")
        return unique_leads

def get_deduplicator():
    return Deduplicator()
