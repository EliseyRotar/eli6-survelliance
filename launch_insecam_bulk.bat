@echo off
title Insecam Bulk Scraper
cd /d C:\Users\eli6-admin\Documents\eli6-surveillance
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\pythonw.exe" "camera_testing\insecam_bulk_scraper.py" > "camera_testing\insecam_bulk_stdout.log" 2> "camera_testing\insecam_bulk_stderr.log"
