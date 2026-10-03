@echo off
title Ruse Services Scanner
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\ruse_scan_services.py" > "camera_testing\ruse_scan_stdout.log" 2> "camera_testing\ruse_scan_stderr.log"
