@echo off
title BF Canon VB CVE+BF
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "bruteforce\vendor_specific\canon_vb\vbviewer_bf_cve.py" > "bruteforce\log_files\vbviewer_bf_cve_log.txt" 2> "bruteforce\log_files\vbviewer_bf_cve_err.txt"
