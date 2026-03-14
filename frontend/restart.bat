@echo off
chcp 65001 >nul

echo ========================================
echo   Frontend Restart Script
echo ========================================
echo.

echo [1/3] Stopping frontend service...
taskkill /F /FI "IMAGENAME eq node.exe" >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] Cleaning cache...
if exist "node_modules\.vite" (
    rmdir /s /q "node_modules\.vite"
)

echo [3/3] Starting frontend service...
echo.
echo ========================================
echo   Starting Vite Dev Server
echo ========================================
echo.
echo Server is running at: http://localhost:5175
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

npm run dev
if errorlevel 1 (
    echo.
    echo Server stopped with error. Press any key to exit...
    pause >nul
) else (
    echo.
    echo Server stopped. Press any key to exit...
    pause >nul
)
