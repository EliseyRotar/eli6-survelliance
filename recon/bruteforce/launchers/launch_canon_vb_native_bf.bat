@echo off
title BF Canon VB Native Auth Endpoints
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "bruteforce\vendor_specific\canon_vb\vbviewer_native_bf.py" > "bruteforce\log_files\vbviewer_native_bf_log.txt" 2> "bruteforce\log_files\vbviewer_native_bf_err.txt"
