@echo off
echo =======================================================
echo          Starting SecureScan Public Tunnel
echo =======================================================
echo.
echo This will generate a public, secure HTTPS link so you can 
echo use your phone's live camera without the browser blocking it!
echo.
echo Please wait a few seconds for the link to appear...
echo.
call npx localtunnel --port 3000
pause

