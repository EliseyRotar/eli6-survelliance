@echo off
setlocal
set "FFMPEG=C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
set "URL=rtsp://admin:admin@133.232.94.137:554/11"
set "OUT=%USERPROFILE%\Desktop\133_232_94_137_recording.mp4"

if "%~2"=="" (set "DUR=30") else (set "DUR=%~2")
echo Recording %DUR%s from 133.232.94.137 to %OUT% ...
"%FFMPEG%" -y -hide_banner -loglevel error -rtsp_transport tcp -i "%URL%" -t %DUR% -c copy "%OUT%"
echo Saved: %OUT%
endlocal
