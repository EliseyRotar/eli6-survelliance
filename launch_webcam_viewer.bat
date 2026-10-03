@echo off
cd /d "C:\Users\eli6-admin\Documents\eli6-surveillance"
echo Starting webcam viewer at http://localhost:8765/
echo Open your browser to: http://localhost:8765/webcam_viewer.html
"C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe" "C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\serve_viewer.py"
