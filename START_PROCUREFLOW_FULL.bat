@echo off
SetLocal EnableExtensions EnableDelayedExpansion
title ProcureFlow Full Startup

REM ==============================================================================
REM ProcureFlow Full Server Startup v3.1
REM ==============================================================================
REM Starts: Backend (8000), Frontend (5175)
REM Credentials are loaded from ignored backend\.env only.
REM ==============================================================================

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend_v2"
set "PYTHON_EXE=C:\Program Files\Python310\python.exe"
set "LOGDIR=%BACKEND%\runtime\startup"
set "BACKEND_LOG=%LOGDIR%\backend.log"
set "BACKEND_ERR=%LOGDIR%\backend.err.log"
set "FRONTEND_LOG=%LOGDIR%\frontend.log"
set "FRONTEND_ERR=%LOGDIR%\frontend.err.log"

if not exist "%BACKEND%\.env" (
  echo ERROR: Missing ignored credential file "%BACKEND%\.env".
  echo Copy backend\.env.example to backend\.env and set real secrets.
  exit /b 1
)
for /F "usebackq eol=# tokens=1,* delims==" %%A in ("%BACKEND%\.env") do set "%%A=%%B"
for %%V in (OWNER_EMAIL OWNER_PASSWORD POSTGRES_PASSWORD DATABASE_URL JWT_SECRET JWT_REFRESH_SECRET REDIS_URL) do (
  if "!%%V!"=="" (
    echo ERROR: Required variable %%V is missing from backend\.env.
    exit /b 1
  )
)
set "PROCUREFLOW_BACKEND_URL=http://127.0.0.1:8000"
set "PROCUREFLOW_FRONTEND_URL=http://localhost:5175"

echo.
echo ============================================================================
echo  ProcureFlow Full Server Startup v3.1
echo ============================================================================
echo.

REM ── Step 1: Log dir ─────────────────────────────────────────────────────────
echo [1/10] Checking prerequisites...
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
if not exist "%PYTHON_EXE%" (
  echo   ERROR: Python 3.10 was not found at "%PYTHON_EXE%".
  pause
  exit /b 1
)
where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo   ERROR: npm.cmd was not found. Install Node.js and reopen this window.
  pause
  exit /b 1
)
if not exist "%FRONTEND%\node_modules" (
  echo   Installing frontend dependencies...
  call npm.cmd install --prefix "%FRONTEND%"
  if errorlevel 1 (
    echo   ERROR: npm install failed.
    pause
    exit /b 1
  )
)
echo   OK: Python, npm, frontend dependencies, and log directory are ready.
echo.

REM ── Step 2: Backend environment ──────────────────────────────────────────────
echo [2/10] Using ignored backend .env...
echo   OK: backend environment loaded
echo.

REM ── Step 3: Frontend environment ─────────────────────────────────────────────
echo [3/10] Checking frontend environment...
if not exist "%FRONTEND%\.env" (
  > "%FRONTEND%\.env" (
    echo VITE_API_URL=
    echo VITE_PORT=5175
    echo VITE_HOST=0.0.0.0
    echo VITE_ENABLE_DEMO_MODE=false
    echo VITE_ENABLE_SSO=false
  )
)
findstr /I /B "VITE_OWNER_PASSWORD= VITE_EGP_PASSWORD= VITE_SMTP_PASS=" "%FRONTEND%\.env" >nul 2>&1
if not errorlevel 1 (
  echo ERROR: Secrets must not be stored in VITE_* variables.
  exit /b 1
)
echo   OK: frontend environment contains no credential variables
echo.

