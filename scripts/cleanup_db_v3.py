import sqlite3
import os

db_path = 'e:/delta-9/delta-9/intent_radar.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables in {db_path}: {tables}")
    
    for table in tables:
        table_name = table[0]
        if table_name == 'sqlite_sequence': continue
        cursor.execute(f"DELETE FROM {table_name}")
        print(f"Deleted all rows from {table_name}")
    
    conn.commit()
    conn.close()
else:
    print(f"{db_path} does not exist")
