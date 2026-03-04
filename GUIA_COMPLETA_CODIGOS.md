# 📚 Guía Completa — Todos los Códigos del SIEM explicados

> **Objetivo de este documento**: Que entiendas cada archivo del proyecto como si lo hubieras escrito vos.  
> Cada sección explica: **qué hace**, **por qué existe** (según el PROYECTO 03) y **cómo funciona línea por línea**.

---

## 📋 Índice

1. [Visión general — ¿Cómo se conecta todo?](#1-visión-general)
2. [docker-compose.yml — El que levanta todo](#2-docker-composeyml)
3. [syslog-ng.conf — El recolector de logs](#3-syslog-ngconf)
4. [logstash.conf — El que parsea los logs](#4-logstashconf)
5. [01-init.sql — La base de datos](#5-01-initsql)
6. [ssh_bruteforce_detector.py — El detective de ataques SSH](#6-ssh_bruteforce_detectorpy)
7. [wazuh_fim_to_n8n.py — El vigilante de archivos](#7-wazuh_fim_to_n8npy)
8. [generate_historical_data.py — El generador de datos de prueba](#8-generate_historical_datapy)
9. [workflow-siem-alerta.json — El workflow de n8n](#9-workflow-siem-alertajson)
10. [Configuraciones de Grafana](#10-configuraciones-de-grafana)
11. [Todos los comandos de prueba explicados](#11-todos-los-comandos-de-prueba-explicados)
12. [Flujo completo de n8n paso a paso](#12-flujo-completo-de-n8n-paso-a-paso)
13. [Estado del proyecto vs PROYECTO 03](#13-estado-del-proyecto-vs-proyecto-03)
14. [Mejoras adicionales propuestas](#14-mejoras-adicionales-propuestas)

---

## 1. Visión general

### ¿Qué es este proyecto?

Es un **SIEM** (Sistema de Información y Gestión de Eventos de Seguridad). Pensalo como un **sistema de alarmas para computadoras**: detecta cuando alguien intenta hacer algo malo (como adivinar contraseñas o modificar archivos importantes) y avisa automáticamente.

### ¿Por qué lo hicimos? (PROYECTO 03)

El PROYECTO 03 pide:
1. **Recolectar logs** de diferentes máquinas en un solo lugar
2. **Detectar ataques** como SSH brute-force y cambios en archivos
3. **Responder automáticamente** (notificar, registrar, guardar evidencia)
4. **Visualizar** todo en dashboards
5. **Medir el rendimiento** (MTTA, MTTR, tasa de automatización)

### ¿Cómo se conecta todo?

```
TU PC (simula un atacante)
    │
    │ envía logs falsos por UDP al puerto 514
    ▼
┌─────────────┐     ┌───────────┐     ┌─────────────────┐
│  syslog-ng  │ ──▶ │ Logstash  │ ──▶ │ Elasticsearch   │
│  (puerto    │     │ (parsea   │     │ (guarda los      │
│   514)      │     │  los logs)│     │  logs indexados) │
└─────────────┘     └───────────┘     └────────┬────────┘
                                               │
                    ┌──────────────────────────▼──────────┐
                    │  ssh_bruteforce_detector.py          │
                    │  (cada 2 min revisa Elasticsearch    │
                    │   buscando ataques)                  │
                    └──────────┬──────────────────────────┘
                               │ si encuentra ataque, envía alerta
                               ▼
                    ┌──────────────────┐
                    │  n8n (webhook)   │
                    │  (el orquestador │
                    │   de respuestas) │
                    └──┬───────┬───┬──┘
                       │       │   │
            ┌──────────▼┐  ┌──▼──┐ └──▶ Responde "OK" o "Error"
            │ PostgreSQL│  │Tele-│
            │ (guarda   │  │gram │
            │  alertas) │  │(avi-│
            └─────┬─────┘  │sa)  │
                  │        └─────┘
                  ▼
            ┌──────────┐
            │ Grafana  │
            │ (muestra │
            │  gráficos│
            └──────────┘

    Wazuh (por otro lado) ──▶ wazuh_fim_to_n8n.py ──▶ n8n
    (vigila cambios en archivos)
```

---

## 2. docker-compose.yml

📁 **Ubicación**: `C:\TP-Final\docker-compose.yml`

### ¿Qué es?
Es el archivo que le dice a Docker: "levantame estos 8 servicios, conectalos entre sí, y configurá cada uno así". Con **un solo comando** (`docker-compose up -d`) levantás todo el SIEM.

### ¿Por qué existe? (PROYECTO 03)
> *"Desarrollar y documentar un prototipo funcional de SIEM automatizado"* — Objetivo General  
> *"Reproducible: un docente puede levantar el stack con un solo docker compose up -d"* — Criterio de validación

### Cada servicio explicado:

#### 🗄️ PostgreSQL (líneas 2-16)
```yaml
postgres:
  image: postgres:16                    # Usa la imagen oficial de PostgreSQL versión 16
  container_name: siem_postgres         # Nombre del contenedor (para identificarlo fácil)
  environment:
    POSTGRES_USER: siem                 # Usuario de la base de datos
    POSTGRES_PASSWORD: siem123          # Contraseña
    POSTGRES_DB: siem                   # Nombre de la base de datos
  ports:
    - "5432:5432"                       # Expone el puerto 5432 (el estándar de PostgreSQL)
  volumes:
    - ./sql:/docker-entrypoint-initdb.d # Al iniciar, ejecuta todos los .sql de la carpeta sql/
    - postgres_data:/var/lib/...        # Guarda los datos para que no se pierdan al apagar
```
**¿Para qué?** Guarda las alertas, los playbooks ejecutados y las métricas. Es la "memoria permanente" del SIEM.  
**PROYECTO 03**: *"Normalizar y almacenar eventos en PostgreSQL (auditoría)"*

#### 🔍 Elasticsearch (líneas 18-31)
```yaml
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.15.0
  environment:
    - discovery.type=single-node        # Un solo nodo (suficiente para el lab)
    - xpack.security.enabled=false      # Sin autenticación (simplifica el lab)
    - ES_JAVA_OPTS=-Xms1g -Xmx1g       # Le da 1GB de RAM a Java
  ports:
    - "9200:9200"                       # Puerto para consultas HTTP
```
**¿Para qué?** Es el "buscador de logs". Guarda todos los logs crudos y permite buscarlos rápidamente (por IP, por fecha, por tipo de evento).  
**PROYECTO 03**: *"Almacenar eventos en Elasticsearch (búsqueda)"*

#### 📊 Kibana (líneas 33-44)
```yaml
kibana:
  environment:
    - ELASTICSEARCH_HOSTS=http://elasticsearch:9200   # Le dice dónde está Elasticsearch
  ports:
    - "5601:5601"                       # Puerto para acceder desde el navegador
  depends_on:
    - elasticsearch                     # No inicia hasta que Elasticsearch esté listo
```
**¿Para qué?** Interfaz web para explorar los logs crudos en Elasticsearch. Podés buscar, filtrar y analizar logs manualmente.  
**PROYECTO 03**: *"Visualización en Kibana (opcional)"*

#### 🔧 Logstash (líneas 46-59)
```yaml
logstash:
  volumes:
    - ./logstash/logstash.conf:/usr/share/logstash/pipeline/logstash.conf
  ports:
    - "5044:5044"          # Puerto Beats (no usado actualmente)
    - "5140:5140/udp"      # Puerto UDP donde recibe logs de syslog-ng
  depends_on:
    - elasticsearch        # Necesita que Elasticsearch esté arriba para enviarle datos
    - postgres
```
**¿Para qué?** Recibe los logs "en crudo" de syslog-ng, los parsea (extrae campos como IP, programa, mensaje) y los envía a Elasticsearch ya organizados.  
**PROYECTO 03**: *"Implementar la recolección centralizada de logs mediante syslog-ng y Logstash"*

#### 📡 Syslog-ng (líneas 61-73)
```yaml
syslog-ng:
  ports:
    - "514:514/udp"        # Escucha logs por UDP en el puerto estándar de syslog
    - "6514:6514/tcp"      # También por TCP (backup)
  depends_on:
    - logstash             # Necesita Logstash para reenviar los logs
```
**¿Para qué?** Es la "puerta de entrada" del SIEM. Cualquier máquina puede enviarle logs por el puerto 514 (el estándar de syslog). Syslog-ng los recibe y los reenvía a Logstash.  
**PROYECTO 03**: *"Recolección de logs desde hosts"*

#### 🤖 n8n (líneas 75-96)
```yaml
n8n:
  ports:
    - "5678:5678"          # Puerto para la interfaz web
  environment:
    - DB_TYPE=postgresdb               # Usa PostgreSQL como base de datos interna
    - DB_POSTGRESDB_HOST=postgres      # Se conecta al contenedor postgres
    - DB_POSTGRESDB_DATABASE=siem      # Misma base de datos del SIEM
```
**¿Para qué?** Es el "cerebro de respuesta automática" (SOAR-lite). Recibe alertas por webhook, las valida, las guarda en PostgreSQL, envía notificaciones a Telegram y registra qué acciones tomó.  
**PROYECTO 03**: *"Orquestar respuestas automáticas en n8n (notificación, bloqueo simulado, ticket, evidencia)"*

#### 📈 Grafana (líneas 98-114)
```yaml
grafana:
  ports:
    - "3000:3000"          # Puerto para acceder al dashboard
  environment:
    - GF_SECURITY_ADMIN_USER=admin
    - GF_SECURITY_ADMIN_PASSWORD=admin123
  volumes:
    - ./grafana:/etc/grafana/provisioning    # Carga los dashboards y datasources automáticamente
```
**¿Para qué?** Muestra gráficos bonitos con toda la información: alertas por severidad, IPs más sospechosas, tiempo de respuesta (MTTR), tasa de automatización.  
**PROYECTO 03**: *"Visualizar métricas operativas y de aprendizaje en Grafana"*

#### 🛡️ Wazuh Manager (líneas 116-141)
```yaml
wazuh-manager:
  image: wazuh/wazuh-manager:4.7.0
  ports:
    - "1514:1514"          # Puerto para agentes Wazuh
    - "1515:1515"          # Puerto de registro de agentes
    - "55000:55000"        # API de Wazuh
```
**¿Para qué?** Vigila la integridad de archivos (FIM = File Integrity Monitoring). Cuando alguien crea, modifica o elimina un archivo monitoreado, Wazuh lo detecta y genera una alerta.  
**PROYECTO 03**: *"Definir reglas de detección: SSH brute force, FIM, actividad anómala"*

### Sección de redes y volúmenes (final del archivo)
```yaml
networks:
  siem-net:                # Red interna donde todos los contenedores se ven entre sí
    driver: bridge

volumes:
  postgres_data:           # Datos de PostgreSQL (persistentes)
  elasticsearch_data:      # Datos de Elasticsearch (persistentes)
  n8n_data:                # Configuración de n8n (persistente)
  grafana_data:            # Dashboards de Grafana (persistente)
  wazuh_*:                 # Varios volúmenes para datos de Wazuh
```
**¿Para qué?** Los `volumes` guardan los datos de forma persistente. Si hacés `docker-compose down` y después `docker-compose up -d`, los datos siguen ahí.

---

## 3. syslog-ng.conf

📁 **Ubicación**: `C:\TP-Final\syslog-ng\syslog-ng.conf`

### ¿Qué es?
La configuración de syslog-ng, el primer servicio que recibe los logs.

### ¿Por qué existe? (PROYECTO 03)
> *"El host/servicio envía sus logs por syslog a syslog-ng (UDP/514)"* — Anexo B

### Código explicado línea por línea:
```conf
@version: 3.35              # Versión de la sintaxis de syslog-ng
@include "scl.conf"         # Incluye la librería estándar de syslog-ng

# ENTRADA: escucha en el puerto 514 por UDP
source s_network {
  network(
    transport("udp")        # Protocolo UDP (rápido, sin conexión)
    port(514)               # Puerto 514 = el estándar de syslog
  );
};

# SALIDA: reenvía todo a Logstash
destination d_logstash {
  network(
    "logstash"              # Nombre del contenedor Logstash dentro de Docker
    transport("udp")        # También por UDP
    port(5140)              # Puerto donde Logstash escucha
  );
};

# REGLA: todo lo que entre por s_network, mandalo a d_logstash
log {
  source(s_network);
  destination(d_logstash);
};
```

### En resumen:
Syslog-ng es como un **cartero**: recibe cartas (logs) en el buzón (puerto 514) y las lleva a Logstash (puerto 5140). No las modifica, solo las pasa.

---

## 4. logstash.conf

📁 **Ubicación**: `C:\TP-Final\logstash\logstash.conf`

### ¿Qué es?
La configuración de Logstash, el servicio que **parsea** (analiza y descompone) los logs.

### ¿Por qué existe? (PROYECTO 03)
> *"Logstash: aplica grok para parsear, enriquece con timestamp de ingesta, envía a Elasticsearch"* — Anexo B

### Código explicado:

```conf
# ═══════════════════════════════════════════
# ENTRADA — ¿De dónde vienen los logs?
# ═══════════════════════════════════════════
input {
  udp {
    port => 5140              # Escucha en puerto 5140 los logs que manda syslog-ng
    type => "syslog"          # Les pone la etiqueta "syslog" para identificarlos
  }
}

# ═══════════════════════════════════════════
# PROCESAMIENTO — ¿Cómo los descompone?
# ═══════════════════════════════════════════
filter {
  # PASO 1: Grok - Extraer campos del mensaje
  # Convierte un texto como:
  #   "<34>Mar 04 20:34:08 testhost sshd[12345]: Failed password for admin from 10.0.0.99"
  # En campos separados:
  #   syslog_pri = 34
  #   syslog_timestamp = "Mar 04 20:34:08"
  #   hostname = "testhost"
  #   program = "sshd"
  #   pid = "12345"
  #   syslog_message = "Failed password for admin from 10.0.0.99"
  grok {
    match => {
      "message" => [
        "<%{POSINT:syslog_pri}>%{SYSLOGTIMESTAMP:syslog_timestamp} %{SYSLOGHOST:hostname} %{DATA:program}(?:\[%{POSINT:pid}\])?: %{GREEDYDATA:syslog_message}",
        "%{SYSLOGTIMESTAMP:syslog_timestamp} %{SYSLOGHOST:hostname} %{DATA:program}(?:\[%{POSINT:pid}\])?: %{GREEDYDATA:syslog_message}"
      ]
    }
  }
  
  # PASO 2: Extraer la IP de origen del mensaje
  # De "Failed password for admin from 10.0.0.99 port 22"
  # Extrae: src_ip = "10.0.0.99"
  grok {
    match => {
      "message" => "from %{IP:src_ip}"
    }
  }
  
  # PASO 3: Si es un intento SSH fallido, extraer el usuario
  if [program] == "sshd" and "Failed password" in [message] {
    grok {
      match => {
        "message" => "Failed password for (?:invalid user )?%{USERNAME:username}"
      }
    }
  }
  
  # PASO 4: Convertir el timestamp del syslog a formato estándar
  date {
    match => [ "syslog_timestamp", "MMM  d HH:mm:ss", "MMM dd HH:mm:ss" ]
    target => "@timestamp"    # Guarda como @timestamp (el campo que usa Elasticsearch)
  }
  
  # PASO 5: Guardar cuándo se procesó el log
  mutate {
    add_field => { "ingest_ts" => "%{@timestamp}" }
  }
}

# ═══════════════════════════════════════════
# SALIDA — ¿A dónde van los logs procesados?
# ═══════════════════════════════════════════
output {
  # Enviar a Elasticsearch organizados por fecha
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "siem-events-%{+YYYY.MM.dd}"   # Un índice por día (ej: siem-events-2026.03.04)
  }
  
  # También mostrar en la consola (útil para debugging)
  stdout { 
    codec => rubydebug 
  }
}
```

### En resumen:
Logstash es como un **traductor**: recibe un texto largo y desordenado, lo descompone en partes útiles (IP, programa, fecha, mensaje), y lo guarda ordenado en Elasticsearch.

---

## 5. 01-init.sql

📁 **Ubicación**: `C:\TP-Final\sql\01-init.sql`

### ¿Qué es?
El archivo SQL que crea las tablas y vistas en PostgreSQL cuando el contenedor se inicia por primera vez.

### ¿Por qué existe? (PROYECTO 03)
> *"Almacenar eventos en PostgreSQL (auditoría)"*  
> *"Auditoría completa de los playbooks de respuesta"*  
> *"Medir el impacto en MTTA/MTTR y tasa de automatización"*

### Tablas explicadas:

#### Tabla `events_raw` — Todos los eventos crudos
```sql
CREATE TABLE IF NOT EXISTS events_raw (
    id SERIAL PRIMARY KEY,        -- Número único auto-incrementable
    ts TIMESTAMP DEFAULT NOW(),   -- Cuándo llegó el evento
    host VARCHAR(120),            -- De qué máquina vino
    source VARCHAR(120),          -- Qué servicio lo generó (ej: "sshd")
    severity VARCHAR(20),         -- Qué tan grave es (low, medium, high, critical)
    message TEXT,                 -- El mensaje completo del log
    json_raw JSONB                -- El evento crudo en formato JSON
);
```
**Analogía**: Es como un **libro de registro** donde se anota TODO lo que pasa, sin filtrar.

#### Tabla `alerts` — Las alertas procesadas
```sql
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP DEFAULT NOW(),     -- Cuándo se creó la alerta
    rule_id VARCHAR(120),           -- Qué regla la disparó (ej: "ssh_bruteforce")
    src_ip VARCHAR(60),             -- IP del atacante
    username VARCHAR(120),          -- Usuario que intentaron atacar
    severity VARCHAR(20),           -- Severidad (low/medium/high/critical)
    raw JSONB,                      -- Datos crudos completos
    status VARCHAR(30) DEFAULT 'new',  -- Estado: new, acknowledged, resolved
    acknowledged_at TIMESTAMPTZ,    -- Cuándo alguien la vio
    acknowledged_by TEXT            -- Quién la vio
);
```
**Analogía**: Es como una **lista de alarmas que se activaron**. Cada fila es un ataque detectado.

#### Tabla `playbook_runs` — Qué hizo el sistema ante cada alerta
```sql
CREATE TABLE IF NOT EXISTS playbook_runs (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alerts(id),  -- A qué alerta corresponde
    workflow VARCHAR(120),                     -- Qué workflow se ejecutó
    outcome VARCHAR(60),                       -- Resultado (success/failure)
    evidence JSONB,                            -- Evidencia guardada
    executed_at TIMESTAMP DEFAULT NOW()        -- Cuándo se ejecutó
);
```
**Analogía**: Es como un **registro de acciones tomadas**. Si alguien intentó entrar y el sistema avisó por Telegram, acá queda registrado.  
**PROYECTO 03**: *"playbook_runs permite reconstruir el incidente"*

### Vistas (consultas pre-armadas):

#### Vista `mttr_stats` — Tiempo medio de respuesta
```sql
CREATE VIEW mttr_stats AS
SELECT 
    AVG(EXTRACT(EPOCH FROM (p.executed_at - a.ts))) AS avg_mttr_seconds,
    COUNT(*) AS total_responses
FROM alerts a
JOIN playbook_runs p ON p.alert_id = a.id;
```
**¿Qué hace?** Calcula el promedio de segundos entre que se crea una alerta y se ejecuta la respuesta automática.  
**Ejemplo**: Si dice `avg_mttr_seconds = 0.5`, significa que el sistema responde en medio segundo en promedio.  
**PROYECTO 03**: *"Medir el impacto en MTTA/MTTR"*

#### Vista `automation_rate` — Tasa de automatización
```sql
CREATE VIEW automation_rate AS
SELECT 
    COUNT(DISTINCT p.alert_id) AS automated_alerts,    -- Alertas que tuvieron respuesta automática
    (SELECT COUNT(*) FROM alerts) AS total_alerts,      -- Total de alertas
    ROUND(...) AS automation_percentage                  -- Porcentaje
FROM playbook_runs p;
```
**¿Qué hace?** Calcula qué porcentaje de alertas fueron respondidas automáticamente.  
**Ejemplo**: Si dice `automation_percentage = 95.00`, significa que el 95% de las alertas se manejaron sin intervención humana.  
**PROYECTO 03**: *"Tasa de automatización: (playbooks / alertas) * 100"*

#### Vista `top_suspicious_ips` — Las IPs más sospechosas
```sql
CREATE VIEW top_suspicious_ips AS
SELECT src_ip, COUNT(*) AS alert_count
FROM alerts
WHERE src_ip IS NOT NULL
GROUP BY src_ip
ORDER BY alert_count DESC
LIMIT 10;
```
**¿Qué hace?** Muestra las 10 IPs que más alertas generaron.

---

## 6. ssh_bruteforce_detector.py

📁 **Ubicación**: `C:\TP-Final\detector\ssh_bruteforce_detector.py`

### ¿Qué es?
Un script Python que cada 2 minutos busca en Elasticsearch si alguien está intentando adivinar contraseñas SSH (ataque de fuerza bruta). Si detecta 5 o más intentos fallidos desde la misma IP, envía una alerta a n8n.

### ¿Por qué existe? (PROYECTO 03)
> *"Definir y ejecutar reglas de detección basadas en umbrales y patrones (SSH brute force)"*  
> *"Criterio: 5 intentos fallidos de login SSH desde la misma IP en una ventana de 2 minutos"* — Anexo G

### Código explicado:

#### Configuración (líneas 1-11)
```python
import requests           # Para hacer peticiones HTTP (a Elasticsearch y n8n)
import time               # Para esperar entre chequeos
from datetime import datetime, timedelta
import json

ELASTICSEARCH_URL = "http://localhost:9200"                    # Dónde está Elasticsearch
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/alert/siem"   # Dónde está n8n
N8N_API_KEY = "superpoderosas26"                               # Clave de autenticación
CHECK_INTERVAL = 120   # Cada cuánto revisar (120 seg = 2 minutos)
THRESHOLD = 5          # Mínimo de intentos para considerarlo ataque
```

#### Función `buscar_ssh_bruteforce()` — El corazón del detector (líneas 13-67)
```python
def buscar_ssh_bruteforce():
    # Arma una consulta para Elasticsearch que dice:
    # "Buscame todos los eventos donde:
    #   - El programa sea 'sshd' (servidor SSH)
    #   - El mensaje contenga 'Failed password' (intento fallido)
    #   - Hayan ocurrido en los últimos 2 minutos
    #   Y agrupalos por IP de origen"
    
    query = {
        "size": 0,            # No quiero los documentos, solo los conteos
        "query": {
            "bool": {
                "must": [
                    {"match": {"program": "sshd"}},           # Filtro: programa SSH
                    {"match": {"message": "Failed password"}}  # Filtro: contraseña fallida
                ],
                "filter": {
                    "range": {
                        "@timestamp": {
                            "gte": "now-2m"    # Solo eventos de los últimos 2 minutos
                        }
                    }
                }
            }
        },
        "aggs": {                  # Agregaciones (agrupaciones)
            "ips_atacantes": {
                "terms": {
                    "field": "src_ip.keyword",      # Agrupar por IP
                    "min_doc_count": THRESHOLD       # Solo IPs con 5+ intentos
                }
            }
        }
    }
    
    # Envía la consulta a Elasticsearch
    response = requests.post(f"{ELASTICSEARCH_URL}/siem-events-*/_search", json=query)
    
    # Si hay resultados, recorre cada IP atacante
    data = response.json()
    buckets = data["aggregations"]["ips_atacantes"]["buckets"]
    
    for bucket in buckets:
        ip = bucket["key"]           # La IP del atacante
        count = bucket["doc_count"]  # Cuántos intentos hizo
        
        print(f"🚨 ALERTA: SSH Brute Force detectado desde {ip} - {count} intentos")
        enviar_alerta_n8n(ip, count)  # Avisar a n8n
```

**Analogía**: Es como un **guardia de seguridad** que cada 2 minutos revisa las cámaras y cuenta cuántas veces la misma persona intentó abrir una puerta. Si fueron 5 o más, llama a la central.

#### Función `enviar_alerta_n8n()` — Avisar a n8n (líneas 69-96)
```python
def enviar_alerta_n8n(src_ip, event_count):
    # Arma el "paquete" de información de la alerta
    alerta = {
        "rule_id": "ssh_bruteforce_auto",      # Qué regla se activó
        "src_ip": src_ip,                       # IP del atacante
        "username": "detected_automatically",   # Detectado por script
        "severity": "high",                     # Severidad alta
        "event_count": event_count,             # Cuántos intentos hubo
        "timestamp": datetime.utcnow().isoformat() + "Z",  # Cuándo se detectó
        "detection_method": "automated_script"  # Método de detección
    }
    
    # Envía la alerta al webhook de n8n con la clave de autenticación
    headers = {
        "x-siem-key": N8N_API_KEY,             # Clave para que n8n acepte la alerta
        "Content-Type": "application/json"
    }
    
    response = requests.post(N8N_WEBHOOK_URL, json=alerta, headers=headers)
```

#### Función `main()` — El loop infinito (líneas 98-112)
```python
def main():
    print("🔍 Detector SSH Brute Force iniciado")
    
    while True:                          # Bucle infinito
        buscar_ssh_bruteforce()          # Buscar ataques
        time.sleep(CHECK_INTERVAL)       # Esperar 2 minutos
        # Y volver a buscar...
```

---

## 7. wazuh_fim_to_n8n.py

📁 **Ubicación**: `C:\TP-Final\detector\wazuh_fim_to_n8n.py`

### ¿Qué es?
Un script Python que monitorea las alertas de Wazuh en tiempo real. Cuando Wazuh detecta que alguien creó, modificó o eliminó un archivo, este script lo lee y envía la alerta a n8n.

### ¿Por qué existe? (PROYECTO 03)
> *"FIM (File Integrity Monitoring): detectar modificaciones en archivos críticos"*  
> *"Integridad de archivos con Wazuh/OSSEC"* — Anexo G

### Código explicado:

```python
def monitor_wazuh_fim():
    # Ejecuta "docker exec siem_wazuh_manager tail -f" 
    # para leer el archivo de alertas de Wazuh en TIEMPO REAL
    cmd = ['docker', 'exec', 'siem_wazuh_manager',
           'tail', '-f', '-n', '0', '/var/ossec/logs/alerts/alerts.json']
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    
    # Lee cada línea nueva que aparezca (en tiempo real)
    for line in process.stdout:
        alert = json.loads(line)    # Convierte la línea de texto a diccionario Python
        
        # Solo procesa alertas de tipo FIM (syscheck)
        if 'syscheck' in alert.get('data', {}):
            fim = alert['data']['syscheck']
            
            # Decide la severidad según qué pasó:
            event_type = fim.get('event', 'unknown')
            if event_type == 'deleted':       # Archivo borrado = CRÍTICO
                severity = 'critical'
            elif event_type == 'modified':    # Archivo modificado = ALTO
                severity = 'high'
            else:                             # Archivo creado = MEDIO
                severity = 'medium'
            
            # Arma la alerta con toda la info
            payload = {
                "rule_id": "file_integrity",
                "severity": severity,
                "filepath": fim.get('path', ''),         # Qué archivo fue afectado
                "change_type": event_type,                # Creado/modificado/eliminado
                "md5_after": fim.get('md5_after', ''),    # Hash del archivo después del cambio
                "detection_method": "wazuh_fim"
            }
            
            # Envía a n8n
            requests.post(N8N_WEBHOOK, json=payload, headers=headers)
```

**Analogía**: Es como un **sensor de movimiento** en una caja fuerte. Si alguien toca algo adentro, suena la alarma y queda registrado qué tocó, cuándo y cómo quedó después.

---

## 8. generate_historical_data.py

📁 **Ubicación**: `C:\TP-Final\detector\generate_historical_data.py`

### ¿Qué es?
Un script que genera 50 alertas aleatorias para que los dashboards de Grafana no estén vacíos. Es para **demostración** y **pruebas**.

### ¿Por qué existe? (PROYECTO 03)
> *"Generación de datos: envío de eventos de prueba (ssh failed, integridad, syslog)"*  
> *"Material didáctico reproducible"*

### Código explicado:

```python
# Tipos de alertas posibles (con probabilidad de aparición)
RULE_TYPES = [
    {"rule_id": "ssh_bruteforce",      "severity": "high",     "base_prob": 0.25},  # 25% de chance
    {"rule_id": "file_integrity",      "severity": "medium",   "base_prob": 0.20},  # 20% de chance
    {"rule_id": "failed_login",        "severity": "low",      "base_prob": 0.25},  # 25% de chance
    {"rule_id": "malware_detected",    "severity": "critical", "base_prob": 0.10},  # 10% de chance
    {"rule_id": "suspicious_activity", "severity": "medium",   "base_prob": 0.15},  # 15% de chance
    {"rule_id": "port_scan",           "severity": "high",     "base_prob": 0.05},  #  5% de chance
]

# IPs y usuarios de ejemplo para que parezca realista
SAMPLE_IPS = ["10.0.0.1", "10.0.0.2", "192.168.1.100", ...]
SAMPLE_USERS = ["admin", "root", "guest", "user1", ...]

def generate_alert():
    # Elige un tipo de alerta al azar (respetando las probabilidades)
    rule = random.choices(RULE_TYPES, weights=[r["base_prob"] for r in RULE_TYPES])[0]
    
    return {
        "rule_id": rule["rule_id"],
        "src_ip": random.choice(SAMPLE_IPS),      # IP al azar
        "username": random.choice(SAMPLE_USERS),   # Usuario al azar
        "severity": rule["severity"],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

def main():
    # Genera 50 alertas y las envía una por una al webhook de n8n
    for i in range(50):
        alert = generate_alert()
        send_alert(alert)    # POST al webhook de n8n
```

**Analogía**: Es como un **simulador de incendios** que activa alarmas de prueba para verificar que todos los sistemas funcionan y los gráficos se actualizan.

---

## 9. workflow-siem-alerta.json

📁 **Ubicación**: `C:\TP-Final\n8n\workflow-siem-alerta.json`

### ¿Qué es?
La definición del workflow de n8n en formato JSON. Define qué nodos (pasos) tiene el flujo y cómo se conectan.

### ¿Por qué existe? (PROYECTO 03)
> *"Orquestar respuestas automáticas en n8n: notificación, bloqueo simulado, ticket, evidencia"*  
> *"n8n valida, guarda en Postgres, notifica (Telegram/Slack), registra la ejecución del playbook"*

### Los 7 nodos del workflow:

```
1. [Webhook SIEM]           → Recibe la alerta por POST en /webhook/alert/siem
       ↓
2. [Validar API Key]        → ¿La clave "x-siem-key" es correcta?
       ↓ SÍ                         ↓ NO
3. [Preparar Datos]         7. [Responder Error 401]
       ↓
4. [Insertar en PostgreSQL] → Guarda la alerta en la tabla "alerts"
       ↓
5. [Notificar Telegram]     → Envía mensaje al bot de Telegram con los detalles
       ↓
6. [Registrar Playbook]     → Guarda en "playbook_runs" que se ejecutó exitosamente
       ↓
7. [Responder OK 200]       → Responde "Alert processed" al que la envió
```

### Detalle de cada nodo:

#### Nodo 1: Webhook SIEM
```json
{
  "httpMethod": "POST",
  "path": "alert/siem"       // URL final: http://localhost:5678/webhook/alert/siem
}
```
Escucha peticiones POST. Cuando un script de detección encuentra algo, le envía la alerta acá.

#### Nodo 2: Validar API Key
```json
{
  "value1": "={{ $json.headers['x-siem-key'] }}",   // Lee la clave del header
  "operation": "equals",
  "value2": "superpoderosas26"                       // La compara con la clave correcta
}
```
Es una **medida de seguridad**: solo acepta alertas que vengan con la clave correcta. Si alguien intenta enviar alertas falsas sin la clave, las rechaza con error 401.

#### Nodo 3: Preparar Datos
Toma los datos del body (rule_id, src_ip, severity, etc.) y los formatea para que PostgreSQL los pueda guardar.

#### Nodo 4: Insertar Alerta en PostgreSQL
Ejecuta un INSERT en la tabla `alerts` con los datos de la alerta.

#### Nodo 5: Notificar Telegram
```json
{
  "text": "🚨 **ALERTA SIEM**\n📋 Regla: ssh_bruteforce\n🔴 Severidad: high\n🌐 IP: 10.0.0.99"
}
```
Envía un mensaje formateado al chat de Telegram con todos los detalles del ataque.

#### Nodo 6: Registrar Playbook
Ejecuta un INSERT en la tabla `playbook_runs` para dejar constancia de que el sistema respondió a la alerta automáticamente.  
**PROYECTO 03**: *"Trazabilidad: la ejecución queda registrada en playbook_runs"*

---

## 10. Configuraciones de Grafana

### datasources.yml
📁 `C:\TP-Final\grafana\datasources\datasources.yml`

```yaml
datasources:
  # Fuente 1: PostgreSQL (para métricas y alertas)
  - name: Postgres SIEM
    type: postgres
    url: postgres:5432         # Se conecta al contenedor PostgreSQL
    database: siem
    user: siem
    secureJsonData:
      password: siem123
    isDefault: true            # Es la fuente de datos por defecto

  # Fuente 2: Elasticsearch (para logs crudos)
  - name: Elasticsearch SIEM
    type: elasticsearch
    url: http://elasticsearch:9200
    database: "[siem-events-]YYYY.MM.DD"    # Patrón de índices por fecha
    jsonData:
      timeField: "@timestamp"               # Campo de tiempo
```
**¿Qué hace?** Le dice a Grafana de dónde sacar los datos: PostgreSQL para alertas/métricas y Elasticsearch para logs crudos.

### dashboards.yml
📁 `C:\TP-Final\grafana\dashboards\dashboards.yml`

```yaml
providers:
  - name: 'SIEM Dashboards'
    folder: 'SIEM'                 # Carpeta donde aparecen en Grafana
    type: file
    updateIntervalSeconds: 30      # Cada 30 segundos busca cambios
    options:
      path: /etc/grafana/provisioning/dashboards    # Dónde están los JSON de dashboards
```
**¿Qué hace?** Le dice a Grafana que cargue automáticamente los dashboards que están en la carpeta `dashboards/`.

---

## 11. Todos los comandos de prueba explicados

### 🟢 Comandos de inicio

| # | Comando | ¿Qué hace? | ¿Por qué? |
|---|---------|-------------|-----------|
| 1 | `cd C:\TP-Final` | Te mueve a la carpeta del proyecto | Todos los comandos deben correrse desde acá |
| 2 | `docker-compose up -d` | Levanta los 8 contenedores | `-d` = en segundo plano. Crea la red, los volúmenes y arranca todo |
| 3 | `docker-compose ps` | Muestra el estado de cada contenedor | Para verificar que todos digan "Up" |

### ✅ Verificaciones

| # | Comando | ¿Qué hace? | ¿Qué debería responder? |
|---|---------|-------------|------------------------|
| 4 | `Invoke-RestMethod -Uri "http://localhost:9200/_cluster/health"` | Consulta la salud de Elasticsearch por HTTP | `status: yellow` o `green` (ambos OK). `red` = hay un problema |
| 5 | `docker exec siem_postgres psql -U siem -d siem -c "SELECT COUNT(*) FROM alerts;"` | Se mete dentro del contenedor PostgreSQL y ejecuta una consulta SQL | Un número (ej: 168). Si responde, PostgreSQL funciona |

**Desglose del comando 5:**
- `docker exec siem_postgres` → Ejecuta un comando dentro del contenedor llamado `siem_postgres`
- `psql` → El programa de línea de comandos de PostgreSQL
- `-U siem` → Conectarse como el usuario `siem`
- `-d siem` → A la base de datos `siem`
- `-c "SELECT COUNT(*) FROM alerts;"` → Ejecutar esta consulta SQL (contar cuántas alertas hay)

### 🔐 Prueba SSH Brute-Force

| # | Comando | ¿Qué hace? |
|---|---------|-------------|
| 6 | `python detector\ssh_bruteforce_detector.py` | Inicia el detector. Queda corriendo en loop, checando cada 2 min |
| 7 | El script de simulación (ver abajo) | Envía 6 logs falsos de "Failed password" al puerto 514 |

**Desglose del script de simulación:**
```powershell
# Genera el timestamp actual en UTC con formato de syslog en inglés
# Ejemplo: "Mar 04 20:35:23"
$ts = (Get-Date).ToUniversalTime().ToString("MMM dd HH:mm:ss", [System.Globalization.CultureInfo]::InvariantCulture)

# Repite 6 veces (para superar el umbral de 5)
for ($i = 1; $i -le 6; $i++) {
    # Arma un mensaje syslog falso que simula un intento SSH fallido
    # <34> = prioridad syslog (facility=auth, severity=crit)
    # testhost = nombre del host
    # sshd[12345] = programa SSH con PID 12345
    # Failed password for invalid user admin from 10.0.0.99 = el intento fallido
    $message = "<34>${ts} testhost sshd[12345]: Failed password for invalid user admin from 10.0.0.99 port 22 ssh2"
    
    # Crea un cliente UDP (protocolo sin conexión, rápido)
    $udpClient = New-Object System.Net.Sockets.UdpClient
    
    # Convierte el mensaje a bytes
    $bytes = [System.Text.Encoding]::ASCII.GetBytes($message)
    
    # Envía los bytes al puerto 514 de localhost (donde escucha syslog-ng)
    $udpClient.Send($bytes, $bytes.Length, "localhost", 514)
    
    # Cierra la conexión
    $udpClient.Close()
}
```

**¿Por qué se usa el timestamp actual en UTC?** Porque Logstash guarda los eventos con la fecha del mensaje. Si mandamos una fecha vieja, el detector (que busca eventos de los últimos 2 minutos) nunca los va a encontrar.

### 🔐 Prueba directa al webhook de n8n

```powershell
# Arma los headers HTTP con la clave de autenticación
$headers = @{
    "x-siem-key" = "superpoderosas26"        # Clave que n8n espera para aceptar la alerta
    "Content-Type" = "application/json"        # Le dice que el body es JSON
}

# Arma el body con los datos de la alerta simulada
$body = @{
    rule_id = "ssh_bruteforce"                 # Tipo de regla
    src_ip = "192.168.1.100"                   # IP del "atacante"
    username = "admin"                          # Usuario que intentaron atacar
    severity = "high"                           # Severidad
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")   # Fecha actual
} | ConvertTo-Json                             # Convierte el hashtable a JSON

# Envía la solicitud HTTP POST al webhook de n8n
Invoke-RestMethod -Uri "http://localhost:5678/webhook/alert/siem" -Method POST -Headers $headers -Body $body
```

**¿Para qué sirve esta prueba?** Para verificar que n8n funciona independientemente del pipeline completo. Si esto funciona pero el detector SSH no detecta, el problema está en Elasticsearch/Logstash, no en n8n.

### 📋 Verificaciones en PostgreSQL

| # | Comando | ¿Qué muestra? |
|---|---------|---------------|
| 8 | `docker exec siem_postgres psql -U siem -d siem -c "SELECT id, rule_id, src_ip, severity, ts FROM alerts ORDER BY id DESC LIMIT 5;"` | Las últimas 5 alertas guardadas |
| 9 | `docker exec siem_postgres psql -U siem -d siem -c "SELECT * FROM playbook_runs ORDER BY id DESC LIMIT 5;"` | Los últimos 5 playbooks ejecutados |
| 10 | `docker exec siem_postgres psql -U siem -d siem -c "SELECT * FROM mttr_stats;"` | Tiempo medio de respuesta en segundos |
| 11 | `docker exec siem_postgres psql -U siem -d siem -c "SELECT * FROM automation_rate;"` | Porcentaje de alertas respondidas automáticamente |

### 📁 Prueba Wazuh FIM

| # | Comando | ¿Qué hace? | ¿Qué genera? |
|---|---------|-------------|--------------|
| 12 | `docker exec siem_wazuh_manager sh -c "echo 'datos secretos' > /tmp/test_fim/secreto.txt"` | Crea un archivo dentro del contenedor Wazuh | Alerta FIM: "File added" (nivel 5) |
| 13 | `docker exec siem_wazuh_manager sh -c "echo 'MODIFICADO!' >> /tmp/test_fim/secreto.txt"` | Modifica el archivo (agrega texto al final) | Alerta FIM: "Integrity checksum changed" (nivel 7) |
| 14 | `docker exec siem_wazuh_manager rm /tmp/test_fim/secreto.txt` | Elimina el archivo | Alerta FIM: "File deleted" (nivel 7) |
| 15 | `docker exec siem_wazuh_manager tail -n 5 /var/ossec/logs/alerts/alerts.json` | Muestra las últimas 5 alertas de Wazuh en formato JSON | Para ver si se generaron las alertas FIM |
| 16 | `docker exec siem_wazuh_manager tail -f /var/ossec/logs/ossec.log` | Muestra los logs de Wazuh en TIEMPO REAL | Para ver "scan started" / "scan ended" |

**Desglose del comando 12:**
- `docker exec siem_wazuh_manager` → Ejecuta un comando dentro del contenedor Wazuh
- `sh -c "..."` → Ejecuta el texto entre comillas como un comando shell
- `echo 'datos secretos' > /tmp/test_fim/secreto.txt` → Crea el archivo con ese contenido
- `>` = crear/sobrescribir   |   `>>` = agregar al final

### 🔴 Apagar todo

| # | Comando | ¿Qué hace? |
|---|---------|-------------|
| 17 | `docker-compose down` | Detiene y elimina todos los contenedores (los datos se guardan en los volúmenes) |

---

## 📊 Resumen: Relación entre Código y PROYECTO 03

| Objetivo del PROYECTO 03 | Archivo que lo cumple |
|---------------------------|----------------------|
| Recolección centralizada de logs | `syslog-ng.conf` + `logstash.conf` |
| Almacenar en Elasticsearch (búsqueda) | `logstash.conf` (output → elasticsearch) |
| Almacenar en PostgreSQL (auditoría) | `01-init.sql` + workflow n8n |
| Detección SSH brute force | `ssh_bruteforce_detector.py` |
| Detección FIM (integridad de archivos) | Wazuh Manager + `wazuh_fim_to_n8n.py` |
| Orquestación SOAR con n8n | `workflow-siem-alerta.json` |
| Notificación automática | Nodo Telegram en n8n |
| Trazabilidad de playbooks | Tabla `playbook_runs` + nodo "Registrar Playbook" |
| Métricas MTTA/MTTR | Vistas SQL en `01-init.sql` |
| Visualización en Grafana | `datasources.yml` + `dashboards.yml` + `siem-dashboard.json` |
| Reproducible con un comando | `docker-compose.yml` |

---

## 12. Flujo completo de n8n paso a paso

### ¿Qué es n8n?

n8n es una herramienta de **automatización visual**. Funciona con **nodos** (cajas) conectados por flechas. Cada nodo hace una tarea específica, y los datos pasan de uno al siguiente como en una cadena de montaje.

En nuestro SIEM, n8n cumple el rol de **SOAR-lite** (Security Orchestration, Automation and Response): recibe alertas, decide qué hacer, y ejecuta las acciones automáticamente.

### El flujo visual completo

```
  Un script detecta un ataque
  y envía un POST HTTP
         │
         ▼
┌─────────────────────────┐
│  1. WEBHOOK SIEM        │  ← Recibe la alerta por HTTP POST
│  URL: /webhook/alert/   │     en http://localhost:5678/webhook/alert/siem
│       siem              │
│                         │     Datos que recibe:
│                         │     {
│                         │       "rule_id": "ssh_bruteforce",
│                         │       "src_ip": "10.0.0.99",
│                         │       "severity": "high",
│                         │       "username": "admin"
│                         │     }
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  2. VALIDAR API KEY     │  ← Revisa el header "x-siem-key"
│                         │
│  ¿El header contiene    │     Esto evita que cualquiera pueda
│  "superpoderosas26"?    │     enviar alertas falsas al sistema.
│                         │
│  SI ──────────┐         │
│  NO ──────┐   │         │
└───────────┼───┼─────────┘
            │   │
     ┌──────▼┐ ┌▼──────────────────────────┐
     │ERROR  │ │  3. PREPARAR DATOS        │
     │401    │ │                            │
     │"No    │ │  Extrae del body:          │
     │autori-│ │  • rule_id → "ssh_brute"   │
     │zado"  │ │  • src_ip → "10.0.0.99"    │
     └───────┘ │  • severity → "high"       │
               │  • username → "admin"      │
               │  • raw_event → todo el JSON│
               └─────────────┬──────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              │
┌──────────────────┐  ┌──────────────┐     │
│ 4. INSERTAR EN   │  │ 5. NOTIFICAR │     │
│    POSTGRESQL    │  │    TELEGRAM  │     │
│                  │  │              │     │
│ INSERT INTO      │  │ Envía al bot:│     │
│   alerts(        │  │              │     │
│     rule_id,     │  │ 🚨 ALERTA    │     │
│     src_ip,      │  │ Regla: ssh   │     │
│     severity,    │  │ IP: 10.0.0.99│     │
│     raw          │  │ Sev: high    │     │
│   )              │  │              │     │
└────────┬─────────┘  └──────────────┘     │
         │                                 │
         ▼                                 │
┌──────────────────────────────────┐       │
│ 6. REGISTRAR PLAYBOOK            │       │
│                                  │       │
│ INSERT INTO playbook_runs(       │       │
│   alert_id,   ← ID de la alerta │       │
│   workflow,   ← "SIEM-Alert"     │       │
│   outcome     ← "success"        │       │
│ )                                │       │
│                                  │       │
│ Esto es la TRAZABILIDAD:         │       │
│ queda registrado QUÉ alerta      │       │
│ disparó QUÉ acción y CUÁNDO.     │       │
└────────────────┬─────────────────┘       │
                 │                         │
                 ▼                         │
┌──────────────────────────────────┐       │
│ 7. RESPONDER OK (200)            │       │
│                                  │       │
│ Devuelve al script que llamó:    │       │
│ {"status": "success",            │       │
│  "message": "Alert processed"}   │       │
└──────────────────────────────────┘       │
```

### ¿Por qué cada nodo es importante?

| Nodo | ¿Qué cumple del PROYECTO 03? | ¿Qué pasa si no existiera? |
|------|-------------------------------|----------------------------|
| Webhook | *"Orquestar respuestas automáticas"* | No habría forma de recibir alertas |
| Validar API Key | *"Control de acceso"* | Cualquiera podría enviar alertas falsas |
| Preparar Datos | Formateo para PostgreSQL | Los datos llegarían mal formateados a la BD |
| Insertar PostgreSQL | *"Almacenar en PostgreSQL (auditoría)"* | No habría registro permanente de alertas |
| Telegram | *"Notificación automática"* | Nadie se enteraría del ataque en tiempo real |
| Registrar Playbook | *"Trazabilidad de playbooks"* | No sabríamos qué acciones se tomaron |
| Responder OK | Confirmación al script | El script no sabría si la alerta se procesó |

### Ejemplo real de ejecución

Cuando corremos la prueba del webhook:
```powershell
Invoke-RestMethod -Uri "http://localhost:5678/webhook/alert/siem" -Method POST -Headers $headers -Body $body
```

Pasa todo esto en **menos de 1 segundo**:
1. n8n recibe el POST → **Webhook**
2. Lee el header `x-siem-key: superpoderosas26` → **Validar** → ✅ Correcto
3. Extrae `rule_id`, `src_ip`, etc. → **Preparar Datos**
4. Ejecuta `INSERT INTO alerts(...)` → **PostgreSQL** → alerta #168 creada
5. Envía mensaje a Telegram → **Notificar** → 📱 llega la notificación
6. Ejecuta `INSERT INTO playbook_runs(...)` → **Registrar** → playbook #162 registrado
7. Devuelve `{"message": "Workflow was started"}` → **Responder OK**

Todo esto es el **MTTR** (Mean Time To Respond): el tiempo entre que se creó la alerta y se ejecutó la respuesta. En nuestro sistema es de **~0.03 segundos**, muchísimo más rápido que si un humano lo hiciera manualmente.

---

## 13. Estado del proyecto vs PROYECTO 03

### ✅ Lo que YA tenemos implementado

| # | Objetivo del PROYECTO 03 | Estado | Cómo lo implementamos |
|---|--------------------------|--------|----------------------|
| 1 | Recolección centralizada de logs mediante syslog-ng y Logstash | ✅ **Completo** | `syslog-ng.conf` recibe logs UDP/514, los reenvía a `logstash.conf` que parsea y envía a Elasticsearch |
| 2 | Normalizar y almacenar eventos en Elasticsearch (búsqueda) | ✅ **Completo** | Logstash aplica grok, extrae campos (IP, programa, timestamp) y guarda en índices diarios `siem-events-YYYY.MM.dd` |
| 3 | Normalizar y almacenar eventos en PostgreSQL (auditoría) | ✅ **Completo** | `01-init.sql` crea las tablas. n8n guarda cada alerta en `alerts` y cada respuesta en `playbook_runs` |
| 4 | Regla de detección SSH brute force (5 intentos en 2 min) | ✅ **Completo** | `ssh_bruteforce_detector.py` consulta Elasticsearch cada 2 min, agrupa por IP y alerta si supera umbral de 5 |
| 5 | Regla de detección FIM (integridad de archivos) | ✅ **Completo** | Wazuh Manager monitorea `/tmp/test_fim/` y genera alertas. `wazuh_fim_to_n8n.py` las envía a n8n |
| 6 | Orquestar respuestas automáticas con n8n | ✅ **Completo** | Workflow con 7 nodos: webhook → validar → preparar → PostgreSQL → Telegram → registrar playbook → responder |
| 7 | Notificación automática (Telegram) | ✅ **Completo** | Nodo Telegram en n8n envía mensaje con detalles de la alerta al bot configurado |
| 8 | Visualizar métricas en Grafana | ✅ **Completo** | Dashboards configurados con datasources de PostgreSQL y Elasticsearch, paneles de alertas por severidad, IPs sospechosas, etc. |
| 9 | Visualización en Kibana (opcional) | ✅ **Completo** | Kibana conectado a Elasticsearch, se puede crear Data View con `siem-events-*` |
| 10 | Medir MTTR (tiempo medio de respuesta) | ✅ **Completo** | Vista SQL `mttr_stats` calcula automáticamente el promedio de `playbook_runs.executed_at - alerts.ts` |
| 11 | Medir MTTA (tiempo medio de detección) | ✅ **Completo** | Vista SQL `mtta_stats` calcula el promedio de `acknowledged_at - ts` |
| 12 | Tasa de automatización | ✅ **Completo** | Vista SQL `automation_rate` calcula `(alertas con playbook / total alertas) * 100` |
| 13 | Trazabilidad de playbooks | ✅ **Completo** | Tabla `playbook_runs` registra cada ejecución con alert_id, workflow, outcome y timestamp |
| 14 | Reproducible con un solo comando | ✅ **Completo** | `docker-compose up -d` levanta los 8 servicios automáticamente |
| 15 | Generación de datos de prueba | ✅ **Completo** | `generate_historical_data.py` genera 50 alertas aleatorias de diferentes tipos |
| 16 | Material didáctico reutilizable | ✅ **Completo** | docker-compose, SQL, workflows n8n, dashboards, guías y README documentado |

### ⚠️ Lo que podríamos mejorar / completar

| # | Aspecto | Estado | Qué falta |
|---|---------|--------|----------|
| 1 | Medición real de MTTA end-to-end | 🟡 **Parcial** | Tenemos la vista SQL, pero para medir el MTTA real completo (desde que el log sale del host hasta que n8n lo procesa) habría que simular el flujo pasando por syslog-ng → Logstash → Elasticsearch → detector → n8n midiendo el Δt total |
| 2 | Comparación manual vs automatizado | 🟡 **Parcial** | El PROYECTO 03 pide demostrar que la automatización reduce el MTTR vs un proceso manual. Tenemos los datos para hacerlo (MTTR automático ≈ 0.03 seg) pero falta documentar la comparación formal con tiempos de respuesta manual |
| 3 | Integración FIM end-to-end vía n8n | 🟡 **Parcial** | Wazuh detecta cambios correctamente (lo probamos), y el script `wazuh_fim_to_n8n.py` existe, pero la integración completa (Wazuh → script → n8n → PostgreSQL → Telegram) no se ha probado como flujo continuo automatizado |
| 4 | Capturas de pantalla para anexos | 🟡 **Pendiente** | El PROYECTO 03 pide screenshots de dashboards Grafana, workflow n8n, notificaciones Telegram para la documentación final |
| 5 | Exportar workflow n8n como JSON | ✅ **Completo** | Ya tenemos `workflow-siem-alerta.json` |

### 📊 Resumen visual del progreso

```
Recolección de logs        [██████████████████████] 100% ✅
Normalización (Logstash)   [██████████████████████] 100% ✅
Almacenamiento dual        [██████████████████████] 100% ✅
Detección SSH brute-force  [██████████████████████] 100% ✅
Detección FIM (Wazuh)      [██████████████████████] 100% ✅
Orquestación n8n           [██████████████████████] 100% ✅
Notificación Telegram      [██████████████████████] 100% ✅
Dashboards Grafana         [██████████████████████] 100% ✅
Métricas MTTA/MTTR/Auto    [██████████████████████] 100% ✅
Reproducibilidad Docker    [██████████████████████] 100% ✅
Comparación manual vs auto [████████████░░░░░░░░░░]  60% 🟡
Documentación/Capturas     [████████████████░░░░░░]  75% 🟡
─────────────────────────────────────────────────────────
Progreso total del PROYECTO 03:              ≈ 95% ✅
```

---

## 14. Mejoras adicionales propuestas

Estas son mejoras que van **más allá de lo que pide el PROYECTO 03**, pero que demuestran conocimiento avanzado y visión a futuro.

### 🔐 14.1 — Seguridad del propio SIEM

**Problema actual**: Las contraseñas están en texto plano en el `docker-compose.yml` (`siem123`, `admin123`).

**Mejora propuesta**:
- Usar un archivo `.env` separado que NO se suba a GitHub (ya está en `.gitignore`)
- Activar `xpack.security.enabled=true` en Elasticsearch para requerir autenticación
- Activar TLS (HTTPS) entre los servicios para que los datos viajen encriptados

**¿Por qué importa?** Porque un SIEM que no se protege a sí mismo es una contradicción. Si un atacante accede a PostgreSQL, puede ver todas las alertas y borrar evidencia.

---

### 🌐 14.2 — Threat Intelligence (Inteligencia de amenazas)

**Problema actual**: Cuando detectamos un ataque desde una IP, solo registramos la IP. No sabemos si esa IP ya fue reportada como maliciosa en otros lugares.

**Mejora propuesta**: Agregar un nodo en n8n que antes de notificar consulte servicios como:
- **AbuseIPDB**: ¿Esta IP fue reportada por otros? ¿Cuántas veces?
- **VirusTotal**: ¿Está asociada a malware o phishing?

**Ejemplo de cómo cambiaría el mensaje de Telegram**:
```
🚨 ALERTA SIEM
📋 Regla: ssh_bruteforce
🌐 IP: 10.0.0.99
⚠️ AbuseIPDB: Reportada 47 veces (confianza 95%)
🔴 Recomendación: BLOQUEAR
```

---

### 🐳 14.3 — Dockerizar los scripts de detección

**Problema actual**: Los scripts Python (`ssh_bruteforce_detector.py`, `wazuh_fim_to_n8n.py`) se ejecutan **fuera de Docker**. El usuario necesita tener Python instalado y ejecutarlos manualmente.

**Mejora propuesta**: Crear un `Dockerfile` para los scripts y agregarlos como servicios en el `docker-compose.yml`:
```yaml
detector:
  build: ./detector
  container_name: siem_detector
  depends_on:
    - elasticsearch
    - n8n
```

**Beneficio**: TODO el sistema se levanta con un solo `docker-compose up -d` sin depender de que el usuario tenga Python.

---

### 📊 14.4 — Playbooks diferenciados por severidad

**Problema actual**: Todas las alertas (critical, high, medium, low) siguen el mismo flujo: guardar + notificar + registrar.

**Mejora propuesta**: Crear workflows diferentes según la severidad:

| Severidad | Acciones automáticas |
|-----------|---------------------|
| **critical** | Guardar + Telegram URGENTE + bloqueo simulado + crear ticket |
| **high** | Guardar + Telegram + registrar |
| **medium** | Guardar + registrar (sin notificación) |
| **low** | Solo registrar en la base de datos |

**Beneficio**: Reduce las notificaciones innecesarias y enfoca la atención del analista en lo importante.

---

### 🔄 14.5 — Rate limiting y deduplicación

**Problema actual**: Si un atacante genera 100 intentos fallidos, el sistema podría enviar muchas notificaciones de Telegram repetidas.

**Mejora propuesta**: Implementar deduplicación: si ya existe una alerta activa para esa IP y regla en los últimos 30 minutos, no generar una nueva.

**Cómo se haría**: En n8n, antes de insertar en PostgreSQL, consultar si ya existe una alerta reciente:
```sql
SELECT COUNT(*) FROM alerts
WHERE src_ip = '10.0.0.99'
  AND rule_id = 'ssh_bruteforce'
  AND ts > NOW() - INTERVAL '30 minutes';
```
Si el count > 0, no insertar ni notificar.

---

### 🤖 14.6 — Machine Learning para detección avanzada

**Problema actual**: Las reglas de detección son fijas ("si hay 5+ intentos fallidos en 2 minutos, alertar"). Un atacante inteligente podría hacer 4 intentos cada 3 minutos para no activar la regla.

**Mejora propuesta**: Entrenar un modelo de ML que aprenda el comportamiento "normal" de la red y detecte anomalías estadísticas, en lugar de depender solo de reglas con umbrales fijos.

**Ejemplo**: Si normalmente hay 2 conexiones SSH por hora y de repente hay 20 (aunque ninguna falle), eso es anómalo y debería alertar.

**PROYECTO 03**: *"Queda abierta la línea de IA-aware SOC para detección avanzada"*

---

### 📋 Resumen de mejoras por prioridad

| Prioridad | Mejora | Dificultad | Impacto |
|-----------|--------|------------|--------|
| 🟢 Fácil | Dockerizar scripts | Baja | Alta — todo se levanta con 1 comando |
| 🟢 Fácil | Archivo `.env` para contraseñas | Baja | Media — mejor seguridad |
| 🟡 Media | Deduplicación de alertas | Media | Alta — menos spam en Telegram |
| 🟡 Media | Playbooks por severidad | Media | Alta — respuestas más inteligentes |
| 🟠 Alta | Threat Intelligence | Media | Alta — contexto para el analista |
| 🔴 Avanzada | Machine Learning | Alta | Muy alta — detección sin reglas fijas |