REM ── Step 4: Check PostgreSQL ────────────────────────────────────────────────
echo [4/10] Starting/checking PostgreSQL 17...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ready = Test-NetConnection -ComputerName '127.0.0.1' -Port 5433 -InformationLevel Quiet -WarningAction SilentlyContinue; if (-not $ready) { $pg = 'C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe'; if (Test-Path -LiteralPath $pg) { & $pg start -D 'C:\Program Files\PostgreSQL\17\data' -l 'C:\Program Files\PostgreSQL\17\data\pg.log' | Out-Host; Start-Sleep -Seconds 3 } }; if (Test-NetConnection -ComputerName '127.0.0.1' -Port 5433 -InformationLevel Quiet -WarningAction SilentlyContinue) { Write-Host '  OK: PostgreSQL is listening on port 5433' } else { Write-Host '  ERROR: PostgreSQL 17 is not reachable on port 5433'; exit 1 }"
if errorlevel 1 (
  pause
  exit /b 1
)
echo.

echo Checking Redis...
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (-not (Test-NetConnection -ComputerName '127.0.0.1' -Port 6379 -InformationLevel Quiet -WarningAction SilentlyContinue)) { $redis = Get-Command redis-server.exe -ErrorAction SilentlyContinue; if ($redis) { Start-Process -WindowStyle Hidden -FilePath $redis.Source } }; Start-Sleep -Seconds 1; if (-not (Test-NetConnection -ComputerName '127.0.0.1' -Port 6379 -InformationLevel Quiet -WarningAction SilentlyContinue)) { Write-Host '  ERROR: Redis is required for Celery'; exit 1 }; Write-Host '  OK: Redis is listening on port 6379'"
if errorlevel 1 (
  pause
  exit /b 1
)
echo.

REM ── Step 5: Ollama ───────────────────────────────────────────────────────────
echo [5/10] Starting/checking Ollama...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3 | Out-Null; Write-Host '  OK: Ollama is running' } catch { $ollama = Get-Command ollama.exe -ErrorAction SilentlyContinue; if ($ollama) { Start-Process -WindowStyle Hidden -FilePath $ollama.Source -ArgumentList 'serve'; Write-Host '  Started Ollama (model: qwen2.5:7b)' } else { Write-Host '  WARNING: Ollama is not installed; AI features will use configured fallbacks' } }"
echo.

REM ── Step 6: Kill existing processes ─────────────────────────────────────────
echo [6/10] Stopping existing processes on ports 8000, 5175...
powershell -NoProfile -ExecutionPolicy Bypass -Command "foreach ($port in @(8000,5175)) { try { $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue; foreach ($c in $conns) { Write-Host ('  Killing PID ' + $c.OwningProcess + ' on port ' + $port); Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue } } catch {} }; Write-Host '  Done'"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'celery.+app[.]celery_app' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2"
echo.

REM ── Step 7: Start Backend (port 8000) ───────────────────────────────────────
echo [7/10] Starting backend on http://127.0.0.1:8000...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -WindowStyle Hidden -FilePath '%PYTHON_EXE%' -ArgumentList @('-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8000') -WorkingDirectory '%BACKEND%' -RedirectStandardOutput '%BACKEND_LOG%' -RedirectStandardError '%BACKEND_ERR%'"
echo   Waiting for backend...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 15"

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 10; Write-Host ('  OK: Backend running - ' + ($r | ConvertTo-Json -Compress)) } catch { Write-Host '  ERROR: Backend failed its health check'; exit 1 }"
if errorlevel 1 (
  echo   See "%BACKEND_ERR%"
  pause
  exit /b 1
)
echo.

echo Starting Celery worker and beat...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -WindowStyle Hidden -FilePath '%PYTHON_EXE%' -ArgumentList @('-m','celery','-A','app.celery_app:celery_app','worker','-Q','high,default,low','--pool=solo','--loglevel=INFO','--hostname=procureflow-worker@%%h') -WorkingDirectory '%BACKEND%' -RedirectStandardOutput '%LOGDIR%\celery-worker.log' -RedirectStandardError '%LOGDIR%\celery-worker.err.log'; Start-Process -WindowStyle Hidden -FilePath '%PYTHON_EXE%' -ArgumentList @('-m','celery','-A','app.celery_app:celery_app','beat','--loglevel=INFO') -WorkingDirectory '%BACKEND%' -RedirectStandardOutput '%LOGDIR%\celery-beat.log' -RedirectStandardError '%LOGDIR%\celery-beat.err.log'"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 5; Set-Location -LiteralPath '%BACKEND%'; $ping = & '%PYTHON_EXE%' -m celery -A app.celery_app:celery_app inspect ping --timeout 5; if ($ping -notmatch 'pong') { Write-Host '  ERROR: Celery worker failed readiness ping'; exit 1 }; Write-Host '  OK: Celery worker and beat started'"
if errorlevel 1 (
  pause
  exit /b 1
)
echo.

