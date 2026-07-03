import random
from datetime import date, timedelta
from app.db.database import get_connection
from app.agents.risk_agent import run_risk_analysis

# Fills in the fields add_new_wards.py didn't set — risk_agent.py needs ALL of
# these (drainage_capacity_index, elevation_m, proximity_water_body_km) or it
# will crash on `1 - ward["drainage_capacity_index"]` against a None value.
NEW_WARDS_PROFILE = {
    "KHI-13": {  # Gulzar-e-Hijri (Scheme 33) — newer, higher elevation, better planned
        "population": 400000, "drainage_capacity_index": 0.50,
        "elevation_m": 35, "proximity_water_body_km": 4.5, "hospital_count": 2,
    },
    "KHI-14": {  # Nazimabad — older, denser, lower elevation
        "population": 600000, "drainage_capacity_index": 0.32,
        "elevation_m": 16, "proximity_water_body_km": 3.0, "hospital_count": 3,
    },
}

# Only Nazimabad gets the high-risk incident-probability treatment — Gulzar-e-Hijri's
# elevation/drainage profile alone should keep its computed score naturally lower,
# matching how seed_data.py treats its HIGH_RISK_WARDS set.
HIGH_RISK_NEW = {"KHI-14"}


def update_ward_profiles(conn):
    cursor = conn.cursor()
    for ward_id, p in NEW_WARDS_PROFILE.items():
        cursor.execute("""
            UPDATE wards SET population=?, drainage_capacity_index=?, elevation_m=?,
                              proximity_water_body_km=?, hospital_count=?
            WHERE ward_id=?
        """, (p["population"], p["drainage_capacity_index"], p["elevation_m"],
              p["proximity_water_body_km"], p["hospital_count"], ward_id))
    conn.commit()
    print(f"Updated profile fields for {len(NEW_WARDS_PROFILE)} wards.")


def seed_weather_and_incidents(conn):
    """Exact same distribution logic as seed_data.py's seed_weather_and_incidents,
    just scoped to the 2 new wards so the risk computation is comparable/consistent
    with the rest of the dataset rather than using different random parameters."""
    cursor = conn.cursor()
    today = date.today()
    start_date = today - timedelta(days=90)
    weather_count = 0
    incident_count = 0

    for ward_id in NEW_WARDS_PROFILE:
        is_high_risk = ward_id in HIGH_RISK_NEW
        current = start_date
        while current <= today:
            base_rainfall = random.uniform(0, 15)
            if random.random() < 0.08:
                base_rainfall += random.uniform(40, 90)

            forecast_24h = base_rainfall * random.uniform(0.8, 1.3)
            forecast_72h = base_rainfall * random.uniform(1.5, 2.5)
            temp = random.uniform(26, 40)

            cursor.execute("""
                INSERT INTO weather_forecast
                (ward_id, forecast_date, rainfall_mm, rainfall_forecast_24h, rainfall_forecast_72h, temperature_c)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ward_id, current.isoformat(), round(base_rainfall, 1),
                  round(forecast_24h, 1), round(forecast_72h, 1), round(temp, 1)))
            weather_count += 1

            incident_chance = 0.35 if (is_high_risk and base_rainfall > 40) else 0.05
            if random.random() < incident_chance:
                severity = random.choices(["low", "medium", "high"], weights=[0.4, 0.35, 0.25])[0]
                incident_type = random.choice(["flood", "drainage_block", "road_closure"])
                cursor.execute("""
                    INSERT INTO incidents (ward_id, incident_date, incident_type, severity)
                    VALUES (?, ?, ?, ?)
                """, (ward_id, current.isoformat(), incident_type, severity))
                incident_count += 1

            current += timedelta(days=1)

    conn.commit()
    print(f"Seeded {weather_count} weather records and {incident_count} incidents for new wards.")


def main():
    conn = get_connection()
    update_ward_profiles(conn)
    seed_weather_and_incidents(conn)
    conn.close()

    # This calls the REAL risk_agent — not a fake/placeholder score. It runs for
    # ALL 18 wards (adds one new historical risk_scores row per ward, which is
    # harmless: every query in the app already takes the latest row per ward_id).
    print("\nComputing risk via risk_agent for all wards...")
    results = run_risk_analysis()
    results.sort(key=lambda r: r["flood_risk_score"], reverse=True)
    print(f"\nDone — {len(results)} wards scored. New wards:")
    for r in results:
        if r["ward_id"] in NEW_WARDS_PROFILE:
            flag = " ⚠ ANOMALY" if r["is_anomaly"] else ""
            print(f"  {r['ward_id']}: score={r['flood_risk_score']}, trend={r['trend_direction']}{flag}")


if __name__ == "__main__":
    main()