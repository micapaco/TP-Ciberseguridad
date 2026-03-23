"""
Script para generar reportes automáticos del SIEM
Consulta PostgreSQL y genera un resumen con métricas KPI
Puede ser ejecutado manualmente o desde n8n (Schedule Trigger)
"""
import psycopg2
import requests
import json
from datetime import datetime
import os

# ============================================
# CONFIGURACIÓN
# ============================================
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "siem"),
    "user": os.getenv("POSTGRES_USER", "siem"),
    "password": os.getenv("POSTGRES_PASSWORD", "siem123")
}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ============================================
# CONSULTAS SQL
# ============================================
QUERIES = {
    "total_alerts": "SELECT COUNT(*) FROM alerts",
    "alerts_last_24h": "SELECT COUNT(*) FROM alerts WHERE ts > NOW() - INTERVAL '24 hours'",
    "alerts_last_7d": "SELECT COUNT(*) FROM alerts WHERE ts > NOW() - INTERVAL '7 days'",
    "alerts_by_severity": """
        SELECT severity, COUNT(*) as count 
        FROM alerts GROUP BY severity ORDER BY count DESC
    """,
    "top_ips": """
        SELECT src_ip, COUNT(*) as count 
        FROM alerts WHERE src_ip IS NOT NULL 
        GROUP BY src_ip ORDER BY count DESC LIMIT 5
    """,
    "top_rules": """
        SELECT rule_id, COUNT(*) as count 
        FROM alerts GROUP BY rule_id ORDER BY count DESC LIMIT 5
    """,
    "mttr": "SELECT * FROM mttr_stats",
    "mtta": "SELECT * FROM mtta_stats",
    "automation_rate": "SELECT * FROM automation_rate",
    "open_incidents": "SELECT COUNT(*) FROM incidents WHERE status = 'open'",
    "total_incidents": "SELECT COUNT(*) FROM incidents",
    "failed_alerts": "SELECT COUNT(*) FROM failed_alerts WHERE resolved = false",
    "recent_critical": """
        SELECT rule_id, src_ip, username, ts 
        FROM alerts WHERE severity = 'critical' 
        ORDER BY ts DESC LIMIT 3
    """
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def execute_query(cursor, query):
    try:
        cursor.execute(query)
        return cursor.fetchall(), [desc[0] for desc in cursor.description]
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return [], []


def collect_metrics():
    metrics = {}
    conn = get_db_connection()
    cursor = conn.cursor()
    for name, query in QUERIES.items():
        rows, columns = execute_query(cursor, query)
        metrics[name] = {"rows": rows, "columns": columns}
    cursor.close()
    conn.close()
    return metrics


def fmt(n):
    if n is None:
        return "N/A"
    if isinstance(n, float):
        return f"{n:.2f}"
    return str(n)


def generate_report(metrics):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    total = metrics["total_alerts"]["rows"][0][0] if metrics["total_alerts"]["rows"] else 0
    last_24h = metrics["alerts_last_24h"]["rows"][0][0] if metrics["alerts_last_24h"]["rows"] else 0
    last_7d = metrics["alerts_last_7d"]["rows"][0][0] if metrics["alerts_last_7d"]["rows"] else 0

    mttr_data = metrics["mttr"]["rows"][0] if metrics["mttr"]["rows"] else (None, 0)
    mttr_seconds = mttr_data[0]
    mttr_responses = mttr_data[1]

    auto_data = metrics["automation_rate"]["rows"][0] if metrics["automation_rate"]["rows"] else (0, 0, 0)
    auto_pct = auto_data[2] if auto_data[2] else 0

    open_inc = metrics["open_incidents"]["rows"][0][0] if metrics["open_incidents"]["rows"] else 0
    total_inc = metrics["total_incidents"]["rows"][0][0] if metrics["total_incidents"]["rows"] else 0
    failed = metrics["failed_alerts"]["rows"][0][0] if metrics["failed_alerts"]["rows"] else 0

    sev = []
    for row in metrics["alerts_by_severity"]["rows"]:
        e = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(str(row[0]), "⚪")
        sev.append(f"  {e} {row[0]}: {row[1]}")

    ips = []
    for i, row in enumerate(metrics["top_ips"]["rows"], 1):
        ips.append(f"  {i}. {row[0]} ({row[1]} alertas)")

    rules = []
    for i, row in enumerate(metrics["top_rules"]["rows"], 1):
        rules.append(f"  {i}. {row[0]} ({row[1]})")

    crits = []
    for row in metrics["recent_critical"]["rows"]:
        ts = row[3].strftime("%m/%d %H:%M") if row[3] else "N/A"
        crits.append(f"  ⚠️ {row[0]} | {row[1]} | {ts}")

    nl = chr(10)
    return f"""📊 REPORTE SIEM — {now}
━━━━━━━━━━━━━━━━━━

📈 RESUMEN GENERAL
  Total alertas: {total}
  Últimas 24h: {last_24h}
  Últimos 7 días: {last_7d}

📊 POR SEVERIDAD
{nl.join(sev) if sev else '  Sin datos'}

⏱️ MÉTRICAS KPI
  MTTR: {fmt(mttr_seconds)}s ({mttr_responses} respuestas)
  Tasa automatización: {fmt(auto_pct)}%

🔒 INCIDENTES
  Abiertos: {open_inc}
  Total: {total_inc}
  Alertas fallidas: {failed}

🌐 TOP 5 IPs SOSPECHOSAS
{nl.join(ips) if ips else '  Sin datos'}

📜 TOP 5 REGLAS
{nl.join(rules) if rules else '  Sin datos'}

🔴 ALERTAS CRÍTICAS RECIENTES
{nl.join(crits) if crits else '  Sin alertas críticas'}

━━━━━━━━━━━━━━━━━━
🤖 Reporte automático del SIEM"""


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Variables TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID no configuradas")
        print("📋 Reporte (solo consola):")
        print(message)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("✅ Reporte enviado a Telegram")
            return True
        else:
            print(f"❌ Error Telegram: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("📊 Generando reporte SIEM...")
    print("━" * 40)

    metrics = collect_metrics()
    report = generate_report(metrics)

    # Mostrar en consola
    print(report)
    print("━" * 40)

    # Enviar por Telegram si hay credenciales
    send_telegram(report)

    # Imprimir JSON para que n8n lo capture si ejecuta el script
    output = {
        "status": "success",
        "report": report,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
