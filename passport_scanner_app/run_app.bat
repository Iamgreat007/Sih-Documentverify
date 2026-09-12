@echo off
echo ===================================================
echo Starting AI Passport & MRZ Scanner Application
echo.
echo Local Links:
echo   - http://localhost:8000
echo   - http://127.0.0.1:8000
echo   - http://0.0.0.0:8000
echo ===================================================
cd /d "%~dp0\.."
.venv\Scripts\python -m uvicorn main:app --app-dir passport_scanner_app --host 0.0.0.0 --port 8000 --reload
pause
