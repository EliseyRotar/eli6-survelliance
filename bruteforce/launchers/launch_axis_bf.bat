@echo off
title BF AXIS
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "bruteforce\vendor_specific\axis\axis_bruter.py" %* > "bruteforce\log_files\axis_bruter_log.txt" 2> "bruteforce\log_files\axis_bruter_err.txt"
