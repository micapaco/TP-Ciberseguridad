-- ============================================
-- SIEM Database Schema
-- ============================================

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

CREATE INDEX IF NOT EXISTS idx_events_raw_ts ON events_raw(ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_raw_host ON events_raw(host);

-- Tabla de alertas procesadas
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP DEFAULT NOW(),
    rule_id VARCHAR(120) NOT NULL,
    src_ip VARCHAR(60),
    username VARCHAR(120),
    severity VARCHAR(20),
    raw JSONB,
    status VARCHAR(30) DEFAULT 'new',
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_rule_id ON alerts(rule_id);
CREATE INDEX IF NOT EXISTS idx_alerts_src_ip ON alerts(src_ip);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);

-- Tabla de ejecuciones de playbooks
CREATE TABLE IF NOT EXISTS playbook_runs (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alerts(id),
    workflow VARCHAR(120),
    outcome VARCHAR(60),
    evidence JSONB,
    executed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_playbook_runs_alert_id ON playbook_runs(alert_id);
CREATE INDEX IF NOT EXISTS idx_playbook_runs_executed_at ON playbook_runs(executed_at DESC);

-- ============================================
-- VISTAS PARA MÉTRICAS
-- ============================================

-- Vista para cálculo de MTTR (Mean Time To Respond)
CREATE OR REPLACE VIEW mttr_stats AS
SELECT 
    AVG(EXTRACT(EPOCH FROM (p.executed_at - a.ts))) AS avg_mttr_seconds,
    COUNT(*) AS total_responses
FROM alerts a
JOIN playbook_runs p ON p.alert_id = a.id;

-- Vista para cálculo de MTTA (Mean Time To Acknowledge)
CREATE OR REPLACE VIEW mtta_stats AS
SELECT 
    AVG(EXTRACT(EPOCH FROM (acknowledged_at - ts))) AS avg_mtta_seconds,
    COUNT(*) FILTER (WHERE acknowledged_at IS NOT NULL) AS acknowledged_count,
    COUNT(*) AS total_alerts
FROM alerts;

-- Vista para alertas por severidad
CREATE OR REPLACE VIEW alerts_by_severity AS
SELECT 
    DATE(ts) AS alert_date,
    severity,
    COUNT(*) AS count
FROM alerts
GROUP BY DATE(ts), severity
ORDER BY alert_date DESC, severity;

-- Vista para tasa de automatización
CREATE OR REPLACE VIEW automation_rate AS
SELECT 
    COUNT(DISTINCT p.alert_id) AS automated_alerts,
    (SELECT COUNT(*) FROM alerts) AS total_alerts,
    ROUND(COUNT(DISTINCT p.alert_id)::numeric / NULLIF((SELECT COUNT(*) FROM alerts), 0) * 100, 2) AS automation_percentage
FROM playbook_runs p;

-- Vista para top IPs sospechosas
CREATE OR REPLACE VIEW top_suspicious_ips AS
SELECT 
    src_ip,
    COUNT(*) AS alert_count
FROM alerts
WHERE src_ip IS NOT NULL
GROUP BY src_ip
ORDER BY alert_count DESC
LIMIT 10;