REM ── Step 8: Start Frontend (port 5175) ──────────────────────────────────────
echo [8/10] Starting frontend on http://127.0.0.1:5175...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$npm = (Get-Command npm.cmd -ErrorAction Stop).Source; Start-Process -WindowStyle Hidden -FilePath $npm -ArgumentList @('run','dev','--','--host','0.0.0.0','--port','5175') -WorkingDirectory '%FRONTEND%' -RedirectStandardOutput '%FRONTEND_LOG%' -RedirectStandardError '%FRONTEND_ERR%'"
echo   Waiting for frontend...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 15"

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5175' -TimeoutSec 10 -UseBasicParsing; Write-Host ('  OK: Frontend running (HTTP ' + $r.StatusCode + ')') } catch { Write-Host '  ERROR: Frontend failed its health check'; exit 1 }"
if errorlevel 1 (
  echo   See "%FRONTEND_ERR%"
  pause
  exit /b 1
)
echo.

REM ── Step 9: Test API login ──────────────────────────────────────────────────
echo [9/10] Testing owner API login...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $body = @{ email = $env:OWNER_EMAIL; password = $env:OWNER_PASSWORD } | ConvertTo-Json; $login = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/auth/login' -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 10; if (-not $login.access_token) { throw 'No access token returned' }; Write-Host '  OK: Owner login verified' } catch { Write-Host ('  ERROR: Owner login failed - ' + $_.Exception.Message); exit 1 }"
if errorlevel 1 (
  pause
  exit /b 1
)
echo.

REM ── Step 10: Summary ────────────────────────────────────────────────────────
echo [10/10] Done!
echo.
echo ============================================================================
echo  STARTUP COMPLETE
echo ============================================================================
echo.
echo  http://127.0.0.1:8000  - Backend API (FastAPI)
echo  http://127.0.0.1:5175  - Frontend (SPA + MPA on same port)
echo.
echo  ── SPA (React Router - client-side navigation) ──────────────────────────────
echo    /dashboard        - Main Dashboard
echo    /monitoring       - Opportunity Monitoring
echo    /knowledge        - Knowledge Center
echo    /tenders          - Tender List
echo    /settings         - Settings
echo    /ppr2025          - PPR 2025 Compliance
echo    /learning         - Learning Hub
echo    /clauses          - Clause Explorer
echo    /trust/chat       - Trust Chat
echo.
echo  ── MPA (separate HTML per page - full reload) ───────────────────────────────
echo    /mpa/dashboard.html    - Dashboard
echo    /mpa/monitoring.html   - Monitoring
echo    /mpa/tenders.html      - Tenders
echo    /mpa/knowledge.html    - Knowledge
echo    /mpa/settings.html     - Settings
echo    /mpa/ppr2025.html      - PPR 2025
echo    /mpa/learning.html     - Learning
echo    /mpa/pricing.html      - Pricing Lab
echo    /mpa/clauses.html      - Clause Explorer
echo    /mpa/trust-chat.html   - Trust Chat
echo.
echo  Login and service credentials: loaded from ignored backend\.env
echo.
echo  PostgreSQL: localhost:5433 / procureflow_bd
echo  Ollama:     http://localhost:11434 (qwen2.5:7b)
echo  Logs:       %LOGDIR%
echo ============================================================================
echo.
start "" "http://localhost:5175/login"
echo Press any key to exit.
pause >nul
