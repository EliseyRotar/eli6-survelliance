@echo off
REM wc2_dartmouth_h264_cam.bat
REM Live H.264 transcoded view of wc2.dartmouth.edu (Baker Library AXIS 221 camera)
REM AXIS 221 is OLD (2005) - no native H.264 support. We transcode MJPEG locally.
REM Original cam: AXIS 221 Network Camera, Dartmouth College

setlocal
set FFMPEG="C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
set FFPLAY="C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffplay.exe"
set SRC=http://wc2.dartmouth.edu/mjpg/video.mjpg?resolution=640x480

echo ============================================
echo  wc2.dartmouth.edu  -  H.264 Live (transcoded)
echo  AXIS 221 Network Camera (Baker Library)
echo  MJPEG source -> local H.264 transcode
echo  Dartmouth College, Hanover NH
echo ============================================
echo.

REM AXIS 221 streams MJPEG slowly (~44 KB/s). Use 640x480 with listen_timeout to prevent ffmpeg hang.
%FFMPEG% -hide_banner -loglevel warning -user_agent "Mozilla/5.0" -listen_timeout 4000000 -fflags nobuffer+genpts -flags low_delay -i "%SRC%" -r 25 -vf "scale=640:480" -c:v libx264 -preset ultrafast -tune zerolatency -crf 28 -an -f matroska - 2>nul | %FFPLAY% -hide_banner -loglevel warning -window_title "wc2.dartmouth.edu H.264 (transcoded)" -framedrop -fflags nobuffer - -

endlocal