import sqlite3

conn = sqlite3.connect('intent_radar.db')
c = conn.cursor()

try:
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='leads'")
    res = c.fetchone()
    if res:
        print("--- LEADS TABLE ---")
        print(res[0])
    else:
        print("--- LEADS TABLE NOT FOUND ---")

    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='agents'")
    res = c.fetchone()
    if res:
        print("\n--- AGENTS TABLE ---")
        print(res[0])
    else:
        print("--- AGENTS TABLE NOT FOUND ---")

except Exception as e:
    print(f"Error: {e}")

conn.close()
