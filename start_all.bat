@echo off
REM ============================================================
REM ELI6 SURVEILLANCE - MASTER START
REM Starts dashboard + all proxies + background services
REM
REM Session 41 update (2026-10-03) - VISIBILITY CLASSIFICATION:
REM   - CSV `visibility` column: public 229,919 / private 113 / unknown 1
REM   - Dashboard: VISIBILITY chips (all/public/private/unknown) + PRIVATE
REM     tile badge; /api/cams?visibility=..., /api/stats by_visibility
REM   - After CSV changes: GET http://127.0.0.1:8773/api/refresh (no restart)
REM
REM Session 40 update (2026-10-03) - PROJECT REORGANIZATION:
REM   - Root decluttered: 495 files -> 24 (by-function layout)
REM   - Services moved to services\ (hls_proxy, skyline, digitraffic,
REM     fl511_token_daemon, cam_reaper, argus_geocode, fl511_helpers)
REM   - Scripts -> scripts\{ingest,scan,brute,geo,fix,fl511,misc,launchers}
REM   - CVE tools -> exploits\, recon folders -> recon\, data -> data\
REM   - Logs/screenshots -> archive\, docs -> docs\, tools -> tools\
REM   - 236 hardcoded path references rewritten repo-wide
REM   - controllable_Webcams.csv + pid files stay at root (hot paths)
REM   - .gitignore: backups/ (39GB), *.db (5.6GB), CSV >100MB excluded
REM   - Baseline commit before reorg = restore point (git revert)
REM
REM Session 38 update (2026-09-15):
REM   - 230,024 cams total (was 228,674)
REM   - +931 ALERTCalifornia cams (UC San Diego HPWREN wildfire cams, all live)
REM     * Master GeoJSON: https://cameras.alertcalifornia.org/public-camera-data/all_cameras-v3.json
REM     * 100% ffmpeg poster extraction success (931/931 JPEGs)
REM   - +44 Pet Paradise cams via abckam.com portal scrape (camera{N}.php pages)
REM     * 62 locations scraped, 90 unique stream URLs found, 44 new after dedup
REM     * Full naming pattern: petparadise{location}{N} or {abbrev}-{N}
REM     * Locations: Pet Paradise website lists 60+ US locations in 11 states
REM   - +375 OpenCCTV cams from sources not previously in DB
REM     * Castlerock, Asfinag, RIDOT, IBB-Istanbul, ArcGIS, camstreamer, etc.
REM   - Pet Paradise is hosted on abckam.com (Ant Media Server)
REM     * 5 active servers: video1, 2, 3, 9, 10 (others 403 / IP-restricted)
REM     * 9 total PP servers with public cams (1, 2, 3, 5, 6, 7, 9, 10, 17)
REM   - CSV patches: 1,920 AC cams had empty isp -> patched to 'alertcalifornia'
REM
REM Session 37 update (2026-09-14):
REM   - 228,674 cams total (was 228,619, +55)
REM   - +55 Pet Paradise cams (video1,2,3,9,10) verified LIVE
REM   - 494 Pet Paradise cams total (439 + 55)
REM   - abckam.com subdomain discovery via crt.sh: 22 subdomains
REM   - Ant Media Server 403 IP allowlist confirmed
REM   - ingest_pp_cams.py for adding PP cams
REM
REM Session 34 update (2026-09-14):
REM   - Fixed VirtualGrid.dispose (was no-op, caused player leaks)
REM   - MAX_ACTIVE_PLAYERS 6 -> 30
REM   - IntersectionObserver disconnect on tile remove
REM   - tile._disposeTile callback set per tile
REM   - evictOneInactive helper
REM   - Pause-on-scroll-out, full destroy on DOM removal
REM   - grid.js: overscan 2 -> 1 row
REM
REM Session 33 update (2026-09-14):
REM   - Added poster_ffmpeg (ffmpeg-based poster extractor service)
REM   - Added /api/poster/<idx> endpoint with negative caching
REM   - MAX_ACTIVE_PLAYERS=30, HLS streams stop after 30s playing
REM   - Added .tile-placeholder gradient (instant visible content)
REM   - player.js: 30s HLS auto-stop matches trafficvision.live
REM
REM Session 28 update:
REM   - Refreshed TrafficVision.Live catalog (150,897 cams captured)
REM   - Added 2,228 new TrafficVision cams to CSV (TxDOT, DFW, SCC, etc.)
REM   - Deduplicated 2,275 duplicate rows + 69 non-digit idx rows
REM   - Fixed HLS proxy manifest rewriter (relative segment URLs)
REM   - Fixed dashboard: pause/resume HLS instead of dispose/recreate
REM   - Fixed loadCams -> reloadCams typo
REM   - Reduced initial random load from 5000 to 2000 cams
REM
REM Session 27 update:
REM   - Uses port 8773 for dashboard (was 8765 - blocked by Windows firewall)
REM   - Starts fl511_token_daemon (refreshes divas tokens for FL511 cams)
REM   - Starts cam_reaper (one-shot probe pass to find dead cams)
REM   - Detects already-running services and skips them
REM   - Opens browser to dashboard when ready
REM
REM To start everything:  start_all.bat
REM To stop everything:     stop_all.bat
REM ============================================================
setlocal

