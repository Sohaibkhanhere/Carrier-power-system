@echo off
title Carrier Power System - Starting...
echo ============================================
echo    Carrier Power System - Starting...
echo ============================================
echo.

:: Kill old processes
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak >nul

echo [1/2] Starting Backend (port 8000)...
start "Backend - Carrier Power System" powershell -NoExit -Command "cd '%~dp0backend'; & '.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --port 8000"
timeout /t 6 /nobreak >nul

echo [2/2] Starting Frontend (port 5173)...
start "Frontend - Carrier Power System" powershell -NoExit -Command "cd '%~dp0frontend'; npm run dev"
timeout /t 4 /nobreak >nul

echo.
echo ============================================
echo    Both servers are starting!
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:5173
echo ============================================
echo.
echo Opening browser in 3 seconds...
timeout /t 3 /nobreak >nul
start http://localhost:5173
