@echo off
chcp 65001 >nul

echo ========================================
echo   Backend Restart Script
echo ========================================
echo.

echo [1/3] Stopping backend service...
taskkill /F /FI "IMAGENAME eq python.exe" >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] Cleaning Python cache...
if exist "__pycache__" (
    rmdir /s /q "__pycache__"
)
if exist "agent\__pycache__" (
    rmdir /s /q "agent\__pycache__"
)
if exist "skill_engine\__pycache__" (
    rmdir /s /q "skill_engine\__pycache__"
)
if exist "tools\__pycache__" (
    rmdir /s /q "tools\__pycache__"
)

echo [3/3] Starting backend service...
echo.
echo ========================================
echo   Starting FastAPI Server
echo ========================================
echo.
echo Server is running at: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python main.py
if errorlevel 1 (
    echo.
    echo Server stopped with error. Press any key to exit...
    pause >nul
) else (
    echo.
    echo Server stopped. Press any key to exit...
    pause >nul
)
