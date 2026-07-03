from app.db.database import get_connection

conn = get_connection()
row = conn.execute(
    "SELECT ward_id, flood_risk_score, predicted_risk_3day, trend_direction "
    "FROM risk_scores WHERE ward_id='KHI-09' ORDER BY id DESC LIMIT 1"
).fetchall()
for r in row:
    print(dict(r))
