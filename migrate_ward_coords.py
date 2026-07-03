import sqlite3

conn = sqlite3.connect('app/db/resilience.db')
c = conn.cursor()

# Add columns (safe to skip if already run once)
for col in ["latitude REAL", "longitude REAL"]:
    try:
        c.execute(f"ALTER TABLE wards ADD COLUMN {col}")
        print(f"OK: added {col}")
    except sqlite3.OperationalError as e:
        print(f"SKIPPED (likely exists): {col} -- {e}")

# Approximate ward-center coordinates (real-world lookup, not random placeholders)
WARD_COORDS = {
    "KHI-01": (24.8710, 66.9891),   # Lyari
    "KHI-02": (24.8256, 67.1349),   # Korangi
    "KHI-03": (24.8955, 67.2088),   # Malir
    "KHI-04": (24.8560, 67.0100),   # Saddar
    "KHI-05": (24.8138, 67.0300),   # Clifton
    "KHI-06": (24.9200, 67.0980),   # Gulshan-e-Iqbal
    "KHI-07": (24.9342, 67.0384),   # North Nazimabad
    "KHI-08": (24.8438, 67.1899),   # Landhi
    "KHI-09": (24.9494, 66.9769),   # Orangi Town
    "KHI-10": (24.9236, 66.9634),   # Baldia Town
    "KHI-11": (24.8000, 67.0300),   # Defence (DHA)
    "KHI-12": (24.8814, 67.1808),   # Shah Faisal Town
    "MNL-01": (14.6187, 120.9673),  # Tondo
    "MNL-02": (14.6570, 120.9569),  # Malabon
    "MNL-03": (14.6507, 121.1029),  # Marikina
    "MNL-04": (14.5547, 121.0244),  # Makati CBD
}

for ward_id, (lat, lng) in WARD_COORDS.items():
    c.execute("UPDATE wards SET latitude = ?, longitude = ? WHERE ward_id = ?", (lat, lng, ward_id))

conn.commit()

# Verify
rows = c.execute("SELECT ward_id, ward_name, latitude, longitude FROM wards ORDER BY ward_id").fetchall()
for r in rows:
    print(r)

conn.close()
print("Migration done — wards now have latitude/longitude")