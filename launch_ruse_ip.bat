@echo off
title Ruse IP Ranges
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\ruse_ip_ranges.py" > "camera_testing\ruse_ip_ranges_stdout.log" 2> "camera_testing\ruse_ip_ranges_stderr.log"
