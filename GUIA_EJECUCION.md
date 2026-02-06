# 🚀 Guía de Ejecución Paso a Paso - SIEM

**Esta guía está diseñada para alguien que nunca usó este proyecto.**  
Seguí cada paso en orden y no te saltees ninguno.

---

## 📋 Índice

1. [Antes de empezar - Requisitos](#1-antes-de-empezar---requisitos)
2. [Preparar el entorno](#2-preparar-el-entorno)
3. [Iniciar el sistema](#3-iniciar-el-sistema)
4. [Verificar que todo funciona](#4-verificar-que-todo-funciona)
5. [Probar las funcionalidades](#5-probar-las-funcionalidades)
6. [Detener el sistema](#6-detener-el-sistema)
7. [Solución de problemas](#7-solución-de-problemas)

---

## 1. Antes de empezar - Requisitos

### ¿Qué necesitás tener instalado?

| Programa | ¿Para qué sirve? | ¿Cómo verificar si lo tenés? |
|----------|-----------------|------------------------------|
| **Docker Desktop** | Ejecuta los 9 servicios del SIEM en contenedores | Abrir Docker Desktop y ver que diga "Running" |
| **Python 3.8+** | Ejecuta los scripts de detección | En terminal: `python --version` |
| **Navegador** | Para ver Grafana, Kibana, n8n | Chrome, Firefox, Edge, etc. |

### ¿Cuánta RAM necesita?

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| RAM | 8 GB | 16 GB |
| Disco | 10 GB libres | 20 GB |

> ⚠️ **IMPORTANTE**: Docker Desktop debe estar abierto y corriendo ANTES de ejecutar cualquier comando.

---

## 2. Preparar el entorno

### Paso 2.1: Abrir Docker Desktop

1. Buscá "Docker Desktop" en el menú inicio de Windows
2. Hacé clic para abrirlo
3. Esperá hasta que diga **"Docker is running"** (puede tardar 1-2 minutos)

**¿Por qué?** Docker es el programa que va a ejecutar todos los servicios. Sin él corriendo, nada funciona.

---

### Paso 2.2: Abrir PowerShell

1. Presioná `Windows + X`
2. Seleccioná **"Windows PowerShell"** o **"Terminal"**

**¿Por qué PowerShell y no CMD?** PowerShell tiene comandos más potentes que vamos a necesitar.

---

### Paso 2.3: Ir a la carpeta del proyecto

Escribí este comando y presioná Enter:

```powershell
cd C:\TP-Final
```

**¿Qué pasa si no funciona?**  
Si dice "no se encuentra la ruta", la carpeta está en otro lugar. Buscá dónde descargaste el proyecto.

---

## 3. Iniciar el sistema

### Paso 3.1: Levantar todos los servicios

Escribí este comando y presioná Enter:

```powershell
docker-compose up -d
```

**¿Qué hace este comando?**
- `docker-compose`: Programa que maneja múltiples contenedores
- `up`: Crear e iniciar los contenedores
- `-d`: Ejecutar en segundo plano (detached) para que no bloquee la terminal

**¿Por qué este comando primero?**  
Porque inicia los 9 servicios que componen el SIEM. Sin esto, no hay nada corriendo.

**Salida esperada (primera vez):**
```
[+] Running 9/9
 ✔ Container siem_postgres        Started
 ✔ Container siem_elasticsearch   Started
 ✔ Container siem_kibana          Started
 ✔ Container siem_logstash        Started
 ✔ Container siem_syslog          Started
 ✔ Container siem_n8n             Started
 ✔ Container siem_grafana         Started
 ✔ Container siem_wazuh_manager   Started
 ✔ Container siem_wazuh_dashboard Started
```

**¿Cuánto tarda?**
- Primera vez: 5-15 minutos (descarga imágenes de ~5GB)
- Veces siguientes: 10-30 segundos

---

### Paso 3.2: Esperar que los servicios inicien completamente

Los servicios tardan en arrancar internamente. Esperá **2-3 minutos** antes de continuar.

**¿Por qué esperar?**  
Aunque Docker dice "Started", los programas dentro de los contenedores todavía están iniciando. Elasticsearch especialmente tarda ~2 minutos.

---

### Paso 3.3: Instalar dependencia Python (solo primera vez)

```powershell
pip install requests
```

**¿Qué hace?**  
Instala la librería `requests` que los scripts de detección necesitan para comunicarse con otros servicios.

**Salida esperada:**
```
Successfully installed requests-2.31.0
```

---

## 4. Verificar que todo funciona

### Paso 4.1: Ver estado de los contenedores

```powershell
docker-compose ps
```

**¿Qué hace?**  
Muestra el estado de todos los contenedores definidos en el proyecto.

**Salida esperada (todo bien):**
```
NAME                   STATUS
siem_postgres          Up
siem_elasticsearch     Up
siem_kibana            Up
siem_logstash          Up
siem_syslog            Up (healthy)
siem_n8n               Up
siem_grafana           Up
siem_wazuh_manager     Up
siem_wazuh_dashboard   Up
```

**¿Qué hacer si alguno dice "Exited"?**  
Ver los logs del servicio problemático:
```powershell
docker logs nombre_del_contenedor
```

---

### Paso 4.2: Verificar Elasticsearch

```powershell
Invoke-RestMethod -Uri "http://localhost:9200/_cluster/health"
```

**¿Qué hace?**  
Consulta el estado de salud de Elasticsearch (la base de datos de búsqueda).

**Salida esperada:**
```
cluster_name : docker-cluster
status       : yellow   ← "yellow" o "green" está bien
```

**Si dice "red":** Hay un problema. Esperá 1 minuto más y volvé a probar.

---

### Paso 4.3: Verificar PostgreSQL

```powershell
docker exec siem_postgres psql -U siem -d siem -c "SELECT COUNT(*) FROM alerts;"
```

**¿Qué hace?**  
Cuenta cuántas alertas hay en la base de datos PostgreSQL.

**Salida esperada:**
```
 count
-------
   163   ← O cualquier número, lo importante es que responda
```

---

## 5. Probar las funcionalidades

### 5.1 Ver dashboards en Grafana

1. Abrí tu navegador
2. Andá a: **http://localhost:3000**
3. Ingresá las credenciales:
   - Usuario: `admin`
   - Contraseña: `admin123`
4. Buscá "SIEM" en Dashboards

**¿Qué deberías ver?**  
Un dashboard con gráficos de alertas, métricas, IPs sospechosas, etc.

---

### 5.2 Ver logs en Kibana

1. Abrí tu navegador
2. Andá a: **http://localhost:5601**
3. Menú ☰ → Analytics → Discover
4. Si te pide crear "Data View": escribí `siem-events-*`

**¿Qué deberías ver?**  
Una lista de logs con campos como timestamp, message, host, etc.

---

### 5.3 Probar detección SSH Brute-Force

Necesitás **2 terminales de PowerShell abiertas**:

#### Terminal 1 - Iniciar el detector:
```powershell
cd C:\TP-Final
python detector\ssh_bruteforce_detector.py
```

**Dejá esta terminal abierta.** Va a decir:
```
🔍 Detector SSH Brute Force iniciado
📊 Umbral: 5 intentos fallidos
⏱️  Intervalo: 120 segundos
```

#### Terminal 2 - Simular ataque:
```powershell
cd C:\TP-Final

# Enviar 6 intentos de login fallidos (simula ataque)
for ($i = 1; $i -le 6; $i++) {
    $message = "<34>Feb 06 16:00:00 testhost sshd[12345]: Failed password for invalid user admin from 10.0.0.99 port 22 ssh2"
    $udpClient = New-Object System.Net.Sockets.UdpClient
    $bytes = [System.Text.Encoding]::ASCII.GetBytes($message)
    $udpClient.Send($bytes, $bytes.Length, "localhost", 514)
    $udpClient.Close()
    Write-Host "Enviado intento $i"
}
```

**¿Qué pasa después?**  
Esperá ~2 minutos. En Terminal 1 debería aparecer:
```
🚨 ALERTA: SSH Brute Force detectado desde 10.0.0.99 - 6 intentos fallidos
✅ Alerta enviada a n8n para IP 10.0.0.99
```

---

### 5.4 Probar detección de cambios en archivos (Wazuh FIM)

Wazuh monitorea archivos críticos y detecta cuando alguien los crea, modifica o elimina.
Esto es útil para detectar intrusos que modifican configuraciones del sistema.

#### 5.4.1 Crear un archivo de prueba

```powershell
docker exec siem_wazuh_manager sh -c "echo 'datos secretos' > /tmp/test_fim/secreto.txt"
```

**¿Qué hace?**  
Crea un archivo de texto dentro del contenedor Wazuh, en una carpeta monitoreada.

**Esperá 30 segundos** para que Wazuh detecte el cambio.

---

#### 5.4.2 Ver las alertas de Wazuh (desde terminal)

```powershell
docker exec siem_wazuh_manager tail -n 5 /var/ossec/logs/alerts/alerts.json
```

**¿Qué hace?**  
Muestra las últimas 5 alertas generadas por Wazuh.

**Salida esperada (archivo creado):**
```json
{
  "rule": {
    "level": 5,
    "description": "File added to the system."
  },
  "syscheck": {
    "path": "/tmp/test_fim/secreto.txt",
    "event": "added"
  }
}
```

---

#### 5.4.3 Modificar el archivo (genera alerta de nivel 7)

```powershell
docker exec siem_wazuh_manager sh -c "echo 'MODIFICADO!' >> /tmp/test_fim/secreto.txt"
```

Esperá 30 segundos y verificá:

```powershell
docker exec siem_wazuh_manager tail -n 3 /var/ossec/logs/alerts/alerts.json
```

**Salida esperada (archivo modificado):**
```json
{
  "rule": {
    "level": 7,
    "description": "Integrity checksum changed."
  },
  "syscheck": {
    "path": "/tmp/test_fim/secreto.txt",
    "event": "modified",
    "changed_attributes": ["size", "md5", "sha256"]
  }
}
```

**¿Qué significa level 7?**  
Es más crítico que level 5. Wazuh detectó que el contenido del archivo cambió (los hashes MD5/SHA256 son diferentes).

---

#### 5.4.4 Eliminar el archivo (genera alerta crítica)

```powershell
docker exec siem_wazuh_manager rm /tmp/test_fim/secreto.txt
```

Verificar:

```powershell
docker exec siem_wazuh_manager tail -n 3 /var/ossec/logs/alerts/alerts.json
```

**Salida esperada:**
```json
{
  "rule": {
    "description": "File deleted."
  },
  "syscheck": {
    "path": "/tmp/test_fim/secreto.txt",
    "event": "deleted"
  }
}
```

---

#### 5.4.5 Ver actividad de escaneo en tiempo real

```powershell
docker exec siem_wazuh_manager tail -f /var/ossec/logs/ossec.log
```

**¿Qué hace?**  
Muestra los logs de Wazuh en tiempo real. Vas a ver mensajes como:
```
File integrity monitoring scan started.
File integrity monitoring scan ended.
```

**Para salir:** Presioná `Ctrl + C`

---

#### 5.4.6 Resumen de comandos Wazuh

| Comando | ¿Para qué? |
|---------|-----------|
| `docker exec siem_wazuh_manager tail -n 5 /var/ossec/logs/alerts/alerts.json` | Ver últimas 5 alertas |
| `docker exec siem_wazuh_manager tail -f /var/ossec/logs/ossec.log` | Ver logs en tiempo real |
| `docker exec siem_wazuh_manager cat /var/ossec/etc/ossec.conf` | Ver configuración completa |

---

### 5.5 Generar datos históricos (para demostración)

```powershell
cd C:\TP-Final
python detector\generate_historical_data.py
```

**¿Qué hace?**  
Genera 50 alertas aleatorias de diferentes tipos para poblar los gráficos.

**Salida esperada:**
```
🔄 Generando 50 alertas históricas...
✅ [1/50] ssh_bruteforce - high - 10.0.0.1
...
✅ Completado: 50/50 alertas enviadas
```

---

## 6. Detener el sistema

### Cuando termines de usar el proyecto:

```powershell
cd C:\TP-Final
docker-compose down
```

**¿Qué hace?**  
Detiene y elimina todos los contenedores. Los datos se mantienen guardados.

**Salida esperada:**
```
[+] Running 9/9
 ✔ Container siem_wazuh_dashboard  Removed
 ✔ Container siem_wazuh_manager    Removed
 ...
 ✔ Network tp-final_siem-net       Removed
```

### Para volver a iniciar después:

```powershell
cd C:\TP-Final
docker-compose up -d
```

Los datos que generaste antes van a seguir ahí.

---

## 7. Solución de problemas

### Error: "Cannot connect to the Docker daemon"

**Causa:** Docker Desktop no está corriendo.  
**Solución:** Abrí Docker Desktop y esperá a que diga "Running".

---

### Error: "Port already in use"

**Causa:** Otro programa usa el puerto.  
**Solución:** Cerrá el programa que usa el puerto o cambiarlo en `docker-compose.yml`.

---

### Error: Contenedor se reinicia constantemente

**Causa:** Poca memoria RAM.  
**Solución:** 
1. Docker Desktop → Settings → Resources
2. Aumentar Memory a 8GB mínimo
3. Reiniciar Docker Desktop

---

### Los gráficos de Grafana están vacíos

**Causa:** No hay datos.  
**Solución:** Ejecutá `python detector\generate_historical_data.py` para generar datos de prueba.
(si no funciona, ir a conexiones en grafana,luego ver fuentes de datos configuradas,seleccionar siem de elasticsearch y guardar de nuevo)

---

### Kibana dice "No data"

**Causa:** No se creó el Data View.  
**Solución:** 
1. Menú ☰ → Stack Management → Data Views
2. Create data view → Name: `siem-events-*`

---

## 📊 Resumen de URLs y Credenciales

| Servicio | URL | Usuario | Contraseña |
|----------|-----|---------|------------|
| Grafana | http://localhost:3000 | admin | admin123 |
| Kibana | http://localhost:5601 | (sin login) | - |
| n8n | http://localhost:5678 | (chicasuperpoderosas26@gmail.com)Poderosas26 |
| Wazuh | https://localhost:8443 | admin | admin | (no hay dashboards por ahora)

---

## 📊 Resumen de Comandos

| Comando | ¿Para qué? |
|---------|-----------|
| `docker-compose up -d` | Iniciar todo |
| `docker-compose ps` | Ver estado |
| `docker-compose down` | Detener todo |
| `docker logs <nombre>` | Ver logs de un servicio |
| `python detector\ssh_bruteforce_detector.py` | Iniciar detector SSH |
| `python detector\generate_historical_data.py` | Generar datos de prueba |

---

**¿Dudas?** Revisá el README.md principal para explicaciones técnicas más detalladas.
