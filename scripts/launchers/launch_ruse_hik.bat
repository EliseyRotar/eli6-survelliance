@echo off
title Ruse Hikvision BF
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\ruse_hikvision_bf.py" > "camera_testing\ruse_hik_bf_stdout.log" 2> "camera_testing\ruse_hik_bf_stderr.log"
