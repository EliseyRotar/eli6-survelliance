@echo off
REM Heavy insecam re-crawl + multi-pipeline driver.
REM Reuse camera_hack_dump.py to refresh insecam_live_cams.txt, then full_probe.py,
REM then bf_cameras.py on auth-requirers, then insecam_2019_ingest on stale data,
REM then camera_hack_probe on the freshest dump.
REM Cycles every 30 minutes to keep disk + CSV updated.

setlocal
set SECONDS=0

:loop
echo [%date% %time%] Starting cycle %SECONDS%
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" "C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\camera_hack_dump.py"
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" "C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\fast_probe.py"
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" "C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\insecam_2019_ingest.py"
echo [%date% %time%] Cycle done. Restarting in 30s...
timeout /T 30 /NOBREAK > NUL
goto loop
