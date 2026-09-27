Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         Starting SecureScan AI System" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path

# Write-Host "[1/3] Starting Java Face Recognition Service (Port 8080)..." -ForegroundColor Yellow
# Start-Process "cmd.exe" -ArgumentList "/k cd /d `"$workspace\facerecognition`" && .\mvnw spring-boot:run" -WindowStyle Normal

Write-Host "[2/3] Starting Django Backend API (Port 8000)..." -ForegroundColor Yellow
Start-Process "cmd.exe" -ArgumentList "/k cd /d `"$workspace`" && if exist venv-django\Scripts\activate.bat (call venv-django\Scripts\activate.bat) && cd django_backend && python manage.py migrate && python manage.py runserver 0.0.0.0:8000" -WindowStyle Normal

Write-Host "[3/3] Starting Next.js Frontend (Port 3000)..." -ForegroundColor Yellow
Start-Process "cmd.exe" -ArgumentList "/k cd /d `"$workspace\frontend`" && if not exist node_modules (npm install) && npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "All services are starting up in separate windows!" -ForegroundColor Green
Write-Host ""
Write-Host "TO VIEW ON MOBILE PHONE (Recommended):" -ForegroundColor White
Write-Host "1. Run .\start-pinggy-tunnel.bat"
Write-Host "2. Open the https://... URL shown on your phone browser."
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Pause
