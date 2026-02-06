import json
import subprocess
import requests
import time
from datetime import datetime

N8N_WEBHOOK = "http://localhost:5678/webhook/alert/siem"
API_KEY = "superpoderosas26"

def monitor_wazuh_fim():
    """Monitorea alertas FIM de Wazuh y las envía a n8n"""
    
    print("🔍 Monitoreando alertas FIM de Wazuh en tiempo real...")
    print("-" * 60)
    
    # Comando para seguir el archivo de alertas
    cmd = [
        'docker', 'exec', 'siem_wazuh_manager',
        'tail', '-f', '-n', '0', '/var/ossec/logs/alerts/alerts.json'
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    for line in process.stdout:
        try:
            if not line.strip():
                continue
                
            alert = json.loads(line.strip())
            
            # Solo procesar alertas de syscheck (FIM)
            if 'syscheck' in alert.get('data', {}):
                fim = alert['data']['syscheck']
                
                # Determinar severidad según evento
                event_type = fim.get('event', 'unknown')
                if event_type == 'deleted':
                    severity = 'critical'
                elif event_type == 'modified':
                    severity = 'high'
                else:
                    severity = 'medium'
                
                # Crear payload para n8n
                payload = {
                    "rule_id": "file_integrity",
                    "src_ip": alert.get('agent', {}).get('ip', 'localhost'),
                    "username": fim.get('uname_after', 'unknown'),
                    "severity": severity,
                    "timestamp": alert.get('timestamp', datetime.utcnow().isoformat() + 'Z'),
                    "filepath": fim.get('path', ''),
                    "change_type": event_type,
                    "md5_after": fim.get('md5_after', ''),
                    "detection_method": "wazuh_fim"
                }
                
                # Enviar a n8n
                headers = {
                    "x-siem-key": API_KEY,
                    "Content-Type": "application/json"
                }
                
                response = requests.post(N8N_WEBHOOK, json=payload, headers=headers)
                
                if response.status_code == 200:
                    print(f"✅ FIM Alert: {fim.get('path')} - {event_type} [{severity}]")
                else:
                    print(f"❌ Error enviando alerta: {response.status_code}")
                    
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        monitor_wazuh_fim()
    except KeyboardInterrupt:
        print("\n⏹️  Monitor detenido")
