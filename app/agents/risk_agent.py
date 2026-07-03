import json
import statistics
from app.db.database import get_connection


def normalize(value, min_val, max_val):
    if max_val == min_val:
        return 0.0
    norm = (value - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, norm))


def get_ward_baseline_rainfall(conn, ward_id):
    rows = conn.execute(
        "SELECT rainfall_forecast_72h FROM weather_forecast WHERE ward_id = ?",
        (ward_id,)
    ).fetchall()
    values = [r["rainfall_forecast_72h"] for r in rows if r["rainfall_forecast_72h"] is not None]
    if not values:
        return 0.0
    return statistics.mean(values)


def get_latest_weather(conn, ward_id):
    row = conn.execute(
        "SELECT * FROM weather_forecast WHERE ward_id = ? ORDER BY forecast_date DESC LIMIT 1",
        (ward_id,)
    ).fetchone()
    return row


def get_recent_incident_count(conn, ward_id, days=30):
    row = conn.execute(
        """SELECT COUNT(*) as cnt FROM incidents
           WHERE ward_id = ? AND incident_date >= date('now', ?)""",
        (ward_id, f"-{days} days")
    ).fetchone()
    return row["cnt"] if row else 0

def get_rainfall_trend_and_projection(conn, ward_id):
    """
    Pure-python linear regression over historical rainfall_mm readings
    to project rainfall 3 days ahead. No numpy dependency (Cloud Run friendly).
    Returns (projected_rainfall, trend_direction) or (None, None) if insufficient data.
    """
    rows = conn.execute(
        """SELECT forecast_date, rainfall_mm FROM weather_forecast
           WHERE ward_id = ? AND rainfall_mm IS NOT NULL
           ORDER BY forecast_date DESC LIMIT 10""",
        (ward_id,)
    ).fetchall()
    rows = list(reversed(rows))  # chronological order for regression

    if len(rows) < 2:
        return None, None

    # x = day index (0, 1, 2, ...), y = rainfall_mm
    n = len(rows)
    xs = list(range(n))
    ys = [r["rainfall_mm"] for r in rows]

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    numerator = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    denominator = sum((xs[i] - mean_x) ** 2 for i in range(n))

    if denominator == 0:
        return ys[-1], "stable"

    slope = numerator / denominator
    intercept = mean_y - slope * mean_x

    projected_day = n + 2  # 3 days ahead of last known day
    projected_rainfall = max(0.0, intercept + slope * projected_day)

    if slope > 0.5:
        direction = "worsening"
    elif slope < -0.5:
        direction = "improving"
    else:
        direction = "stable"

    return round(projected_rainfall, 2), direction


def compute_risk_for_ward(conn, ward):
    ward_id = ward["ward_id"]
    latest_weather = get_latest_weather(conn, ward_id)

    if not latest_weather:
        return None

    rainfall_72h = latest_weather["rainfall_forecast_72h"] or 0
    baseline_rainfall = get_ward_baseline_rainfall(conn, ward_id)
    incident_count = get_recent_incident_count(conn, ward_id)
    projected_rainfall, trend_direction = get_rainfall_trend_and_projection(conn, ward_id)

    rainfall_norm = normalize(rainfall_72h, 0, 150)
    drainage_risk = 1 - ward["drainage_capacity_index"]
    elevation_risk = normalize(30 - ward["elevation_m"], 0, 30)
    water_proximity_risk = normalize(5 - ward["proximity_water_body_km"], 0, 5)
    incident_freq_norm = normalize(incident_count, 0, 10)

    score = (
        0.35 * rainfall_norm +
        0.25 * drainage_risk +
        0.20 * elevation_risk +
        0.15 * water_proximity_risk +
        0.05 * incident_freq_norm
    )
    score = round(min(1.0, max(0.0, score)), 3)
    predicted_risk_3day = None
    if projected_rainfall is not None:
        projected_rainfall_norm = normalize(projected_rainfall, 0, 150)
        predicted_score = (
            0.35 * projected_rainfall_norm +
            0.25 * drainage_risk +
            0.20 * elevation_risk +
            0.15 * water_proximity_risk +
            0.05 * incident_freq_norm
        )
        predicted_risk_3day = round(min(1.0, max(0.0, predicted_score)), 3)

    is_anomaly = False
    anomaly_reason = None
    if baseline_rainfall > 0 and rainfall_72h > (2 * baseline_rainfall):
        is_anomaly = True
        anomaly_reason = (
            f"72h rainfall forecast ({rainfall_72h}mm) is "
            f"{round(rainfall_72h / baseline_rainfall, 1)}x above 90-day average ({round(baseline_rainfall, 1)}mm)"
        )

    key_drivers = {
        "rainfall_contribution": round(0.35 * rainfall_norm, 3),
        "drainage_contribution": round(0.25 * drainage_risk, 3),
        "elevation_contribution": round(0.20 * elevation_risk, 3),
        "water_proximity_contribution": round(0.15 * water_proximity_risk, 3),
        "incident_history_contribution": round(0.05 * incident_freq_norm, 3),
        "raw_inputs": {
            "rainfall_forecast_72h_mm": rainfall_72h,
            "drainage_capacity_index": ward["drainage_capacity_index"],
            "elevation_m": ward["elevation_m"],
            "proximity_water_body_km": ward["proximity_water_body_km"],
            "recent_incidents_30d": incident_count,
        }
    }

    return {
        "ward_id": ward_id,
        "flood_risk_score": score,
        "is_anomaly": is_anomaly,
        "anomaly_reason": anomaly_reason,
        "key_drivers": json.dumps(key_drivers),
        "predicted_risk_3day": predicted_risk_3day,
        "trend_direction": trend_direction,
    }


def run_risk_analysis():
    conn = get_connection()
    wards = conn.execute("SELECT * FROM wards").fetchall()

    results = []
    for ward in wards:
        result = compute_risk_for_ward(conn, ward)
        if result:
            conn.execute("""
                INSERT INTO risk_scores
                (ward_id, flood_risk_score, is_anomaly, anomaly_reason, key_drivers,
                 predicted_risk_3day, trend_direction)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (result["ward_id"], result["flood_risk_score"], result["is_anomaly"],
                  result["anomaly_reason"], result["key_drivers"],
                  result["predicted_risk_3day"], result["trend_direction"]))
            results.append(result)

    conn.commit()
    conn.close()
    return results


if __name__ == "__main__":
    results = run_risk_analysis()
    results.sort(key=lambda r: r["flood_risk_score"], reverse=True)
    print(f"\nComputed risk for {len(results)} wards:\n")
    for r in results:
        flag = " ⚠ ANOMALY" if r["is_anomaly"] else ""
        print(f"{r['ward_id']}: score={r['flood_risk_score']}{flag}")
        if r["is_anomaly"]:
            print(f"   → {r['anomaly_reason']}")