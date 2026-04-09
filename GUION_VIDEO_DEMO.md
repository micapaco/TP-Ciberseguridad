# 🎬 Guion — Video Demostración SIEM/SOAR

> **Duración estimada:** 10–12 minutos  
> **Participantes:**  
> - **Compañera:** Introducción + Arquitectura + Flujo n8n (Escenas 1–3)  
> - **Mika:** Pruebas de ramas + Telegram + Dashboards (Escenas 4–8)

---

# 👩‍💻 PARTE 1 — COMPAÑERA

---

## ESCENA 1 — Introducción al proyecto (0:00 – 1:00)

### 🖥️ Qué mostrar en pantalla
- El `README.md` abierto o el diagrama de arquitectura del proyecto.

### 🎙️ Qué decir

> *"Buenas, en este video vamos a mostrar una demo funcional de nuestro SIEM básico orquestado con n8n.*  
> *El sistema tiene 8 servicios Docker: PostgreSQL, Elasticsearch, Logstash, syslog-ng, Kibana, Grafana, n8n y un dashboard en Streamlit.*  
> *Vamos a probar cada rama del workflow de n8n para verificar que todo funciona correctamente: desde alertas que se descartan, hasta la creación de incidentes y el bloqueo automático de IPs."*

---

## ESCENA 2 — Infraestructura Docker (1:00 – 1:45)

### 🖥️ Qué mostrar en pantalla
- Terminal con los contenedores ya levantados

### ⌨️ Comando

```powershell
docker compose ps
```

### 🎙️ Qué decir

> *"El sistema corre todo en contenedores Docker. Con un solo comando se levanta toda la infraestructura. Acá vemos los 8 servicios corriendo: PostgreSQL, Elasticsearch, Kibana, Logstash, syslog-ng, n8n, Grafana y el dashboard Streamlit."*

---

## ESCENA 3 — Explicar los workflows de n8n (1:45 – 4:00)

### 🖥️ Qué mostrar en pantalla
- Navegador en `http://localhost:5678`

---

### 3A — Workflow principal: "SIEM - Alerta Entrante" (1:45 – 3:30)

> *"Este es el corazón del sistema. Lo recorro de izquierda a derecha."*

**Recorrer los nodos señalándolos:**

#### 🟢 Entrada y enriquecimiento

1. **Webhook** → **Enriquecer Datos**
   > *"Todo empieza con el Webhook que recibe alertas por HTTP POST. El nodo Enriquecer Datos clasifica el tipo de incidente y asigna una prioridad: P1 urgente, P2 alta, o P3 normal."*

2. **Filtrar por Severidad** (Switch con 3 salidas)
   > *"Después pasa por un filtro de severidad con tres caminos: si es CRITICAL o HIGH continúa el análisis completo. Si es LOW, solo se guarda en la DB y termina."*

#### 🔵 Verificación de reincidencia

3. **Verificar Incidente Activo** → **¿Incidente ya existe?**
   > *"Antes de seguir, el sistema revisa si esta IP ya tiene un incidente abierto. Si ya existe, envía una Alerta de Reincidencia por Telegram sin duplicar. Si no, continúa."*

#### 🟡 Análisis en paralelo

4. **Insertar Alerta** → Se abren 2 ramas en paralelo:

   **Rama superior — Password Spraying:**
   > *"Arriba se cuentan cuántas IPs distintas atacaron al mismo usuario en 5 minutos. Si son 5 o más, se detecta Password Spraying y se crea un incidente especial."*

   **Rama principal — Risk Score:**
   > *"La rama principal consulta AbuseIPDB para la reputación de la IP, cuenta alertas acumuladas, revisa la reputación interna de los últimos 7 días, y calcula un Risk Score de 0 a 100."*

5. **Detectar Ataque** (If — risk_level = critical?)
   > *"Si el Risk Score llega a 70 o más, se considera critical y se crea un incidente. Si no, se envía una alerta normal por Telegram y email."*

