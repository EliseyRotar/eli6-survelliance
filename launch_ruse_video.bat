@echo off
title Ruse Video Finder
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\ruse_video_finder.py" > "camera_testing\ruse_video_log.txt" 2> "camera_testing\ruse_video_err.txt"
