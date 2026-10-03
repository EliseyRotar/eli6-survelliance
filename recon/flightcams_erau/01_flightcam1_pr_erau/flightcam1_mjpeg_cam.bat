@echo off
REM flightcam1_mjpeg_cam.bat
REM Live MJPEG view of flightcam1.pr.erau.edu (lower-latency, but may lag due to MJPEG bandwidth)
REM Source: AXIS P5415-E PTZ Dome @ Embry-Riddle Aeronautical University, Prescott AZ
REM For smoother playback use flightcam1_h264_cam.bat (transcodes to H.264)

setlocal
set FFPLAY="C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffplay.exe"

echo ============================================
echo  flightcam1.pr.erau.edu  -  MJPEG Live
echo  AXIS P5415-E PTZ  -  Embry-Riddle Aero U
echo  Native MJPEG stream (may lag)
echo  Try flightcam1_h264_cam.bat for smooth
echo ============================================
echo.

%FFPLAY% -hide_banner -loglevel warning -window_title "flightcam1.pr.erau.edu MJPEG" -framedrop -fflags nobuffer -flags low_delay -an "http://flightcam1.pr.erau.edu/mjpg/video.mjpg?resolution=1280x720"

endlocal