#### 🔴 Respuesta automática

6. **Crear Incidente** → **Bloquear IP** → **Enforce Block** → **Actualizar Enforcement** → **Notificar Bloqueo**
   > *"Si es critical: se crea un incidente, se bloquea la IP en la blacklist, se aplica el bloqueo en el firewall, y se notifica todo por Telegram y email."*

> *"Ahora Mika va a probar cada una de estas ramas en vivo para verificar que funcionan correctamente."*

---

### 3B — "Reporte Diario" y "Error Handler" (3:30 – 4:00)

> *"Además del workflow principal, tenemos otros dos. El Reporte Diario se ejecuta automáticamente, consulta métricas y top IPs en PostgreSQL, y envía un resumen por Telegram y email. Y el Error Handler captura cualquier error del sistema, avisa por Telegram y lo guarda en la base de datos."*

---

# 👨‍💻 PARTE 2 — MIKA

> **Concepto:** Probar cada rama del workflow una por una, verificando el resultado esperado en n8n y Telegram.

---

## ESCENA 4 — Preparar e iniciar el simulador (4:00 – 4:30)

### 🖥️ Layout de pantalla
- **Izquierda:** Terminal PowerShell
- **Derecha:** Telegram abierto

### ⌨️ Comando

```powershell
cd C:\TP-Final
python detector/attack_simulator.py
```

### 🎙️ Qué decir

> *"Ahora voy a correr el simulador de ataques en modo interactivo. Acá tenemos un menú con distintas opciones. Abajo hay pruebas específicas para cada rama del workflow, que es lo que vamos a usar."*
>
> *"En vez de mandar todos los ataques juntos con el modo automático, vamos a probar rama por rama. ¿Por qué? Porque así podemos verificar que cada camino del workflow funciona correctamente: que lo que tiene que descartarse se descarta, que lo que tiene que generar incidente lo genera, y que lo que tiene que bloquearse se bloquea. Es una forma más ordenada de validar el sistema."*
>
> *"Empezamos por la Rama 2 y no por la 1, porque queremos verificar primero que el sistema descarta correctamente lo que tiene que descartar, y después ir subiendo de severidad hasta llegar a los incidentes más graves."*

*(Mostrar el menú brevemente)*

---

## ESCENA 5 — Prueba de ramas (4:30 – 8:30)

---

### 🔵 RAMA 2 — Alerta LOW, solo se registra (4:30 – 5:15)

### ⌨️ En el menú, escribir: `r2`

### 🎙️ Qué decir ANTES

> *"Empezamos con la Rama 2: enviamos una alerta con severidad LOW. El sistema la recibe, pasa por el filtro de severidad, y como es low va al nodo Registrar Playbook Low que solo la guarda en la base de datos. NO debe llegar ninguna notificación a Telegram ni generar incidente."*

### ✅ Qué verificar en pantalla
- Terminal muestra `OK` (el webhook respondió 200)
- **Telegram: NO debe llegar ningún mensaje nuevo**

### 🎙️ Qué decir DESPUÉS

> *"Vemos que el webhook respondió OK, pero si miramos Telegram... no llegó nada. Perfecto, eso es exactamente lo esperado. Las alertas low se guardan en la base de datos pero no generan notificación. El filtro de severidad funciona correctamente."*

---

### 🟡 RAMA 1 — Alerta HIGH, solo notificación (5:15 – 6:00)

### ⌨️ En el menú, escribir: `r1`

### 🎙️ Qué decir ANTES

> *"Ahora probamos la Rama 1: una alerta con severidad HIGH. Esta sí debería pasar el filtro, recorrer el análisis completo con AbuseIPDB y Risk Score, y generar una notificación en Telegram y un email. Pero como es HIGH y no critical, NO debería crear un incidente."*

