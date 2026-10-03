@echo off
REM flightcamsouth_h264_cam.bat
REM Live H.264 view of flightcamsouth.db.erau.edu (Daytona Beach campus, south flight cam)
REM Source: AXIS M2025-LE Network Camera, Embry-Riddle Aeronautical University
REM Native H.264 via /axis-cgi/media.cgi (works directly, no transcode needed)

setlocal
set FFPLAY="C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffplay.exe"
set SRC=http://flightcamsouth.db.erau.edu/axis-cgi/media.cgi?container=matroska&videocodec=h264&resolution=1280x720

echo ============================================
echo  flightcamsouth.db.erau.edu  -  H.264 Live
echo  AXIS M2025-LE  -  Embry-Riddle Daytona Beach
echo  Native H.264 over HTTP (1280x720)
echo ============================================
echo.

%FFPLAY% -hide_banner -loglevel warning -window_title "flightcamsouth.db.erau.edu H.264" -framedrop -fflags nobuffer -flags low_delay -an "%SRC%"

endlocal