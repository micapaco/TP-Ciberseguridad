"""
Script para generar datos históricos de alertas SIEM
Genera alertas distribuidas en las últimas 2 semanas para gráficos de tendencia
"""
import requests
import random
from datetime import datetime, timedelta

# Configuración
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/alert/siem"
N8N_API_KEY = "superpoderosas26"

# Tipos de alertas
RULE_TYPES = [
    {"rule_id": "ssh_bruteforce", "severity": "high", "base_prob": 0.25},
    {"rule_id": "file_integrity", "severity": "medium", "base_prob": 0.20},
    {"rule_id": "failed_login", "severity": "low", "base_prob": 0.25},
    {"rule_id": "malware_detected", "severity": "critical", "base_prob": 0.10},
    {"rule_id": "suspicious_activity", "severity": "medium", "base_prob": 0.15},
    {"rule_id": "port_scan", "severity": "high", "base_prob": 0.05},
]

# IPs de ejemplo
SAMPLE_IPS = [
    "10.0.0.1", "10.0.0.2", "10.0.0.50", "192.168.1.100", "192.168.1.150",
    "172.16.0.10", "172.16.0.74", "192.168.100.10", "192.168.100.50", "10.10.10.5"
]

# Usuarios de ejemplo
SAMPLE_USERS = ["admin", "root", "guest", "user1", "operator", "backup", "www-data", "nobody"]

def generate_alert():
    """Genera una alerta aleatoria"""
    rule = random.choices(RULE_TYPES, weights=[r["base_prob"] for r in RULE_TYPES])[0]
    
    return {
        "rule_id": rule["rule_id"],
        "src_ip": random.choice(SAMPLE_IPS),
        "username": random.choice(SAMPLE_USERS),
        "severity": rule["severity"],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

def send_alert(alert):
    """Envía alerta al webhook de n8n"""
    headers = {
        "x-siem-key": N8N_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=alert, headers=headers, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Genera múltiples alertas para datos históricos"""
    num_alerts = 50  # Generar 50 alertas adicionales
    
    print(f"🔄 Generando {num_alerts} alertas históricas...")
    print("-" * 50)
    
    success = 0
    for i in range(num_alerts):
        alert = generate_alert()
        if send_alert(alert):
            success += 1
            print(f"✅ [{i+1}/{num_alerts}] {alert['rule_id']} - {alert['severity']} - {alert['src_ip']}")
        else:
            print(f"❌ [{i+1}/{num_alerts}] Error enviando alerta")
    
    print("-" * 50)
    print(f"✅ Completado: {success}/{num_alerts} alertas enviadas")

if __name__ == "__main__":
    main()
