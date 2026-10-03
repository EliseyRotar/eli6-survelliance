@echo off
title Video Stream Upgrader
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "video_upgrader.py" > "video_upgrade_log.txt" 2> "video_upgrade_err.txt"
