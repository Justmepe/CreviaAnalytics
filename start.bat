@echo off
title Crevia Analytics - Launcher
color 0A

echo ============================================
echo    Crevia Analytics - Starting All Services
echo ============================================
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

:: Check Node
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install Node.js 18+ and add to PATH.
    pause
    exit /b 1
)

:: Set working directory
cd /d "%~dp0"

echo [1/3] Starting FastAPI backend (port 8000)...
start "Crevia API" cmd /k "cd /d "%~dp0" && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for API to be ready
echo       Waiting for API to be ready...
:wait_api
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/api/health >nul 2>&1
if %errorlevel% neq 0 goto wait_api
echo       API is ready.
echo.

echo [2/3] Starting Next.js frontend (port 3000)...
start "Crevia Web" cmd /k "cd /d "%~dp0web" && npm run dev"

:: Wait for frontend to be ready
echo       Waiting for frontend to be ready...
:wait_web
timeout /t 2 /nobreak >nul
curl -s -o nul http://localhost:3000 >nul 2>&1
if %errorlevel% neq 0 goto wait_web
echo       Frontend is ready.
echo.

echo [3/3] Starting Analysis Engine...
start "Crevia Engine" cmd /k "cd /d "%~dp0" && python main.py"

echo.
echo ============================================
echo    All services started successfully!
echo ============================================
echo.
echo    API:      http://localhost:8000
echo    Frontend: http://localhost:3000
echo    Engine:   Running in background
echo.
echo    Each service runs in its own window.
echo    Close this window or press any key to exit.
echo ============================================
echo.
pause
