# Guía de Testing — SIEM/SOAR TP-Final

## Prerequisitos

- Docker Desktop corriendo
- Python 3.x instalado
- PowerShell/Terminal con acceso al directorio `C:\TP-Final`

---

## PASO 1 — Levantar la infraestructura

```bash
cd C:\TP-Final
docker compose up -d
```

Esperar ~2-3 minutos a que todos los servicios inicien. Verificar que todos estén `healthy`:

```bash
docker compose ps
```

Todos deben mostrar `Up` o `healthy`. Si alguno falla, revisar logs:

```bash
docker compose logs <nombre-servicio>
```

---

## PASO 2 — Verificar servicios web accesibles

Abrir en el navegador:

| Servicio | URL | Credenciales |
|----------|-----|-------------|
| **Grafana** | `http://localhost:3000` | `admin / admin123` |
| **Kibana** | `http://localhost:5601` | Sin login |
| **n8n** | `http://localhost:5678` | Sin login |
| **Dashboard (Streamlit)** | `http://localhost:8501` | Sin login |
| **Elasticsearch** | `http://localhost:9200` | Sin login |

Para verificar Elasticsearch rápido:

```bash
curl http://localhost:9200/_cluster/health
```

Debe retornar `"status":"green"` o `"yellow"`.

---

## PASO 3 — Verificar la base de datos PostgreSQL

```bash
docker exec -it tp-final-postgres-1 psql -U siem -d siem -c "\dt"
```

Debe listar las tablas: `alerts`, `incidents`, `playbook_runs`, `events_raw`, `ip_blacklist`, `failed_alerts`.

---

## PASO 4 — Importar y activar workflows en n8n

1. Ir a `http://localhost:5678`
2. Ir a **Workflows → Import from File**
3. Importar estos archivos desde `C:\TP-Final\n8n\`:
   - `SIEM - Alerta Entrante.json` ← el principal
   - `SIEM - Reporte Diario.json`
   - `SIEM - Error Handler.json`
4. Activar cada workflow con el toggle **Active**
5. Anotar la URL del webhook del workflow principal (generalmente `http://localhost:5678/webhook/alert/siem`)

---

## PASO 5 — Probar el simulador de ataques

```bash
cd C:\TP-Final\detector
pip install -r ..\requirements.txt   # si no están instalados
```

### Opción A — Menú interactivo

```bash
python attack_simulator.py
```

### Opción B — Ataque SSH brute-force automático

```bash
python attack_simulator.py --brute
```

### Opción C — Mix de todos los ataques

```bash
python attack_simulator.py --auto
```

Esto envía alertas JSON al webhook de n8n. Verificar en la terminal que las peticiones retornen `200 OK`.

---

## PASO 6 — Verificar que n8n procesó las alertas

1. En `http://localhost:5678` → abrir el workflow **"SIEM - Alerta Entrante"**
2. Hacer clic en **Executions** (historial de ejecuciones)
3. Deben aparecer ejecuciones recientes con estado **Success**
4. Hacer clic en una ejecución para ver cada nodo procesado

---

## PASO 7 — Verificar datos en PostgreSQL

```bash
docker exec -it tp-final-postgres-1 psql -U siem -d siem -c "SELECT COUNT(*) FROM alerts;"
docker exec -it tp-final-postgres-1 psql -U siem -d siem -c "SELECT * FROM alerts ORDER BY created_at DESC LIMIT 5;"
docker exec -it tp-final-postgres-1 psql -U siem -d siem -c "SELECT * FROM incidents LIMIT 5;"
```

---

## PASO 8 — Verificar Grafana dashboards

1. Ir a `http://localhost:3000` → **Dashboards**
2. Abrir **SIEM Dashboard** — debe mostrar:
   - Conteo de alertas por severidad
   - MTTR / MTTA
   - Top IPs atacantes
3. Abrir **SOAR Operations** — debe mostrar tasa de automatización
4. Si los panels muestran "No data", es posible que las alertas aún no tengan `responded_at` seteado

---

## PASO 9 — Verificar el dashboard Streamlit

1. Ir a `http://localhost:8501`
2. Debe mostrar KPIs: total de alertas, incidentes abiertos, MTTR, MTTA
3. Si muestra error de conexión a DB, verificar que PostgreSQL esté corriendo

---

## PASO 10 — Probar el detector SSH en tiempo real

En una terminal separada, dejar corriendo el detector:

```bash
cd C:\TP-Final\detector
python ssh_bruteforce_detector.py
```

Luego en otra terminal enviar tráfico simulado:

```bash
python attack_simulator.py --brute
```

El detector debe imprimir los ataques detectados cada 2 minutos.

---

## PASO 11 — Probar generación de reporte

```bash
cd C:\TP-Final\detector
python generate_report.py
```

Debe imprimir en consola un reporte con las 12 métricas del sistema.

---

## PASO 12 — Probar el Blocker API (requiere admin)

Abrir PowerShell **como Administrador**:

```bash
cd C:\TP-Final\blocker
pip install flask
python blocker_api.py
```

En otra terminal, probar bloquear una IP:

```bash
curl -X POST http://localhost:8765/block \
  -H "Content-Type: application/json" \
  -H "x-siem-key: siem-secret-key" \
  -d "{\"ip\": \"1.2.3.4\", \"reason\": \"test\"}"
```

Verificar las reglas activas:

```bash
curl http://localhost:8765/rules \
  -H "x-siem-key: siem-secret-key"
```

---

## PASO 13 — Verificar Kibana (opcional)

1. Ir a `http://localhost:5601`
2. Ir a **Discover**
3. Crear un index pattern: `siem-events-*`
4. Debe mostrar los eventos enviados por el simulador vía Logstash

---

## Checklist de validación final

- [ ] Todos los contenedores Docker en estado `Up`
- [ ] n8n recibe y procesa alertas (executions exitosas)
- [ ] PostgreSQL tiene registros en `alerts` e `incidents`
- [ ] Grafana muestra datos en los dashboards
- [ ] Streamlit dashboard carga sin errores
- [ ] Simulador envía alertas y obtiene `200 OK`
- [ ] Reporte genera métricas correctamente

---

## Apagar todo al terminar

```bash
cd C:\TP-Final
docker compose down
```

Para borrar también los volúmenes (datos):

```bash
docker compose down -v
```
