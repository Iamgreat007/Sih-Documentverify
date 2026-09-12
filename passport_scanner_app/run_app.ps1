Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Starting AI Passport & MRZ Scanner Application" -ForegroundColor Green
Write-Host ""
Write-Host "Local Links:" -ForegroundColor Yellow
Write-Host "  - http://localhost:8000" -ForegroundColor White
Write-Host "  - http://127.0.0.1:8000" -ForegroundColor White
Write-Host "===================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

& .venv\Scripts\python -m uvicorn main:app --app-dir passport_scanner_app --host 0.0.0.0 --port 8000 --reload
