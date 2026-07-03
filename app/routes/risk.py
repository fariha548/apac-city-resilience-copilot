from fastapi import APIRouter
from app.db.database import get_connection

router = APIRouter()


@router.get("/risk-dashboard")
def get_risk_dashboard():
    """Return latest risk score + status for every ward, sorted high to low."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT rs.ward_id, w.ward_name, w.latitude, w.longitude,
               rs.flood_risk_score, rs.is_anomaly, rs.anomaly_reason,
               rs.trend_direction, rs.predicted_risk_3day, rs.computed_at
        FROM risk_scores rs
        JOIN wards w ON rs.ward_id = w.ward_id
        WHERE rs.id IN (SELECT MAX(id) FROM risk_scores GROUP BY ward_id)
        ORDER BY rs.flood_risk_score DESC
    """).fetchall()
    conn.close()
    return {"wards": [dict(r) for r in rows]}


@router.get("/ward/{ward_id}")
def get_ward_detail(ward_id: str):
    """Return full detail for a single ward: profile, risk, recommendations."""
    conn = get_connection()

    ward = conn.execute("SELECT * FROM wards WHERE ward_id = ?", (ward_id,)).fetchone()
    if not ward:
        return {"error": "Ward not found"}

    risk = conn.execute("""
        SELECT * FROM risk_scores WHERE ward_id = ?
        ORDER BY id DESC LIMIT 1
    """, (ward_id,)).fetchone()

    recs = conn.execute("""
        SELECT * FROM recommendations WHERE ward_id = ?
        ORDER BY id DESC
    """, (ward_id,)).fetchall()

    conn.close()
    return {
        "ward": dict(ward),
        "risk": dict(risk) if risk else None,
        "recommendations": [dict(r) for r in recs],
    }


@router.post("/recommendation/{rec_id}/approve")
def approve_recommendation(rec_id: int, approved_by: str = "city_officer"):
    """HITL gate: approve a pending recommendation."""
    conn = get_connection()
    conn.execute("""
        UPDATE recommendations
        SET hitl_status = 'approved', approved_by = ?, approved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (approved_by, rec_id))
    conn.commit()
    conn.close()
    return {"status": "approved", "recommendation_id": rec_id}


@router.post("/recommendation/{rec_id}/reject")
def reject_recommendation(rec_id: int, approved_by: str = "city_officer"):
    """HITL gate: reject a pending recommendation."""
    conn = get_connection()
    conn.execute("""
        UPDATE recommendations
        SET hitl_status = 'rejected', approved_by = ?, approved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (approved_by, rec_id))
    conn.commit()
    conn.close()
    return {"status": "rejected", "recommendation_id": rec_id}