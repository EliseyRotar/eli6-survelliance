@echo off
title Ruse Restore
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\ruse_restore.py" > "camera_testing\ruse_restore_stdout.log" 2> "camera_testing\ruse_restore_stderr.log"
