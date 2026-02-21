@echo off
title Crevia Analytics - Shutdown
color 0C

echo ============================================
echo    Crevia Analytics - Stopping All Services
echo ============================================
echo.

echo Stopping FastAPI (port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Stopping Next.js (port 3000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Stopping Engine (python main.py)...
taskkill /F /FI "WINDOWTITLE eq Crevia Engine*" >nul 2>&1

echo.
echo All services stopped.
pause
