import sqlite3
import os

# Define database path
DB_PATH = "intent_radar.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. Skipping migration (tables will be created on startup).")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        ("agent_id", "CHAR(32)"), # SQLite doesn't have UUID, so use CHAR(32) or similar. SQLAlchemy UUID maps to CHAR/BLOB in SQLite usually, but let's check.
        # Actually, SQLAlchemy UUID(as_uuid=True) stores as CHAR(32) or 16 bytes BLOB in SQLite. 
        # But wait, the existing UUIDs in other tables might be different.
        # Let's use TEXT for simplicity as SQLite is flexible, and SQLAlchemy handles conversion.
        # In `admin.py`, we saw issues with UUID strings.
        # Let's use TEXT.
        ("query", "TEXT"),
        ("location", "TEXT")
    ]

    table_name = "leads"

    # Check existing columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [info[1] for info in cursor.fetchall()]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"Adding column {col_name} to {table_name}...")
            try:
                # SQLite ALTER TABLE is limited, but ADD COLUMN is supported
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                print(f"Successfully added {col_name}.")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"Column {col_name} already exists in {table_name}.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
