@echo off
setlocal

set "FFPLAY=C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffplay.exe"
set "URL=rtsp://admin:admin@133.232.94.137:554/11"

echo ============================================================
echo  133.232.94.137  -  Hipcam H.265 Live Stream (5MP)
echo  Chiyoda, Tokyo, Japan  (Camera 4 - Japan in project)
echo  HiSilicon Hi3518, model C6F0SoZ3N0PcL2
echo  2560x1920 H.265 Main + audio @ 15fps, 1536kbps
echo  RTSP on port 554, path /11 (main) or /12 (sub 800x600)
echo  Auth: admin/admin (root access)
echo ============================================================
echo.

start "" /wait /b "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -Command "& '%FFPLAY%' -hide_banner -window_title '133.232.94.137 - Tokyo - Hipcam H.265 5MP' -rtsp_transport tcp '%URL%'"
endlocal