set ROOT=C:\Users\eli6-admin\Documents\eli6-surveillance
set PY=C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe
set LOG_DIR=C:\Users\eli6-admin\AppData\Local\Temp

REM Service ports
set DASHBOARD_PORT=8773
set HLS_PROXY_PORT=8770
set SKYLINE_PORT=8771
set DIGITRAFFIC_PORT=8772

REM Log files
set LOG_FILE=%LOG_DIR%\eli6_start.log
set DASHBOARD_LOG=%LOG_DIR%\eli6-dashboard.log
set HLS_LOG=%LOG_DIR%\hls_proxy.log
set SKYLINE_LOG=%LOG_DIR%\skyline_proxy.log
set DIGITRAFFIC_LOG=%LOG_DIR%\digitraffic_proxy.log
set TOKEN_LOG=%LOG_DIR%\fl511_token_daemon.log
set REAPER_LOG=%LOG_DIR%\cam_reaper.log
set NOMINATIM_LOG=%LOG_DIR%\argus_geocode.log
set POSTER_LOG=%LOG_DIR%\poster_ffmpeg_runner.log

echo. > "%LOG_FILE%"
echo === START %DATE% %TIME% === >> "%LOG_FILE%"

echo.
echo === ELI6 SURVEILLANCE - START ===
echo.

REM --- Helpers ---
goto :main

:check_port
REM Usage: call :check_port 8773 result
REM Sets %~2=1 if port in use, 0 if free
set %~2=0
for /f "tokens=5" %%A in ('netstat -aon 2^>nul ^| findstr ":%~1 " ^| findstr "LISTENING"') do set "%~2=1"
goto :eof

:start_dashboard
echo [1/8] Starting dashboard (%DASHBOARD_PORT%)...
echo Starting dashboard >> "%LOG_FILE%"
cd /d "%ROOT%"
start "ELI6-Dashboard" /B "%PY%" "%ROOT%\api\run_dashboard.py"
cd /d "%ROOT%"
goto :eof

:start_hls_proxy
echo [2/8] Starting fl511 HLS proxy (%HLS_PROXY_PORT%)...
echo Starting fl511 HLS proxy >> "%LOG_FILE%"
start "ELI6-fl511" /B cmd /c ""%PY%" "%ROOT%\services\hls_proxy.py" %HLS_PROXY_PORT% > "%HLS_LOG%" 2>&1"
goto :eof

:start_skyline
echo [3/8] Starting Skyline HLS proxy (%SKYLINE_PORT%)...
echo Starting Skyline HLS proxy >> "%LOG_FILE%"
start "ELI6-Skyline" /B cmd /c ""%PY%" "%ROOT%\services\skyline_hls_proxy.py" %SKYLINE_PORT% > "%SKYLINE_LOG%" 2>&1"
goto :eof

:start_digitraffic
echo [4/8] Starting Digitraffic proxy (%DIGITRAFFIC_PORT%)...
echo Starting Digitraffic proxy >> "%LOG_FILE%"
start "ELI6-Digitraffic" /B cmd /c ""%PY%" "%ROOT%\services\digitraffic_proxy.py" %DIGITRAFFIC_PORT% > "%DIGITRAFFIC_LOG%" 2>&1"
goto :eof

:start_token_daemon
echo [5/8] Starting fl511 token daemon...
echo Starting fl511 token daemon >> "%LOG_FILE%"
start "ELI6-TokenDaemon" /B cmd /c ""%PY%" "%ROOT%\services\fl511_token_daemon.py" > "%TOKEN_LOG%" 2>&1"
goto :eof

:start_cam_reaper
echo [6/8] Starting cam reaper (probe pass)...
echo Starting cam reaper >> "%LOG_FILE%"
start "ELI6-Reaper" /B cmd /c ""%PY%" "%ROOT%\services\cam_reaper.py" probe > "%REAPER_LOG%" 2>&1"
goto :eof

:start_argus_geocode
echo [7/8] Starting argus geocode (rate-limited 1/sec)...
echo Starting argus geocode >> "%LOG_FILE%"
start "ELI6-ArgusGeocode" /B cmd /c ""%PY%" "%ROOT%\services\argus_geocode.py" > "%NOMINATIM_LOG%" 2>&1"
goto :eof

