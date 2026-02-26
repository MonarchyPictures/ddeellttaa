import sqlite3
import os

def check_db():
    db_path = 'intent_radar.db'
    if not os.path.exists(db_path):
        print("DB not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT count(*) FROM leads")
    count = cursor.fetchone()[0]
    print(f"Total leads: {count}")
    
    cursor.execute("SELECT intent_type, count(*) FROM leads GROUP BY intent_type")
    print("Intent types:")
    for row in cursor.fetchall():
        print(f" - {row[0]}: {row[1]}")
        
    cursor.execute("SELECT buyer_request_snippet, intent_type FROM leads ORDER BY timestamp DESC LIMIT 5")
    print("\nLatest 5 leads:")
    for row in cursor.fetchall():
        print(f"[{row[1]}] {row[0][:100]}...")
        
    conn.close()

if __name__ == "__main__":
    check_db()
