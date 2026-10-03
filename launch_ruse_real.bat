@echo off
title Ruse Real IP Cam Scan
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\ruse_real_ip_scan.py" > "camera_testing\ruse_real_log.txt" 2> "camera_testing\ruse_real_err.txt"
