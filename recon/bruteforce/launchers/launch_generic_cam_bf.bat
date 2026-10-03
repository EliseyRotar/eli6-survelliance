@echo off
title BF Hikvision Default Creds
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "bruteforce\vendor_specific\hikvision\generic_cam_bf.py" %* > "bruteforce\log_files\generic_cam_bf_log.txt" 2> "bruteforce\log_files\generic_cam_bf_err.txt"
