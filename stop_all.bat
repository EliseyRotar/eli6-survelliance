@echo off
REM ============================================================
REM ELI6 SURVEILLANCE - STOP
REM Stops dashboard, all proxies, and background services
REM
REM Kills in order:
REM   1. Dashboard supervisor (so it doesn't restart the child)
REM   2. Cam reaper (if running)
REM   3. Anything listening on our ports (8773, 8770, 8771, 8772)
REM   4. Python processes with ELI6- window title
REM ============================================================
setlocal

echo.
echo === STOPPING ELI6 SURVEILLANCE ===
echo.

REM Kill the dashboard supervisor first (so it stops relaunching app.py)
if exist "C:\Users\eli6-admin\Documents\eli6-surveillance\eli6-dashboard.pid" (
    set /p DASH_PID=<"C:\Users\eli6-admin\Documents\eli6-surveillance\eli6-dashboard.pid"
    echo Killing dashboard supervisor PID !DASH_PID!
    taskkill /F /PID !DASH_PID! >nul 2>&1
)

REM Kill any cam reaper pidfile
if exist "C:\Users\eli6-admin\Documents\eli6-surveillance\cam_reaper.pid" (
    set /p RP_PID=<"C:\Users\eli6-admin\Documents\eli6-surveillance\cam_reaper.pid"
    echo Killing cam reaper PID !RP_PID!
    taskkill /F /PID !RP_PID! >nul 2>&1
)

REM Kill anything listening on our ports
for %%P in (8773 8770 8771 8772) do (
    for /f "tokens=5" %%A in ('netstat -aon ^| findstr ":%%P " ^| findstr "LISTENING"') do (
        echo Killing PID %%A on port %%P
        taskkill /F /PID %%A >nul 2>&1
    )
)

REM Final sweep: any python process whose window title contains "ELI6-"
for /f "tokens=2 delims=," %%P in ('tasklist /V /FI "IMAGENAME eq python.exe" /FO CSV /NH 2^>nul ^| findstr /I "ELI6-"') do (
    set "PID=%%~P"
    if defined PID (
        echo Killing ELI6- tagged python PID !PID!
        taskkill /F /PID !PID! >nul 2>&1
    )
)

echo.
echo === STOPPED ===
echo.

endlocal