### ✅ Qué verificar en pantalla
- Terminal muestra `OK`
- **Telegram: SÍ llega un mensaje** con icono ⚠️ ALERTA ALTA SIEM
- El mensaje muestra: severidad, regla, IP, usuario, datos de AbuseIPDB, Risk Score

### 🎙️ Qué decir DESPUÉS

> *"Acá sí llegó el mensaje. Vemos que dice 'Alerta Alta SIEM', muestra la IP, el usuario, y abajo la información de Threat Intelligence de AbuseIPDB: el país, el score de abuso, los reportes. También el Risk Score calculado con sus factores. Pero no creó un incidente porque el riesgo no llegó a critical."*

---

### 🔴 RAMA 3 — Nuevo incidente + Bloqueo de IP (6:00 – 7:15)

### ⌨️ En el menú, escribir: `r3`

### 🎙️ Qué decir ANTES

> *"Esta es la prueba más importante. Rama 3: vamos a enviar 6 alertas CRITICAL desde la misma IP, 45.33.32.156. El sistema debería acumular esas alertas, calcular un Risk Score alto, crear un incidente, bloquear la IP en la blacklist, y mandarnos notificaciones de todo: la alerta, el incidente, y el bloqueo."*

### ✅ Qué verificar en pantalla
- Terminal muestra 6 alertas enviadas con `OK`
- **Telegram: varios mensajes deben llegar:**
  - 🚨 Alertas críticas con Risk Score
  - 🚨 INCIDENTE DE SEGURIDAD DETECTADO (con ID del incidente)
  - 🛡️ ACCIÓN AUTOMÁTICA — IP BLOQUEADA (con duración 24hs)

### 🎙️ Qué decir DESPUÉS

> *"Perfecto. Vemos en Telegram que llegaron las alertas, y acá lo más importante: se creó un incidente de seguridad automáticamente."*
>
> *(Señalar el mensaje de incidente)* *"Este mensaje muestra el ID del incidente, los intentos detectados, la IP atacante, y toda la info de AbuseIPDB."*
>
> *(Señalar el mensaje de bloqueo)* *"Y acá abajo vemos que el SOAR tomó acción: la IP fue bloqueada automáticamente por 24 horas. Todo sin intervención humana."*

---

### 🟡 RAMA 4 — IP Reincidente (7:15 – 7:50)

### ⌨️ En el menú, escribir: `r4`

### 🎙️ Qué decir ANTES

> *"Ahora la Rama 4. Enviamos otra alerta desde la misma IP 45.33.32.156 que ya tiene un incidente abierto de la prueba anterior. El sistema debería detectar que es una IP reincidente y avisar por Telegram, pero SIN crear un nuevo incidente duplicado."*

### ✅ Qué verificar en pantalla
- Terminal muestra `OK`
- **Telegram: llega un mensaje de** 🔄 IP REINCIDENTE DETECTADA
- **NO llega** un nuevo mensaje de "Incidente de seguridad detectado"

### 🎙️ Qué decir DESPUÉS

> *"Ahí está: 'IP Reincidente Detectada'. El sistema reconoció que esa IP ya tiene un incidente abierto y solo mandó una alerta de reincidencia, sin duplicar el incidente. Esto es clave para no generar ruido innecesario."*

---

### 🎯 RAMA 5 — Password Spraying (7:50 – 8:30)

### ⌨️ En el menú, escribir: `r5`

### 🎙️ Qué decir ANTES

> *"La última rama: Password Spraying. Esto simula un ataque distribuido: 6 IPs diferentes atacando al mismo usuario 'admin' en los últimos 5 minutos. El sistema debería detectar el patrón, crear un incidente de tipo password spraying, y avisarnos."*

### ✅ Qué verificar en pantalla
- Terminal muestra 6 alertas enviadas desde IPs diferentes, todas `OK`
- **Telegram: llega un mensaje de** 🎯 PASSWORD SPRAYING DETECTADO
  - Muestra usuario objetivo, cantidad de IPs distintas, severidad critical

