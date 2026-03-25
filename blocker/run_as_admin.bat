@echo off
echo ============================================
echo   BLOCKER API — SOAR Firewall Enforcement
echo   Requiere privilegios de Administrador
echo ============================================
echo.

:: Verificar si corre como admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Este script debe ejecutarse como Administrador.
    echo Hacé clic derecho en el archivo y elegí "Ejecutar como administrador".
    pause
    exit /b 1
)

echo [OK] Ejecutando como Administrador
echo.

:: Instalar dependencias si no están
pip show flask >nul 2>&1
if %errorLevel% neq 0 (
    echo Instalando dependencias...
    pip install -r requirements.txt
)

echo Iniciando Blocker API en http://localhost:8765
echo (n8n la llama como http://host.docker.internal:8765)
echo.
python blocker_api.py
pause
