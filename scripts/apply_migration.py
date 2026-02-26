import sqlite3
import os

DB_PATH = "intent_radar.db"

def migrate():
    print(f"Applying migration to {DB_PATH}...")
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Add content_hash column if not exists
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(leads)")
        columns = [row[1] for row in cursor.fetchall()]
        if "content_hash" not in columns:
            cursor.execute("ALTER TABLE leads ADD COLUMN content_hash TEXT")
            print("Added content_hash column.")
        else:
            print("content_hash column already exists.")
    except Exception as e:
        print(f"Error checking/adding column: {e}")

    # 2. Create Unique Index (and handle duplicates)
    try:
        # Check if index exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='uix_agent_url'")
        if not cursor.fetchone():
            print("Index uix_agent_url not found. Checking for duplicates...")
            
            # Find duplicates
            cursor.execute("""
                SELECT agent_id, source_url, COUNT(*)
                FROM leads
                WHERE agent_id IS NOT NULL AND source_url IS NOT NULL
                GROUP BY agent_id, source_url
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            
            if duplicates:
                print(f"Found {len(duplicates)} duplicate sets. Cleaning up...")
                for agent_id, url, count in duplicates:
                    # Keep the latest one (by rowid)
                    # We delete all but the one with max rowid
                    cursor.execute("""
                        DELETE FROM leads 
                        WHERE agent_id = ? AND source_url = ? 
                        AND rowid NOT IN (
                            SELECT MAX(rowid) 
                            FROM leads 
                            WHERE agent_id = ? AND source_url = ?
                        )
                    """, (agent_id, url, agent_id, url))
                print("Duplicates cleaned up.")

            cursor.execute("CREATE UNIQUE INDEX uix_agent_url ON leads(agent_id, source_url)")
            print("Created unique index uix_agent_url.")
        else:
            print("Unique index uix_agent_url already exists.")
            
    except Exception as e:
        print(f"Error managing index: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()