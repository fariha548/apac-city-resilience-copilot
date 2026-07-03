import sqlite3

conn = sqlite3.connect('app/db/resilience.db')
c = conn.cursor()

migrations = [
    "ALTER TABLE hazard_reports ADD COLUMN hitl_status TEXT DEFAULT 'pending_review'",
    "ALTER TABLE hazard_reports ADD COLUMN approved_by TEXT",
    "ALTER TABLE hazard_reports ADD COLUMN approved_at TIMESTAMP",
    "ALTER TABLE hazard_reports ADD COLUMN latitude REAL",
    "ALTER TABLE hazard_reports ADD COLUMN longitude REAL",
]

for sql in migrations:
    try:
        c.execute(sql)
        print(f"OK: {sql}")
    except sqlite3.OperationalError as e:
        print(f"SKIPPED (likely already exists): {sql} -- {e}")

c.execute("UPDATE hazard_reports SET hitl_status = 'auto_approved' WHERE verified = 1 AND hitl_status = 'pending_review'")
conn.commit()
conn.close()
print("Migration done")