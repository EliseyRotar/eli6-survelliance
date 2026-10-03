@echo off
title Brand Backfill 1
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\backfill_brands.py" > "camera_testing\backfill_log.txt" 2> "camera_testing\backfill_err.txt"
