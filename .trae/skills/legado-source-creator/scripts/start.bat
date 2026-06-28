@echo off
setlocal EnableDelayedExpansion

:: ============================================================
::  Legado Client 3.0 - One-click Start Script
::  Modes: web / backend / frontend / install / db-init / build / stop
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "WEB_DIR=%SCRIPT_DIR%legado_client\web\admin"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"
set "PIP=%VENV_DIR%\Scripts\pip.exe"
set "LEGADO_CLI=%PYTHON% -m legado_client.cli"

set "MODE=web"
set "HOST=127.0.0.1"
set "PORT=8080"
set "SKIP_INSTALL=0"

:parse_args
if "%~1"=="" goto end_parse
if /i "%~1"=="web" set "MODE=web"
if /i "%~1"=="backend" set "MODE=backend"
if /i "%~1"=="frontend" set "MODE=frontend"
if /i "%~1"=="install" set "MODE=install"
if /i "%~1"=="db-init" set "MODE=db-init"
if /i "%~1"=="build" set "MODE=build"
if /i "%~1"=="stop" set "MODE=stop"
if /i "%~1"=="--host" (
    set "HOST=%~2"
    shift
)
if /i "%~1"=="--port" (
    set "PORT=%~2"
    shift
)
if /i "%~1"=="--skip-install" set "SKIP_INSTALL=1"
shift
goto parse_args
:end_parse

echo.
echo  ========================================
echo   Legado Client 3.0
echo   Mode: %MODE%    Host: %HOST%:%PORT%
echo  ========================================
echo.

if "%SKIP_INSTALL%"=="1" goto skip_install

if not exist "%VENV_DIR%" (
    echo  [1/3] Creating venv...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo  [ERROR] Failed to create venv. Is Python installed?
        exit /b 1
    )
)

if not exist "%PYTHON%" (
    echo  [ERROR] Venv broken. Delete .venv and retry.
    exit /b 1
)

echo  [2/3] Checking Python deps...
"%PIP%" install -e "%SCRIPT_DIR%." --quiet 2>nul
"%PIP%" install fastapi "uvicorn[standard]" python-multipart httpx websockets aiomysql pymysql alembic "sqlalchemy[asyncio]" python-dotenv beautifulsoup4 lxml --quiet 2>nul

if not "%MODE%"=="frontend" if not "%MODE%"=="web" goto skip_install

echo  [3/3] Checking frontend deps...
if not exist "%WEB_DIR%\node_modules" (
    echo  Installing frontend deps (first run may be slow)...
    cd /d "%WEB_DIR%" && npm install
    if errorlevel 1 (
        echo  [ERROR] Frontend npm install failed
        exit /b 1
    )
)
cd /d "%SCRIPT_DIR%"

:skip_install

if "%MODE%"=="install" (
    echo  Install complete! Run start.bat to launch.
    exit /b 0
)

if "%MODE%"=="db-init" (
    echo  Initializing database...
    "%LEGADO_CLI%" db init
    echo  Done.
    exit /b 0
)

if "%MODE%"=="build" (
    echo  Building frontend for production...
    cd /d "%WEB_DIR%" && npm run build
    if errorlevel 1 (
        echo  [ERROR] Frontend build failed
        exit /b 1
    )
    cd /d "%SCRIPT_DIR%"
    echo  Build complete. Run: start.bat backend
    exit /b 0
)

if "%MODE%"=="stop" (
    echo  Stopping all services...
    taskkill /f /fi "WINDOWTITLE eq Legado-Backend*" 2>nul
    taskkill /f /fi "WINDOWTITLE eq Legado-Frontend*" 2>nul
    echo  Done.
    exit /b 0
)

if "%MODE%"=="frontend" goto start_frontend

echo  Starting backend %HOST%:%PORT% ...
start "Legado-Backend" cmd /c "%PYTHON% -m uvicorn legado_client.server.app:app --host %HOST% --port %PORT% --reload"
echo  Backend: http://%HOST%:%PORT%
echo  API docs: http://%HOST%:%PORT%/docs
echo.

if "%MODE%"=="backend" goto wait

:start_frontend
echo  Starting frontend dev server...
start "Legado-Frontend" cmd /c "cd /d %WEB_DIR% && npm run dev"
echo  Frontend: http://localhost:5173
echo.

:wait
echo  ========================================
echo   Running...
echo   Backend:  http://%HOST%:%PORT%
if not "%MODE%"=="backend" echo   Frontend: http://localhost:5173
echo   Health:   http://%HOST%:%PORT%/api/health
echo  ========================================
echo.
echo  Run start.bat stop to stop all services.
echo.
timeout /t 3 /nobreak >nul

echo  Health check...
"%PYTHON%" -c "import urllib.request; r=urllib.request.urlopen('http://%HOST%:%PORT%/api/health'); print('  Status:', r.read().decode())" 2>nul
if errorlevel 1 (
    echo  [WARN] Health check failed - backend may still be starting...
) else (
    echo  Backend OK
)

echo.
pause
