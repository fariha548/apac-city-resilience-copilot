import random
from datetime import date, timedelta
from app.db.database import get_connection, init_db

# 12 Karachi wards with realistic profiles
WARDS = [
    {"ward_id": "KHI-01", "ward_name": "Lyari", "population": 850000, "drainage_capacity_index": 0.25, "elevation_m": 8, "proximity_water_body_km": 0.5, "hospital_count": 2},
    {"ward_id": "KHI-02", "ward_name": "Korangi", "population": 700000, "drainage_capacity_index": 0.30, "elevation_m": 10, "proximity_water_body_km": 1.2, "hospital_count": 3},
    {"ward_id": "KHI-03", "ward_name": "Malir", "population": 600000, "drainage_capacity_index": 0.35, "elevation_m": 15, "proximity_water_body_km": 2.0, "hospital_count": 2},
    {"ward_id": "KHI-04", "ward_name": "Saddar", "population": 400000, "drainage_capacity_index": 0.55, "elevation_m": 20, "proximity_water_body_km": 3.5, "hospital_count": 5},
    {"ward_id": "KHI-05", "ward_name": "Clifton", "population": 300000, "drainage_capacity_index": 0.70, "elevation_m": 12, "proximity_water_body_km": 0.3, "hospital_count": 4},
    {"ward_id": "KHI-06", "ward_name": "Gulshan-e-Iqbal", "population": 900000, "drainage_capacity_index": 0.45, "elevation_m": 25, "proximity_water_body_km": 4.0, "hospital_count": 6},
    {"ward_id": "KHI-07", "ward_name": "North Nazimabad", "population": 750000, "drainage_capacity_index": 0.40, "elevation_m": 22, "proximity_water_body_km": 5.0, "hospital_count": 3},
    {"ward_id": "KHI-08", "ward_name": "Landhi", "population": 650000, "drainage_capacity_index": 0.20, "elevation_m": 9, "proximity_water_body_km": 1.5, "hospital_count": 1},
    {"ward_id": "KHI-09", "ward_name": "Orangi Town", "population": 950000, "drainage_capacity_index": 0.22, "elevation_m": 30, "proximity_water_body_km": 3.0, "hospital_count": 2},
    {"ward_id": "KHI-10", "ward_name": "Baldia Town", "population": 550000, "drainage_capacity_index": 0.28, "elevation_m": 18, "proximity_water_body_km": 2.5, "hospital_count": 1},
    {"ward_id": "KHI-11", "ward_name": "Defence (DHA)", "population": 250000, "drainage_capacity_index": 0.75, "elevation_m": 14, "proximity_water_body_km": 0.8, "hospital_count": 5},
    {"ward_id": "KHI-12", "ward_name": "Shah Faisal Town", "population": 500000, "drainage_capacity_index": 0.33, "elevation_m": 11, "proximity_water_body_km": 1.8, "hospital_count": 2},
]

CITY_ID = "karachi"

# Wards with poor drainage + low elevation = higher baseline flood tendency
HIGH_RISK_WARDS = {"KHI-01", "KHI-02", "KHI-08", "KHI-09", "KHI-10"}


def seed_wards(conn):
    cursor = conn.cursor()
    for w in WARDS:
        cursor.execute("""
            INSERT OR REPLACE INTO wards
            (ward_id, city_id, ward_name, population, drainage_capacity_index, elevation_m, proximity_water_body_km, hospital_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (w["ward_id"], CITY_ID, w["ward_name"], w["population"], w["drainage_capacity_index"],
              w["elevation_m"], w["proximity_water_body_km"], w["hospital_count"]))
    conn.commit()
    print(f"Seeded {len(WARDS)} wards.")


def seed_weather_and_incidents(conn):
    cursor = conn.cursor()
    today = date.today()
    start_date = today - timedelta(days=90)

    incident_count = 0
    weather_count = 0

    for w in WARDS:
        is_high_risk = w["ward_id"] in HIGH_RISK_WARDS
        current = start_date
        while current <= today:
            # Base rainfall with occasional monsoon spikes
            base_rainfall = random.uniform(0, 15)
            if random.random() < 0.08:  # ~8% chance of heavy rain event
                base_rainfall += random.uniform(40, 90)

            forecast_24h = base_rainfall * random.uniform(0.8, 1.3)
            forecast_72h = base_rainfall * random.uniform(1.5, 2.5)
            temp = random.uniform(26, 40)

            cursor.execute("""
                INSERT INTO weather_forecast
                (ward_id, forecast_date, rainfall_mm, rainfall_forecast_24h, rainfall_forecast_72h, temperature_c)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (w["ward_id"], current.isoformat(), round(base_rainfall, 1),
                  round(forecast_24h, 1), round(forecast_72h, 1), round(temp, 1)))
            weather_count += 1

            # Incident probability higher for high-risk wards during heavy rain
            incident_chance = 0.35 if (is_high_risk and base_rainfall > 40) else 0.05
            if random.random() < incident_chance:
                severity = random.choices(["low", "medium", "high"], weights=[0.4, 0.35, 0.25])[0]
                incident_type = random.choice(["flood", "drainage_block", "road_closure"])
                cursor.execute("""
                    INSERT INTO incidents (ward_id, incident_date, incident_type, severity)
                    VALUES (?, ?, ?, ?)
                """, (w["ward_id"], current.isoformat(), incident_type, severity))
                incident_count += 1

            current += timedelta(days=1)

    conn.commit()
    print(f"Seeded {weather_count} weather records and {incident_count} incidents.")

    # --- Second city: Manila (proves multi-city scalability) ---
