@echo off
echo =======================================================
echo          Installing Dependencies
echo =======================================================

echo [1/3] Checking Java local JDK...
if not exist "%~dp0jdk" (
    echo Installing Java local JDK...
    PowerShell -ExecutionPolicy Bypass -File "%~dp0scripts\install-jdk.ps1"
) else (
    echo JDK already installed. Skipping.
)

echo.
echo [2/3] Setting up Python Virtual Environment and Backend...
cd "%~dp0"
if not exist "%~dp0venv-django\Scripts\python.exe" (
    echo Creating Python virtual environment...
    python -m venv venv-django
) else (
    echo Python virtual environment already exists.
)
call "%~dp0venv-django\Scripts\activate.bat"
pip install -r requirements.txt
cd "%~dp0django_backend"
python manage.py migrate
cd "%~dp0"

echo.
echo [3/3] Installing Frontend Dependencies (Clean Install)...
cd "%~dp0frontend"
echo Removing old node_modules...
rmdir /s /q node_modules 2>nul
rmdir /s /q .next 2>nul
call npm install
cd "%~dp0"

echo.
echo =======================================================
echo All dependencies installed! You can now run start-all.bat
echo =======================================================
pause

