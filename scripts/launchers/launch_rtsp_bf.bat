@echo off
title RTSP BF
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\rtsp_bf.py" > "camera_testing\rtsp_bf_stdout.log" 2> "camera_testing\rtsp_bf_stderr.log"
