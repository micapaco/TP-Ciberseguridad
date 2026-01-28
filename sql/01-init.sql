-- Tabla de eventos crudos (auditoría completa)
CREATE TABLE IF NOT EXISTS events_raw (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP NOT NULL DEFAULT NOW(),
    host VARCHAR(120),
    source VARCHAR(120),
    severity VARCHAR(20),
    message TEXT,
    json_raw JSONB
);

CREATE INDEX idx_events_raw_ts ON events_raw(ts DESC);
CREATE INDEX idx_events_raw_host ON events_raw(host);

-- Tabla de alertas procesadas
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP DEFAULT NOW(),
    rule_id VARCHAR(120) NOT NULL,
    src_ip VARCHAR(60),
    username VARCHAR(120),
    severity VARCHAR(20),
    raw JSONB,
    status VARCHAR(30) DEFAULT 'new'
);

CREATE INDEX idx_alerts_ts ON alerts(ts DESC);
CREATE INDEX idx_alerts_rule_id ON alerts(rule_id);
CREATE INDEX idx_alerts_src_ip ON alerts(src_ip);

-- Tabla de ejecuciones de playbooks
CREATE TABLE IF NOT EXISTS playbook_runs (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alerts(id),
    workflow VARCHAR(120),
    outcome VARCHAR(60),
    evidence JSONB,
    executed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_playbook_runs_alert_id ON playbook_runs(alert_id);
CREATE INDEX idx_playbook_runs_executed_at ON playbook_runs(executed_at DESC);

-- Vista para cálculo de MTTR
CREATE OR REPLACE VIEW mttr_stats AS
SELECT 
    a.id AS alert_id,
    a.rule_id,
    a.severity,
    a.ts AS alert_time,
    p.executed_at AS response_time,
    EXTRACT(EPOCH FROM (p.executed_at - a.ts)) AS mttr_seconds
FROM alerts a
JOIN playbook_runs p ON p.alert_id = a.id
ORDER BY a.id DESC;

-- Vista para alertas por severidad
CREATE OR REPLACE VIEW alerts_by_severity AS
SELECT 
    DATE(ts) AS alert_date,
    severity,