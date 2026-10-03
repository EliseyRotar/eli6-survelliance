@echo off
title Ruse ISP Direct Scan
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\ruse_isp_scan.py" > "camera_testing\ruse_isp_log.txt" 2> "camera_testing\ruse_isp_err.txt"
