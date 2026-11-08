@echo off
echo ========================================================
echo   PayResolve AI — Full-Stack Demo Launcher
echo ========================================================
echo.
echo [1/2] Launching FastAPI Swarm Backend on http://127.0.0.1:8000 ...
start "PayResolve AI - Backend (Port 8000)" cmd /k "cd /d "%~dp0" && .\venv\Scripts\uvicorn.exe backend.api.main:app --reload --host 127.0.0.1 --port 8000"

echo [2/2] Launching React + Vite Visualizer UI on http://localhost:5173 ...
start "PayResolve AI - Frontend (Port 5173)" cmd /k "cd /d "%~dp0frontend" && npm.cmd run dev"

echo.
echo [SUCCESS] Both servers are starting in separate windows!
echo Open http://localhost:5173 in your browser.