MANILA_CITY_ID = "manila"

MANILA_WARDS = [
    {"ward_id": "MNL-01", "ward_name": "Tondo", "population": 630000, "drainage_capacity_index": 0.20, "elevation_m": 5, "proximity_water_body_km": 0.3, "hospital_count": 2},
    {"ward_id": "MNL-02", "ward_name": "Malabon", "population": 380000, "drainage_capacity_index": 0.18, "elevation_m": 3, "proximity_water_body_km": 0.5, "hospital_count": 1},
    {"ward_id": "MNL-03", "ward_name": "Marikina", "population": 450000, "drainage_capacity_index": 0.40, "elevation_m": 12, "proximity_water_body_km": 1.0, "hospital_count": 3},
    {"ward_id": "MNL-04", "ward_name": "Makati CBD", "population": 200000, "drainage_capacity_index": 0.65, "elevation_m": 15, "proximity_water_body_km": 2.5, "hospital_count": 5},
]

MANILA_HIGH_RISK_WARDS = {"MNL-01", "MNL-02"}


def seed_manila_wards(conn):
    cursor = conn.cursor()
    for w in MANILA_WARDS:
        cursor.execute("""
            INSERT OR REPLACE INTO wards
            (ward_id, city_id, ward_name, population, drainage_capacity_index, elevation_m, proximity_water_body_km, hospital_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (w["ward_id"], MANILA_CITY_ID, w["ward_name"], w["population"], w["drainage_capacity_index"],
              w["elevation_m"], w["proximity_water_body_km"], w["hospital_count"]))
    conn.commit()
    print(f"Seeded {len(MANILA_WARDS)} Manila wards.")


def seed_manila_weather_and_incidents(conn):
    import random
    from datetime import date, timedelta
    cursor = conn.cursor()
    today = date.today()
    start_date = today - timedelta(days=90)

    weather_count = 0
    incident_count = 0

    for w in MANILA_WARDS:
        is_high_risk = w["ward_id"] in MANILA_HIGH_RISK_WARDS
        current = start_date
        while current <= today:
            base_rainfall = random.uniform(0, 18)
            if random.random() < 0.10:
                base_rainfall += random.uniform(50, 100)

            forecast_24h = base_rainfall * random.uniform(0.8, 1.3)
            forecast_72h = base_rainfall * random.uniform(1.5, 2.5)
            temp = random.uniform(27, 35)

            cursor.execute("""
                INSERT INTO weather_forecast
                (ward_id, forecast_date, rainfall_mm, rainfall_forecast_24h, rainfall_forecast_72h, temperature_c)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (w["ward_id"], current.isoformat(), round(base_rainfall, 1),
                  round(forecast_24h, 1), round(forecast_72h, 1), round(temp, 1)))
            weather_count += 1

            incident_chance = 0.35 if (is_high_risk and base_rainfall > 40) else 0.05
            if random.random() < incident_chance:
                severity = random.choices(["low", "medium", "high"], weights=[0.4, 0.35, 0.25])[0]
                incident_type = random.choice(["flood", "drainage_block", "road_closure"])
                cursor.execute("""
                    INSERT INTO incidents (ward_id, incident_date, incident_type, severity)
                    VALUES (?, ?, ?, ?)
                """, (w["ward_id"], current.isoformat(), incident_type, severity))
                incident_count += 1

            current += timedelta(days=1)

    conn.commit()
    print(f"Seeded {weather_count} Manila weather records and {incident_count} incidents.")


def run_seed():
    init_db()
    conn = get_connection()
    seed_wards(conn)
    seed_weather_and_incidents(conn)
    seed_manila_wards(conn)
    seed_manila_weather_and_incidents(conn)
    conn.close()
    print("Seeding complete.")


if __name__ == "__main__":
    run_seed()