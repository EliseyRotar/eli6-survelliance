@echo off
title Start All Ingestors
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance

REM Start all background ingestors
start "Argus" /min "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\argus_ingest_v3.py"
start "OpenCCTV" /min "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\opencctv_ingest.py"
start "TrafficVision" /min "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\trafficvision_full_ingest_v3.py"
start "Caltrans" /min "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\caltrans_ingest.py"
start "TfL" /min "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\tfl_ingest.py"
start "Netlas" /min "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\netlas_ingest.py"
start "Mass Scan" /min "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\mass_scan3.py"
start "Full Reprobe" /min "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\full_reprobe.py"
start "Pipeline" /min "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\run_pipeline.py"
start "MJPEG Proxy" /min "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\vbviewer_mjpeg_proxy.py"
start "Viewer Server" /min "C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\serve_viewer.py"

echo All ingestors started
