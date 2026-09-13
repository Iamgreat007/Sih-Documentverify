@echo off
echo =======================================================
echo          Starting SecureScan AI System
echo =======================================================

echo.
echo [1/3] Starting Java Face Recognition Service...
start "Java Face Recognition Service (Port 8080)" cmd /k "cd facerecognition && .\mvnw spring-boot:run"

echo.
echo [2/3] Starting Django Backend...
start "Django Backend API (Port 8000)" cmd /k "cd django_backend && ..\venv-django\Scripts\activate && python manage.py runserver 0.0.0.0:8000"
echo [2/3] Checking and Starting Django Backend API...
start "Django Backend API (Port 8000)" cmd /k "if not exist venv-django (echo Creating virtual environment... && python -m venv venv-django && .\venv-django\Scripts\activate && pip install -r requirements.txt && cd django_backend && python manage.py migrate && python manage.py runserver 0.0.0.0:8000) else (.\venv-django\Scripts\activate && cd django_backend && python manage.py runserver 0.0.0.0:8000)"

echo.
echo [3/3] Starting Next.js Frontend...
start "Next.js Frontend (Port 3000)" cmd /k "cd frontend && npm run dev"
echo [3/3] Checking and Starting Next.js Frontend...
start "Next.js Frontend (Port 3000)" cmd /k "cd frontend && if not exist node_modules (echo Installing NPM dependencies... && npm install && npm run dev) else (npm run dev)"

echo.
echo =======================================================
echo All services are starting up in separate windows!
echo.
echo TO VIEW ON MOBILE PHONE:
echo 1. Ensure your phone and PC are on the same Wi-Fi network.
echo 2. Open Command Prompt, type 'ipconfig' and find your IPv4 Address.
echo 3. On your phone browser, go to http://YOUR_IPV4_ADDRESS:3000
echo.
echo Have a great time!
echo =======================================================
pause

