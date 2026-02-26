import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "intent_radar.db"

def apply_final_indexes():
    """
    Applies the missing index for 'urgency_level' to the 'leads' table.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if index exists
        cursor.execute("PRAGMA index_list(leads)")
        existing_indexes = [row[1] for row in cursor.fetchall()]
        
        index_name = "ix_leads_urgency_level"
        
        if index_name not in existing_indexes:
            logger.info(f"Creating index {index_name} on leads(urgency_level)...")
            cursor.execute(f"CREATE INDEX {index_name} ON leads(urgency_level)")
            logger.info(f"Index {index_name} created successfully.")
        else:
            logger.info(f"Index {index_name} already exists.")
            
        conn.commit()
        conn.close()
        logger.info("Final database hardening completed.")
        
    except Exception as e:
        logger.error(f"Error applying indexes: {e}")

if __name__ == "__main__":
    apply_final_indexes()
