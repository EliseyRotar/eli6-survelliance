@echo off
REM flightcam1_h264_cam.bat
REM Live H.264 transcoded view of flightcam1.pr.erau.edu
REM Source: AXIS P5415-E PTZ Dome @ Embry-Riddle Aeronautical University, Prescott AZ
REM Transcodes MJPEG (which lags) into smooth H.264 using local ffmpeg
REM The native H.264 is only available via RTSP (port 554, firewalled externally).
REM Local transcoding gives buttery-smooth 25fps H.264 playback in ffplay.
REM PTZ is anonymous-controllable. See docs/AXIS_FLIGHTCAM1_P5415E.md

setlocal
set FFMPEG="C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
set FFPLAY="C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffplay.exe"
set SRC=http://flightcam1.pr.erau.edu/mjpg/video.mjpg?resolution=1280x720

echo ============================================
echo  flightcam1.pr.erau.edu  -  H.264 Live
echo  AXIS P5415-E PTZ  -  Embry-Riddle Aero U
echo  MJPEG source -> local H.264 transcode
echo  1280x720 @ 25fps  -  ultrafast + zerolatency
echo ============================================
echo.

REM Use ffmpeg to transcode MJPEG -> H.264, then pipe to ffplay for smooth display.
REM -preset ultrafast + -tune zerolatency = minimal encode delay
REM -r 25 = smooth playback
REM -an = no audio
%FFMPEG% -hide_banner -loglevel warning -user_agent "Mozilla/5.0" -i "%SRC%" -r 25 -vf "scale=1280:720" -c:v libx264 -preset ultrafast -tune zerolatency -crf 28 -an -f matroska - 2>nul | %FFPLAY% -hide_banner -loglevel warning -window_title "flightcam1.pr.erau.edu H.264 (transcoded)" -framedrop - -

endlocal