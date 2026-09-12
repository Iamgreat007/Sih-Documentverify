@echo off
echo ===================================================
echo Starting AI Driving Licence Screening App...
echo SIH 26188 Motor Vehicle & Driver ID Extractor
echo ===================================================

cd /d "%~dp0\.."
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m uvicorn main:app --app-dir driving_licence_scanner_app --host 127.0.0.1 --port 8001 --reload
) else (
    python -m uvicorn main:app --app-dir driving_licence_scanner_app --host 127.0.0.1 --port 8001 --reload
)
pause
