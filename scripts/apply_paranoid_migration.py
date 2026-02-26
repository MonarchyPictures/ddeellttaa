import sqlite3
import os

DB_PATH = "intent_radar.db"

def migrate():
    print(f"Applying PARANOID migration to {DB_PATH}...")
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Add last_heartbeat to agents
    try:
        cursor.execute("PRAGMA table_info(agents)")
        columns = [row[1] for row in cursor.fetchall()]
        if "last_heartbeat" not in columns:
            cursor.execute("ALTER TABLE agents ADD COLUMN last_heartbeat DATETIME")
            print("Added last_heartbeat column to agents.")
        else:
            print("last_heartbeat column already exists in agents.")
    except Exception as e:
        print(f"Error adding last_heartbeat: {e}")

    # 2. Ensure Unique Constraint on source_url in leads
    # First, check if index exists
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='uix_source_url'")
        if not cursor.fetchone():
            print("Index uix_source_url not found. checking for duplicates...")
            
            # Find duplicates based on source_url
            cursor.execute("""
                SELECT source_url, COUNT(*)
                FROM leads
                WHERE source_url IS NOT NULL AND source_url != ''
                GROUP BY source_url
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            
            if duplicates:
                print(f"Found {len(duplicates)} duplicate source_urls. Cleaning up...")
                for url, count in duplicates:
                    # Keep the latest one (by created_at or rowid)
                    # Delete all but the one with max rowid
                    cursor.execute("""
                        DELETE FROM leads 
                        WHERE source_url = ? 
                        AND rowid NOT IN (
                            SELECT MAX(rowid) 
                            FROM leads 
                            WHERE source_url = ?
                        )
                    """, (url, url))
                print("Duplicates cleaned up.")

            # Create the unique index
            cursor.execute("CREATE UNIQUE INDEX uix_source_url ON leads(source_url)")
            print("Created unique index uix_source_url.")
        else:
            print("Unique index uix_source_url already exists.")
            
    except Exception as e:
        print(f"Error managing uix_source_url: {e}")

    conn.commit()
    conn.close()
    print("Paranoid Migration complete.")

if __name__ == "__main__":
    migrate()
