Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         Starting SecureScan AI System" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Starting Java Face Recognition Service..." -ForegroundColor Yellow
Start-Process "cmd.exe" -ArgumentList "/c cd facerecognition && .\mvnw spring-boot:run" -WindowStyle Normal

Write-Host "[2/3] Starting Django Backend API..." -ForegroundColor Yellow
Start-Process "cmd.exe" -ArgumentList "/c cd django_backend && ..\venv-django\Scripts\activate && python manage.py runserver 0.0.0.0:8000" -WindowStyle Normal
Write-Host "[2/3] Checking and Starting Django Backend API..." -ForegroundColor Yellow
Start-Process "cmd.exe" -ArgumentList "/c if not exist venv-django (echo Creating virtual environment... && python -m venv venv-django && .\venv-django\Scripts\activate && pip install -r requirements.txt && cd django_backend && python manage.py migrate && python manage.py runserver 0.0.0.0:8000) else (.\venv-django\Scripts\activate && cd django_backend && python manage.py runserver 0.0.0.0:8000)" -WindowStyle Normal

Write-Host "[3/3] Starting Next.js Frontend..." -ForegroundColor Yellow
Start-Process "cmd.exe" -ArgumentList "/c cd frontend && npm run dev" -WindowStyle Normal
Write-Host "[3/3] Checking and Starting Next.js Frontend..." -ForegroundColor Yellow
Start-Process "cmd.exe" -ArgumentList "/c cd frontend && if not exist node_modules (echo Installing NPM dependencies... && npm install && npm run dev) else (npm run dev)" -WindowStyle Normal

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "All services are starting up in separate windows!" -ForegroundColor Green
Write-Host ""
Write-Host "TO VIEW ON MOBILE PHONE:" -ForegroundColor White
Write-Host "1. Ensure your phone and PC are on the same Wi-Fi network."
Write-Host "2. Open Command Prompt, type 'ipconfig' and find your IPv4 Address."
Write-Host "3. On your phone browser, go to http://YOUR_IPV4_ADDRESS:3000"
Write-Host ""
Write-Host "Have a great time!" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Green
Pause

