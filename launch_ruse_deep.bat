@echo off
title Ruse Deep Scan
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\ruse_deep_scan.py" > "camera_testing\ruse_deep_stdout.log" 2> "camera_testing\ruse_deep_stderr.log"
