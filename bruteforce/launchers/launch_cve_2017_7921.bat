@echo off
title BF CVE-2017-7921
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "bruteforce\vendor_specific\hikvision\cve_2017_7921.py" %* > "bruteforce\log_files\cve_2017_7921_log.txt" 2> "bruteforce\log_files\cve_2017_7921_err.txt"
