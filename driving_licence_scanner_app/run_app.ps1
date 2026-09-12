# PowerShell Launcher for AI Driving Licence Screening App
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Starting AI Driving Licence Screening App..." -ForegroundColor Green
Write-Host "SIH 26188 Motor Vehicle & Driver ID Extractor" -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Cyan

$WorkspaceRoot = Split-Path -Parent $PSScriptRoot
Set-Location $WorkspaceRoot

$VenvPython = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    & $VenvPython -m uvicorn main:app --app-dir driving_licence_scanner_app --host 127.0.0.1 --port 8001 --reload
} else {
    python -m uvicorn main:app --app-dir driving_licence_scanner_app --host 127.0.0.1 --port 8001 --reload
}
