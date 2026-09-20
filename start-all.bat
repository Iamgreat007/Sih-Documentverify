@echo off
echo =======================================================
echo          Starting SecureScan AI System
echo =======================================================

echo.
echo [1/3] Starting Java Face Recognition Service...
start "Java Face Recognition Service (Port 8080)" cmd /k "cd /d "%~dp0" && PowerShell -ExecutionPolicy Bypass -File "%~dp0scripts\run-with-local-jdk.ps1""

echo.
echo [2/3] Starting Django Backend API...
start "Django Backend API (Port 8000)" cmd /k "cd /d "%~dp0" && "%~dp0venv-django\Scripts\activate.bat" && cd "%~dp0django_backend" && python manage.py runserver 0.0.0.0:8000"

echo.
echo [3/3] Starting Next.js Frontend...
start "Next.js Frontend (Port 3000)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo =======================================================
echo All services are starting up!
echo =======================================================
pause
