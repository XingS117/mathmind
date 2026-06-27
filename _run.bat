@echo off
cd /d D:\Sven\maths
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH. Install Python or run backend with your configured interpreter.
  pause
  exit /b 1
)

start "MathMind API" cmd /k python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
start "MathMind Web" cmd /k "cd /d D:\Sven\maths\frontend && npm.cmd run dev"
