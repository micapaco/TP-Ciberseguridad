# Documentación de Workflows n8n — Sistema SIEM

## Índice

1. [SIEM - Alerta Entrante](#1-siem---alerta-entrante)
2. [SIEM - Error Handler](#2-siem---error-handler)
3. [SIEM - Reporte Diario](#3-siem---reporte-diario)

---

## 1. SIEM - Alerta Entrante

### Descripción general

Es el workflow principal del sistema. Se activa cada vez que llega una alerta desde un agente externo (ej. Wazuh). Recibe los datos, los enriquece con threat intelligence, calcula un risk score y ejecuta una respuesta automática según el nivel de riesgo detectado.

### Trigger

- **Tipo:** Webhook HTTP (POST)
- **Path:** `/alert/siem`
- **Autenticación:** Header Auth

### Flujo completo

#### Paso 1 — Enriquecer Datos

Al recibir la alerta, se normalizan y enriquecen los campos del body:

| Campo | Descripción |
|---|---|
| `priority` | P1-URGENTE / P2-ALTA / P3-NORMAL según severity |
| `classification` | "Ataque de acceso" si la regla contiene "ssh", sino "Integridad de archivos" |
| `severity` | Normalizado a lowercase |
| `rule_id`, `src_ip`, `username`, `timestamp` | Pasados tal cual del body |

#### Paso 2 — Filtrar por Severidad

Un nodo Switch divide el flujo según la severidad de la alerta:

- **critical / high** → continúa al paso 3 (flujo completo)
- **low** → se registra directamente en la tabla `alerts` + `playbook_runs` con outcome `logged_low` y el flujo termina

#### Paso 3 — Verificar Incidente Activo (solo critical/high)

Se consulta la BD para saber si la IP origen ya tiene un incidente **abierto**.

- **Si ya existe** → envía alerta de reincidencia por Telegram (`Alerta Reincidencia`) y el flujo termina
- **Si no existe** → continúa al paso 4

#### Paso 4 — Insertar Alerta

Se inserta la alerta en la tabla `alerts` (PostgreSQL) con `RETURNING id`. A partir de aquí se bifurca en dos ramas paralelas:

---

##### Rama A — Detección de Password Spraying

1. **Contar IPs únicas:** Cuenta cuántas IPs distintas atacaron el mismo `username` en los últimos 5 minutos.
2. **¿Es Password Spraying?** Si hay 5 o más IPs distintas:
   - Crea un incidente de tipo `password_spraying` en la tabla `incidents` (severity = critical).
   - Envía alerta por Telegram describiendo el ataque distribuido.
   - Registra el playbook run con outcome `incident_created`.

---

##### Rama B — Threat Intelligence + Risk Scoring

1. **Consultar AbuseIPDB:** Llama a la API de AbuseIPDB para obtener:
   - `countryCode`, `abuseConfidenceScore`, `totalReports`, `isp`

2. **Guardar País:** Actualiza el campo `country_code` de la alerta en la BD.

3. **Contar Alertas:** Cuenta cuántas alertas de la misma IP+regla hubo en los últimos 10 minutos.

4. **Reputación Interna:** Cuenta alertas de la IP en los últimos 7 días (historial interno).

5. **Calcular Risk Score:** Motor de scoring con los siguientes factores:

   | Factor | Condición | Puntos |
   |---|---|---|
   | Severidad | critical | +40 |
   | Severidad | high | +25 |
   | Intentos (10 min) | >= 10 | +40 |
   | Intentos (10 min) | >= 5 | +25 |
   | Intentos (10 min) | >= 3 | +10 |
   | AbuseIPDB score | >= 80% | +30 |
   | AbuseIPDB score | >= 50% | +15 |
   | Reportes externos | >= 100 | +10 |
   | Historial 7 días | >= 20 alertas | +25 |
   | Historial 7 días | >= 10 alertas | +15 |
   | Historial 7 días | >= 5 alertas | +10 |

   **Niveles de riesgo:**
   - `critical` → score >= 70 (crea incidente + bloqueo)
   - `high` → score >= 40 (alerta)
   - `low` → score < 40 (solo notificación)

6. **Detectar Ataque:** Evalúa si `risk_level === "critical"`.

---

#### Paso 5A — Flujo de riesgo NO crítico

Si el risk score no es crítico:

- **Registrar Playbook** con outcome `success`
- **Email Alerta** con detalles completos (regla, IP, usuario, AbuseIPDB, risk score)
- **Enviar Mensaje Telegram** con resumen de la alerta

---

#### Paso 5B — Flujo de riesgo CRÍTICO (respuesta automatizada SOAR)

1. **Verificar Incidente Abierto:** Revisa si ya existe un incidente abierto para esta IP+regla en los últimos 10 minutos.

2. **¿Crear nuevo incidente?** Si no existe:
   - **Crear Incidente:** Inserta en tabla `incidents` (tipo `bruteforce`, `RETURNING id`).
   - **Bloquear IP:** Inserta la IP en la tabla `ip_blacklist` con expiración de 24 horas.
   - **Enforce Block:** Llama al endpoint `http://host.docker.internal:8765/block` (agente de bloqueo externo) via HTTP POST con la IP y el ID de incidente.
   - **Actualizar Enforcement:** Actualiza `ip_blacklist` con el resultado del bloqueo (`enforced`, `enforcement_message`, `enforced_at`).
   - **Notificar Bloqueo:** Telegram — confirma que la IP fue bloqueada automáticamente por 24h.
   - **Mensaje especial:** Telegram — alerta de incidente de seguridad con todos los detalles.
   - **Email de Incidente:** Email con el reporte completo del incidente crítico.
   - **Registrar Playbook1** con outcome `blocked`.

---

### Diagrama de flujo simplificado

```
Webhook
  └─► Enriquecer Datos
        └─► Filtrar por Severidad
              ├─► [low] Registrar Playbook Low (fin)
              └─► [critical/high] Verificar Incidente Activo
                    ├─► [ya existe] Alerta Reincidencia (fin)
                    └─► [no existe] Insertar Alerta
                          ├─► Contar IPs únicas
                          │     └─► ¿Password Spraying? (>=5 IPs/5min)
                          │           └─► Crear Incidente Spraying → Alerta Spraying
                          └─► Consultar AbuseIPDB
                                └─► Guardar País
                                      └─► Contar Alertas
                                            └─► Reputación Interna
                                                  └─► Calcular Risk Score
                                                        └─► Detectar Ataque
                                                              ├─► [no crítico] Registrar Playbook → Email + Telegram
                                                              └─► [crítico] Verificar Incidente Abierto
                                                                    └─► ¿Crear nuevo incidente?
                                                                          └─► Crear Incidente
                                                                                └─► Bloquear IP
                                                                                      └─► Enforce Block
                                                                                            └─► Actualizar Enforcement
                                                                                                  └─► Notificar Bloqueo
                                                                                                        ├─► Mensaje especial (Telegram)
                                                                                                        └─► Email de Incidente
```

### Tablas de base de datos utilizadas

| Tabla | Operación | Descripción |
|---|---|---|
| `alerts` | INSERT + UPDATE | Registra cada alerta con su país |
| `incidents` | INSERT | Incidentes de bruteforce o password spraying |
| `ip_blacklist` | INSERT + UPDATE | IPs bloqueadas automáticamente (24h) |
| `playbook_runs` | INSERT | Trazabilidad de acciones ejecutadas |

---

## 2. SIEM - Error Handler

### Descripción general

Workflow de guardia que captura cualquier error que ocurra en otros workflows de n8n. Notifica al equipo y persiste el error en la base de datos para auditoría.

### Trigger

- **Tipo:** Error Trigger
- Se activa automáticamente cuando cualquier workflow falla en n8n.

### Flujo

```
Error Trigger
  └─► Notificar Error por Telegram
        └─► Guardar Error en PostgreSQL
```

#### Nodo 1 — Notificar Error por Telegram

Envía un mensaje al canal de Telegram con:

- Nodo donde ocurrió el error (`execution.lastNodeExecuted`)
- Mensaje de error (`execution.error.message`)
- Nombre del workflow fallido (`execution.workflowData.name`)
- ID de ejecución (`execution.id`)

Formato del mensaje:
```
❌ ERROR EN SIEM
⚙️ Nodo: <nombre del nodo>
📋 Error: <descripción>
🔗 Workflow: <nombre>
🔢 Ejecución: #<id>
⚠️ Revisar manualmente en n8n
```

#### Nodo 2 — Guardar Error en PostgreSQL

Inserta el error en la tabla `failed_alerts` con:

- `error_node`: último nodo ejecutado
- `error_message`: primeros 200 caracteres del error
- `alert_data`: `{}`(vacío por defecto)

### Tablas de base de datos utilizadas

| Tabla | Operación | Descripción |
|---|---|---|
| `failed_alerts` | INSERT | Log de errores de ejecución de workflows |

---

## 3. SIEM - Reporte Diario

### Descripción general

Workflow programado que genera y distribuye un resumen ejecutivo diario del estado del SIEM: métricas de alertas, incidentes, KPIs de automatización y las IPs más sospechosas del sistema.

### Trigger

- **Tipo:** Schedule Trigger
- **Horario:** Todos los días a las **08:00 hs**

### Flujo

```
Schedule Trigger
  └─► Obtener Métricas (PostgreSQL)
        └─► Top IPs (PostgreSQL)
              └─► Formatear Reporte (JavaScript)
                    ├─► Enviar Reporte Telegram
                    └─► Email Reporte
```

#### Nodo 1 — Obtener Métricas

Ejecuta una query SQL que obtiene en una sola consulta:

| Métrica | Descripción |
|---|---|
| `total_alerts` | Total histórico de alertas |
| `alerts_24h` | Alertas de las últimas 24 horas |
| `alerts_7d` | Alertas de los últimos 7 días |
| `open_incidents` | Incidentes con status = 'open' |
| `total_incidents` | Total histórico de incidentes |
| `mttr_seconds` | MTTR promedio en segundos (tiempo entre alerta y ejecución de playbook) |
| `auto_rate` | Porcentaje de alertas con playbook ejecutado automáticamente |
| `failed_count` | Alertas fallidas sin resolver |

#### Nodo 2 — Top IPs

Obtiene las **5 IPs origen con mayor cantidad de alertas** en el historial, ordenadas de mayor a menor.

#### Nodo 3 — Formatear Reporte

Código JavaScript que construye el reporte en texto plano con el siguiente formato:

```
📊 REPORTE DIARIO SIEM — YYYY-MM-DD HH:MM
━━━━━━━━━━━━━━━━━━

📈 RESUMEN
  Total alertas: <n>
  Últimas 24h: <n>
  Últimos 7 días: <n>

⏱️ MÉTRICAS KPI
  MTTR: <n>s
  Automatización: <n>%

🔒 INCIDENTES
  Abiertos: <n>
  Total: <n>
  Alertas fallidas: <n>

🌐 TOP 5 IPs SOSPECHOSAS
  1. <ip> (<n> alertas)
  ...
━━━━━━━━━━━━━━━━━━
🤖 Reporte automático del SIEM
```

#### Nodo 4A — Enviar Reporte Telegram

Envía el reporte formateado al canal de Telegram configurado.

#### Nodo 4B — Email Reporte

Envía el mismo reporte por email (SMTP) con asunto:
`📊 Reporte Diario SIEM — YYYY-MM-DD`

### Tablas de base de datos utilizadas

| Tabla | Operación | Descripción |
|---|---|---|
| `alerts` | SELECT | Conteo de alertas y top IPs |
| `incidents` | SELECT | Conteo de incidentes abiertos y totales |
| `playbook_runs` | SELECT | Cálculo de MTTR y tasa de automatización |
| `failed_alerts` | SELECT | Conteo de alertas fallidas pendientes |

---

## Resumen de integraciones externas

| Integración | Uso | Workflow(s) |
|---|---|---|
| **PostgreSQL** | Persistencia de alertas, incidentes, blacklist, errores y métricas | Todos |
| **Telegram Bot** | Notificaciones en tiempo real | Todos |
| **AbuseIPDB API** | Threat intelligence sobre IPs origen | Alerta Entrante |
| **Agente de bloqueo** (`localhost:8765/block`) | Bloqueo efectivo de IPs en infraestructura | Alerta Entrante |
| **SMTP / Gmail** | Reportes y notificaciones por email | Alerta Entrante, Reporte Diario |
