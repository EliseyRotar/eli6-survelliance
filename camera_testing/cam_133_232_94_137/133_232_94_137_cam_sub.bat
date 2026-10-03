@echo off
setlocal
set "FFPLAY=C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffplay.exe"
set "URL=rtsp://admin:admin@133.232.94.137:554/12"

echo ============================================================
echo  133.232.94.137  -  Sub Stream (800x600 H.265)
echo ============================================================
echo.

start "" /wait /b "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -Command "& '%FFPLAY%' -hide_banner -window_title '133.232.94.137 - Sub' -rtsp_transport tcp '%URL%'"
endlocal
