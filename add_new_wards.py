import sqlite3

conn = sqlite3.connect('app/db/resilience.db')
c = conn.cursor()

new_wards = [
    ('KHI-13', 'karachi', 'Gulzar-e-Hijri (Scheme 33)', 24.9425, 67.1223),
    ('KHI-14', 'karachi', 'Nazimabad', 24.9042, 67.0362),
]

for ward_id, city_id, ward_name, lat, lng in new_wards:
    try:
        c.execute(
            "INSERT INTO wards (ward_id, city_id, ward_name, latitude, longitude) VALUES (?, ?, ?, ?, ?)",
            (ward_id, city_id, ward_name, lat, lng)
        )
        print(f"OK: added {ward_name} ({ward_id})")
    except sqlite3.IntegrityError as e:
        print(f"SKIPPED (already exists): {ward_id} -- {e}")

conn.commit()
conn.close()
print("Done — 2 new wards added to wards table")