### 🎙️ Qué decir DESPUÉS

> *"Ahí está el mensaje: 'Password Spraying Detectado'. Muestra que 6 IPs distintas atacaron al usuario admin en 5 minutos. El sistema creó un incidente especial de tipo password spraying. Esta es una detección avanzada que los SIEMs básicos no hacen."*

---

### ⌨️ Salir del simulador: escribir `0`

---

## ESCENA 6 — Resumen en Telegram (8:30 – 9:00)

### 🖥️ Qué mostrar
- Telegram maximizado, scrollear por los mensajes

### 🎙️ Qué decir

> *"Si recorremos todos los mensajes de Telegram, vemos los 5 tipos de respuesta que tiene el sistema:"*
>
> 1. *"Alertas low que se registran sin notificación — la Rama 2."*
> 2. *"Alertas informativas con Threat Intelligence — la Rama 1 con high."*  
> 3. *"Incidentes con bloqueo automático — la Rama 3 con critical."*
> 4. *"Detección de IPs reincidentes — la Rama 4."*
> 5. *"Detección de ataques distribuidos como Password Spraying — la Rama 5."*
>
> *"Cada mensaje tiene toda la información que un analista necesita para actuar."*

---

## ESCENA 7 — Dashboards (9:00 – 11:00)

### 🎙️ Introducción — ¿Por qué dos herramientas de visualización?

> *"Para la visualización usamos dos herramientas: Grafana y un dashboard propio en Streamlit. ¿Por qué dos? Porque cumplen funciones distintas."*
>
> *"Grafana es el estándar de la industria para monitoreo de infraestructura. Se conecta directo a PostgreSQL con queries SQL y tiene 4 dashboards especializados: uno para el SOC, otro para el pipeline de datos, otro para la salud de la plataforma, y otro para las operaciones SOAR. Cada uno con métricas específicas que se actualizan en tiempo real."*
>
> *"El dashboard de Streamlit, Chemical X, lo desarrollamos nosotras en Python. La ventaja es que podemos hacer cosas que Grafana no hace fácilmente: un mapa geográfico interactivo con los países de los ataques, tarjetas KPI personalizadas, tablas con badges de colores, y una vista unificada de todo el sistema para un analista SOC. Además, al ser código Python, es completamente personalizable."*
>
> *"En resumen: Grafana para métricas operativas y drilling, Streamlit para la vista ejecutiva del analista."*

---

### 7A — Grafana: 4 dashboards (9:00 – 10:00)

### 🖥️ Qué mostrar
- Navegador en `http://localhost:3000` → login `admin / admin123`
- Ir a **Dashboards** → Carpeta **SIEM**

> *"En Grafana tenemos 4 dashboards. Los recorro rápido."*

**(Abrir cada dashboard, mostrar unos segundos, y pasar al siguiente)**

1. **SIEM Dashboard - Centro de Operaciones:**
   > *"El principal: alertas de las últimas 24h, distribución por severidad, MTTR de 1.74 segundos, las últimas alertas en tabla, y las top IPs sospechosas."*

2. **SIEM Data Pipeline:**
   > *"El pipeline de datos: 6 KPIs con tarjetas de colores, volumen de alertas por hora, top reglas disparadas, tendencia de alertas fallidas, y los ataques por país con datos de AbuseIPDB."*

3. **Salud de la plataforma:**
   > *"La salud de la infraestructura: conexiones a PostgreSQL, tamaño de la base, cache hit ratio del 99%, deadlocks en cero, y los indicadores de actividad del detector y de n8n."*

4. **Operaciones SOAR / n8n:**
   > *"Y el SOAR: 14 playbooks ejecutados, tasa de éxito del 100%, cero fallidos, las ejecuciones en el tiempo con sus resultados, y abajo las 2 IPs bloqueadas automáticamente con su estado ACTIVO."*

---

### 7B — Dashboard Streamlit "Chemical X" (10:00 – 11:00)

