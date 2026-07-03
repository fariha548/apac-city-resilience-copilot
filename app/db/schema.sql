CREATE TABLE IF NOT EXISTS wards (
    ward_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    ward_name TEXT,
    population INTEGER,
    drainage_capacity_index REAL,
    elevation_m REAL,
    proximity_water_body_km REAL,
    hospital_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS weather_forecast (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ward_id TEXT,
    forecast_date DATE,
    rainfall_mm REAL,
    rainfall_forecast_24h REAL,
    rainfall_forecast_72h REAL,
    temperature_c REAL,
    FOREIGN KEY (ward_id) REFERENCES wards(ward_id)
);

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ward_id TEXT,
    incident_date DATE,
    incident_type TEXT,
    severity TEXT,
    FOREIGN KEY (ward_id) REFERENCES wards(ward_id)
);

CREATE TABLE IF NOT EXISTS risk_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ward_id TEXT,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    flood_risk_score REAL,
    is_anomaly BOOLEAN,
    anomaly_reason TEXT,
    key_drivers TEXT,
    predicted_risk_3day REAL,
    trend_direction TEXT,
    FOREIGN KEY (ward_id) REFERENCES wards(ward_id)
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ward_id TEXT,
    risk_score_id INTEGER,
    action_text TEXT,
    priority TEXT,
    hitl_status TEXT DEFAULT 'pending',
    approved_by TEXT,
    approved_at TIMESTAMP,
    FOREIGN KEY (ward_id) REFERENCES wards(ward_id),
    FOREIGN KEY (risk_score_id) REFERENCES risk_scores(id)
);

CREATE TABLE IF NOT EXISTS hazard_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ward_id TEXT,
    hazard_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT,
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified BOOLEAN DEFAULT 0,
    FOREIGN KEY (ward_id) REFERENCES wards(ward_id)
);