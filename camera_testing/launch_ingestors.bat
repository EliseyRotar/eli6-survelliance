@echo off
echo Starting all camera ingestors at %time%
cd /d "C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"

start "argus_v3" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" argus_ingest_v3.py > argus3_stdout.log 2> argus3_stderr.log
start "opencctv" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" opencctv_ingest.py > opencctv_stdout.log 2> opencctv_stderr.log
start "caltrans" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" caltrans_ingest.py > caltrans_stdout.log 2> caltrans_stderr.log
start "tfl" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" tfl_ingest.py > tfl_stdout.log 2> tfl_stderr.log
start "netlas" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" netlas_ingest.py > netlas_stdout.log 2> netlas_stderr.log

echo All started at %time%
