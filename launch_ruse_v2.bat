@echo off
title Ruse V2 Scan
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\ruse_v2_scan.py" > "camera_testing\ruse_v2_stdout.log" 2> "camera_testing\ruse_v2_stderr.log"
