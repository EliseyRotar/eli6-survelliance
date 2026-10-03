@echo off
REM Launch the HLS player in default browser.
REM Usage: launch_hls_player.bat "https://example.com/cam/playlist.m3u8"

setlocal
set URL=%~1

if "%URL%"=="" (
  start "" "%~dp0hls_player.html"
) else (
  start "" "file:///%~dp0hls_player.html?url=%URL%"
)