### 🖥️ Qué mostrar
- Navegador en `http://localhost:8501`

### 🎙️ Qué decir

> *"Y este es Chemical X, nuestro dashboard propio hecho en Python con Streamlit y Plotly."*

Ir recorriendo las secciones:

- **KPIs superiores:**
  > *"Arriba tenemos 7 indicadores clave en tarjetas: alertas de la última hora, alertas de 24 horas, incidentes abiertos, MTTR, tasa de automatización, alertas fallidas, e IPs bloqueadas por el SOAR. Los colores cambian según el estado: verde si está bien, rojo si hay algo crítico."*

- **Análisis de alertas (timeline + donut):**
  > *"Acá vemos las alertas por hora apiladas por severidad, y la distribución en un gráfico de torta."*

- **Mapa geográfico interactivo:**
  > *"Este mapa es algo que Grafana no puede hacer tan fácil. Muestra de qué países vienen los ataques con un choropleth interactivo. A la derecha, el ranking de países. Todo con datos de AbuseIPDB."*

- **Top IPs + Playbooks:**
  > *"Las IPs más sospechosas y las ejecuciones de los playbooks automáticos con el detalle de éxito o fallo."*

- **Reglas e Incidentes:**
  > *"Las reglas más disparadas en las últimas 24 horas, y los incidentes abiertos con su severidad, IP, usuario e intentos."*

- **IPs bloqueadas (SOAR):**
  > *"La sección del SOAR muestra las IPs bloqueadas con su razón, cuándo se bloqueó, cuándo vence, y si el bloqueo fue aplicado en el firewall o solo registrado lógicamente."*

- **Últimas alertas:**
  > *"Y al final, la tabla con las 20 últimas alertas en tiempo real con badges de colores."*

> *"Todo se refresca automáticamente cada 30 segundos. Y como es código Python, podemos agregar cualquier visualización que necesitemos."*

---

## CIERRE (después de Chemical X)

### 🎙️ Qué decir

> *"Y con esto cerramos la demo. Probamos las 5 ramas del workflow y todas funcionaron correctamente: alertas low que se registran sin ruido, alertas high con Threat Intelligence, incidentes con bloqueo automático, detección de reincidencia, y Password Spraying. Todo automatizado, open source, y corriendo en Docker. Gracias."*

---

## 📋 Checklist pre-grabación

### Para la compañera (Parte 1)
- [ ] Docker corriendo, todos los contenedores Up
- [ ] n8n en `http://localhost:5678` con los 3 workflows activados
- [ ] Practicar el recorrido de nodos del workflow principal

### Para Mika (Parte 2)
- [ ] `pip install requests` ya instalado
- [ ] Terminal lista en `C:\TP-Final`
- [ ] Telegram abierto y visible
- [ ] **Limpiar DB antes de grabar** (para que los resultados sean limpios):
  ```powershell
  docker exec siem_postgres psql -U siem -d siem -c "DELETE FROM playbook_runs; DELETE FROM ip_blacklist; DELETE FROM incidents; DELETE FROM alerts;"
  ```
- [ ] Grafana en `http://localhost:3000` (user: `admin`, pass: `admin123`)
- [ ] Streamlit en `http://localhost:8501` (Chemical X)
- [ ] Grabador de pantalla listo, resolución 1920x1080

---

## 🎯 Tips para Mika

1. **Pantalla dividida:** Terminal izquierda, Telegram derecha. Así las notificaciones se ven llegando en vivo.
2. **Pausá entre ramas** — dejá 2-3 segundos para que Telegram reciba los mensajes antes de comentar.
3. **Señalá con el mouse** las partes importantes de cada mensaje de Telegram.
4. **Orden de ramas:** R2 → R1 → R3 → R4 → R5. Este orden va de la más simple a la más compleja, y R4 necesita que R3 se haya ejecutado antes.
5. **Si algo falla**, explicá qué pasó — eso demuestra dominio del sistema.
