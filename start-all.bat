@echo off
title Starting SecureScan AI System
echo =======================================================
echo          Starting SecureScan AI System
echo =======================================================

echo.
REM echo [1/3] Starting Java Face Recognition Service (Port 8080)...
REM start "Java Face Recognition Service (Port 8080)" cmd /k "cd /d "%~dp0facerecognition" && .\mvnw spring-boot:run"

echo.
echo [2/3] Starting Django Backend API (Port 8000)...
start "Django Backend API (Port 8000)" cmd /k "cd /d "%~dp0" && if exist venv-django\Scripts\activate.bat (call venv-django\Scripts\activate.bat) && cd django_backend && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"

echo.
echo [3/3] Starting Next.js Frontend (Port 3000)...
start "Next.js Frontend (Port 3000)" cmd /k "cd /d "%~dp0frontend" && if not exist node_modules (echo Installing NPM dependencies... && npm install) && npm run dev"

echo.
echo =======================================================
echo All services are starting up!
echo.
echo TO VIEW ON MOBILE PHONE (Recommended):
echo 1. Double-click 'start-pinggy-tunnel.bat'
echo 2. Open the https://... URL shown in that window on your phone!
echo.
echo (Or if on same Wi-Fi: http://YOUR_PC_IP:3000)
echo =======================================================
pause
