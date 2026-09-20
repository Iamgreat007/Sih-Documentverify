Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         Starting SecureScan AI System" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Starting Java Face Recognition Service..." -ForegroundColor Yellow
Start-Process "cmd.exe" -ArgumentList "/c cd /d `"$PSScriptRoot`" && PowerShell -ExecutionPolicy Bypass -File `"$PSScriptRoot\scripts\run-with-local-jdk.ps1`"" -WindowStyle Normal

Write-Host "[2/3] Starting Django Backend API..." -ForegroundColor Yellow
Start-Process "cmd.exe" -ArgumentList "/c cd /d `"$PSScriptRoot`" && `"$PSScriptRoot\venv-django\Scripts\activate.bat`" && cd `"$PSScriptRoot\django_backend`" && python manage.py runserver 0.0.0.0:8000" -WindowStyle Normal

Write-Host ""
Write-Host "[3/3] Starting Next.js Frontend..." -ForegroundColor Yellow
Start-Process "cmd.exe" -ArgumentList "/c cd /d `"$PSScriptRoot\frontend`" && npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "All services are starting up!" -ForegroundColor Green
Pause
