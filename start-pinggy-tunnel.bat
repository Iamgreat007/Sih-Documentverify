@echo off
title SecureScan AI - Mobile Pinggy Tunnel
echo =======================================================
echo        SecureScan AI - Mobile Pinggy Tunnel
echo =======================================================
echo.
echo Forwarding port 3000 to public HTTPS tunnel...
echo Open the https://... URL displayed below on your phone!
echo (All backend APIs on port 8000 are automatically proxied)
echo.
ssh -p 443 -R0:127.0.0.1:3000 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 a.pinggy.io
pause
