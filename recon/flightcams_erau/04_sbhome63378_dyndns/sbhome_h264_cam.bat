@echo off
REM sbhome_h264_cam.bat
REM Live H.264 native view of sbhome63378.dyndns.org:16251 (private home AXIS M2025-LE)
REM This cam has NATIVE H.264 support via /axis-cgi/media.cgi - no transcode needed!
REM IP: 92.171.245.23 (Orange ISP, France)

setlocal
set FFPLAY="C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffplay.exe"
set SRC=http://sbhome63378.dyndns.org:16251/axis-cgi/media.cgi?container=matroska&videocodec=h264&resolution=1280x720

echo ============================================
echo  sbhome63378.dyndns.org:16251  -  H.264 Live
echo  AXIS M2025-LE Network Camera (private home)
echo  NATIVE H.264 over HTTP (1280x720 Main profile)
echo  Orange ISP, France  -  No transcode
echo ============================================
echo.

%FFPLAY% -hide_banner -loglevel warning -window_title "sbhome63378.dyndns.org H.264 (native)" -framedrop -fflags nobuffer -flags low_delay -an "%SRC%"

endlocal