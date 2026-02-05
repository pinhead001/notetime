@echo off
REM Notetime Docker Startup Script for Windows
REM This script helps you start Notetime on Windows

echo ========================================
echo    Notetime Docker Startup (Windows)
echo ========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running.
    echo.
    echo Please install Docker Desktop from:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is installed
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker Desktop is not running.
    echo.
    echo Please start Docker Desktop and try again.
    echo Look for the whale icon in your system tray.
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Capture git info for build metadata
for /f "delims=" %%i in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set GIT_BRANCH=%%i
for /f "delims=" %%i in ('git rev-parse --short HEAD 2^>nul') do set GIT_COMMIT=%%i
if not defined GIT_BRANCH set GIT_BRANCH=local
if not defined GIT_COMMIT set GIT_COMMIT=dev
echo [INFO] Build info: %GIT_BRANCH% @ %GIT_COMMIT%
echo.

REM Ask user what they want to do
echo What would you like to do?
echo.
echo 1. Start Notetime (development mode, with logs)
echo 2. Start Notetime (background mode)
echo 3. Stop Notetime
echo 4. Restart Notetime
echo 5. View logs
echo 6. Check status
echo 7. Clean up (stop and remove containers)
echo 8. Exit
echo.

set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" goto start_dev
if "%choice%"=="2" goto start_background
if "%choice%"=="3" goto stop
if "%choice%"=="4" goto restart
if "%choice%"=="5" goto logs
if "%choice%"=="6" goto status
if "%choice%"=="7" goto cleanup
if "%choice%"=="8" goto end

echo Invalid choice. Please run the script again.
pause
exit /b 1

:start_dev
echo.
echo Starting Notetime in development mode...
echo Press Ctrl+C to stop
echo.
docker-compose up --build
goto end

:start_background
echo.
echo Starting Notetime in background mode...
docker-compose up -d --build
if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Notetime is starting!
    echo.
    echo Wait a few seconds, then open your browser to:
    echo http://localhost:8000
    echo.
    echo To view logs, run this script again and choose option 5
    echo To stop, run this script again and choose option 3
) else (
    echo.
    echo [ERROR] Failed to start Notetime
    echo Check the errors above
)
echo.
pause
goto end

:stop
echo.
echo Stopping Notetime...
docker-compose down
if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Notetime stopped
) else (
    echo.
    echo [ERROR] Failed to stop Notetime
)
echo.
pause
goto end

:restart
echo.
echo Restarting Notetime...
docker-compose restart
if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Notetime restarted
    echo Open your browser to: http://localhost:8000
) else (
    echo.
    echo [ERROR] Failed to restart Notetime
)
echo.
pause
goto end

:logs
echo.
echo Showing Notetime logs (Press Ctrl+C to exit)...
echo.
docker-compose logs -f
goto end

:status
echo.
echo Checking Notetime status...
echo.
docker-compose ps
echo.
pause
goto end

:cleanup
echo.
echo WARNING: This will stop and remove all containers.
echo Your data in the database volume will be preserved.
echo.
set /p confirm="Are you sure? (y/n): "
if /i "%confirm%"=="y" (
    echo.
    echo Cleaning up...
    docker-compose down
    echo.
    echo [SUCCESS] Cleanup complete
) else (
    echo.
    echo Cleanup cancelled
)
echo.
pause
goto end

:end
echo.
echo Done!