:start_poster_extractor
echo [8/8] Starting ffmpeg poster extractor (long-running, 6,654 HLS cams)...
echo Starting poster extractor >> "%LOG_FILE%"
start "ELI6-PosterExtractor" /B cmd /c ""%PY%" "%ROOT%\camera_testing\poster_ffmpeg.py" >> "%POSTER_LOG%" 2>&1"
goto :eof

:main
REM --- fl511 HLS ---
call :check_port %HLS_PROXY_PORT% RES
if "%RES%"=="1" (echo [skip] fl511 already on %HLS_PROXY_PORT%) else (call :start_hls_proxy)

REM --- Skyline ---
call :check_port %SKYLINE_PORT% RES
if "%RES%"=="1" (echo [skip] Skyline already on %SKYLINE_PORT%) else (call :start_skyline)

REM --- Digitraffic ---
call :check_port %DIGITRAFFIC_PORT% RES
if "%RES%"=="1" (echo [skip] Digitraffic already on %DIGITRAFFIC_PORT%) else (call :start_digitraffic)

REM --- Dashboard ---
call :check_port %DASHBOARD_PORT% RES
if "%RES%"=="1" (echo [skip] Dashboard already on %DASHBOARD_PORT%) else (call :start_dashboard)

REM --- fl511 token daemon (background) ---
tasklist /FI "IMAGENAME eq python.exe" /FO LIST 2>nul | findstr /C:"fl511_token_daemon.py" >nul
if %errorlevel% neq 0 (call :start_token_daemon) else (echo [skip] fl511 token daemon already running)

REM --- cam reaper (one-shot probe) ---
tasklist /FI "IMAGENAME eq python.exe" /FO LIST 2>nul | findstr /C:"cam_reaper.py" >nul
if %errorlevel% neq 0 (call :start_cam_reaper) else (echo [skip] cam reaper already running)

REM --- argus geocode (rate-limited Nominatim, very long) ---
tasklist /FI "IMAGENAME eq python.exe" /FO LIST 2>nul | findstr /C:"argus_geocode.py" >nul
if %errorlevel% neq 0 (call :start_argus_geocode) else (echo [skip] argus geocode already running)

REM --- ffmpeg poster extractor (long-running, ~50 min for all 6,654 HLS cams) ---
tasklist /FI "IMAGENAME eq python.exe" /FO LIST 2>nul | findstr /C:"poster_ffmpeg.py" >nul
if %errorlevel% neq 0 (call :start_poster_extractor) else (echo [skip] poster extractor already running)

REM --- Wait for dashboard ---
echo.
echo Waiting for dashboard (max 30s)...
set /a WAITED=0
:wait_dashboard
call :check_port %DASHBOARD_PORT% RES
if "%RES%"=="1" goto :all_up
set /a WAITED+=1
if %WAITED% gtr 30 goto :all_up
timeout /t 1 /nobreak >nul
goto :wait_dashboard

:all_up
echo.
echo === STATUS ===
echo.
echo   Dashboard          http://127.0.0.1:%DASHBOARD_PORT%
echo   fl511 HLS proxy    http://127.0.0.1:%HLS_PROXY_PORT%/health
echo   Skyline proxy      http://127.0.0.1:%SKYLINE_PORT%/health
echo   Digitraffic proxy  http://127.0.0.1:%DIGITRAFFIC_PORT%/health
echo.
echo Background services:
echo   - fl511 token daemon   (refreshes divas.cloud tokens)
echo   - cam reaper           (one-shot probe pass)
echo   - argus geocode        (Nominatim reverse, 1 req/sec, ~12hr for 60k cams)
echo   - poster extractor     (ffmpeg -> /web_viewer/static/posters/<idx>.jpg)
echo.
echo Logs:
echo   %DASHBOARD_LOG%
echo   %HLS_LOG%
echo   %SKYLINE_LOG%
echo   %DIGITRAFFIC_LOG%
echo   %TOKEN_LOG%
echo   %REAPER_LOG%
echo   %NOMINATIM_LOG%
echo   %POSTER_LOG%
echo.

REM --- Open browser ---
set BROWSER=
if exist "%ProgramFiles%\Mozilla Firefox\firefox.exe" set BROWSER=%ProgramFiles%\Mozilla Firefox\firefox.exe
if exist "%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe" if not defined BROWSER set BROWSER=%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe
if not defined BROWSER set BROWSER=msedge.exe
echo Opening %BROWSER% ...
start "" "%BROWSER%" "http://127.0.0.1:%DASHBOARD_PORT%"

endlocal
