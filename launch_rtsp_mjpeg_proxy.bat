@echo off
title RTSP-MJPEG Proxy
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\rtsp_mjpeg_proxy.py" > "camera_testing\rtsp_mjpeg_proxy_stdout.log" 2> "camera_testing\rtsp_mjpeg_proxy_stderr.log"
