import json
from app.db.database import get_connection


def get_priority(score, is_anomaly):
    """Map risk score to priority bucket."""
    if is_anomaly or score >= 0.5:
        return "immediate"
    elif score >= 0.35:
        return "24h"
    else:
        return "monitor"


def generate_actions(ward_name, score, is_anomaly, anomaly_reason, key_drivers_json):
    """Generate action list based on risk score and key drivers."""
    drivers = json.loads(key_drivers_json)
    raw = drivers["raw_inputs"]
    actions = []

    priority = get_priority(score, is_anomaly)

    if is_anomaly:
        actions.append(f"URGENT: Investigate anomalous rainfall spike — {anomaly_reason}")

    if priority == "immediate":
        actions.append(f"Deploy emergency drainage pumps to {ward_name}")
        actions.append(f"Pre-position relief stock and rescue teams")
        if raw["recent_incidents_30d"] > 3:
            actions.append(f"Issue public flood warning — {raw['recent_incidents_30d']} incidents in last 30 days")

    elif priority == "24h":
        actions.append(f"Clear and inspect drainage channels in {ward_name}")
        actions.append(f"Alert local emergency response team to standby")

    else:
        actions.append(f"Continue routine monitoring for {ward_name}")

    # Driver-specific actions
    if drivers["drainage_contribution"] > 0.15:
        actions.append("Prioritize drainage infrastructure maintenance — low capacity is a key risk driver")

    if drivers["water_proximity_contribution"] > 0.10:
        actions.append("Monitor nearby water body levels closely")

    return actions, priority


def run_recommendations():
    conn = get_connection()

    # Get latest risk score per ward
    rows = conn.execute("""
        SELECT rs.*, w.ward_name
        FROM risk_scores rs
        JOIN wards w ON rs.ward_id = w.ward_id
        WHERE rs.id IN (
            SELECT MAX(id) FROM risk_scores GROUP BY ward_id
        )
    """).fetchall()

    total_actions = 0
    for row in rows:
        actions, priority = generate_actions(
            row["ward_name"], row["flood_risk_score"], row["is_anomaly"],
            row["anomaly_reason"], row["key_drivers"]
        )
        for action_text in actions:
            conn.execute("""
                INSERT INTO recommendations
                (ward_id, risk_score_id, action_text, priority, hitl_status)
                VALUES (?, ?, ?, ?, 'pending')
            """, (row["ward_id"], row["id"], action_text, priority))
            total_actions += 1

    conn.commit()
    conn.close()
    print(f"Generated {total_actions} recommendations across {len(rows)} wards (status: pending HITL approval).")


if __name__ == "__main__":
    run_recommendations()