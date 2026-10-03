@echo off
title RTSP Scan
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\rtsp_scan.py" > "camera_testing\rtsp_scan_stdout.log" 2> "camera_testing\rtsp_scan_stderr.log"
