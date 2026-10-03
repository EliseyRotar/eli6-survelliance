@echo off
echo Starting all ingestors...
cd /d "C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
start "argus_v3" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" argus_ingest_v3.py
start "opencctv" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" opencctv_ingest.py
start "caltrans" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" caltrans_ingest.py
start "tfl" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" tfl_ingest.py
start "mass_scan3" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" mass_scan3.py
start "full_reprobe" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" full_reprobe.py
start "tv_full" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" trafficvision_full_ingest.py
start "netlas" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" netlas_ingest.py
start "pipeline" /B "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" run_pipeline.py
echo All started
