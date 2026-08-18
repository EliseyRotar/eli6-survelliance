#!/bin/zsh

# ---- HARD FIX PATH ----
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"
CURL="/usr/bin/curl"

echo
echo "📷 IP Camera Scanner"
echo "===================="
echo

# ---- INPUTS (with defaults) ----
read "IP?🌐 Camera IP (default: 185.73.190.212): "
IP=${IP:-185.73.190.212}

read "USER?👤 Username (default: user): "
USER=${USER:-user}

read "PASS?🔑 Password (default: user): "
PASS=${PASS:-user}

BASE_URL="http://${IP}"

echo
echo "🔍 Scanning $BASE_URL"
echo "---------------------------------"
echo

# ---- SNAP + STREAM PATHS ----
PATHS=(
  # snapshots
  "/web/tmpfs/snap.jpg"
  "/tmpfs/snap.jpg"
  "/snap.jpg"
  "/snapshot.jpg"
  "/image.jpg"
  "/jpg/image.jpg"

  # cgi snapshots
  "/cgi-bin/snapshot.cgi"
  "/cgi-bin/snap.cgi"
  "/cgi-bin/hi3510/snap.cgi"
  "/cgi-bin/hi3510/tmpfs/snap.jpg"
  "/cgi-bin/currentpic.cgi"

  # mjpeg / video
  "/video.cgi"
  "/videostream.cgi"
  "/mjpeg.cgi"
  "/cgi-bin/mjpeg.cgi"
  "/cgi-bin/video.cgi"
  "/cgi-bin/stream.cgi"
  "/cgi-bin/hi3510/video.cgi"
  "/cgi-bin/hi3510/mjpeg.cgi"
  "/cgi-bin/hi3510/stream.cgi"

  # random OEM stuff
  "/web/video.cgi"
  "/web/mjpeg.cgi"
  "/live/ch0"
  "/live/ch1"
)

FOUND=0
RTSP_FOUND=0

for path in "${PATHS[@]}"; do
  URL="${BASE_URL}${path}"
  echo "➡️  $URL"

  STATUS=$($CURL -s -o /dev/null -w "%{http_code}" \
    -u "${USER}:${PASS}" \
    -H "User-Agent: Mozilla/5.0" \
    "$URL")

  if [[ "$STATUS" == "200" ]]; then
    echo "   ✅ FOUND"
    FOUND=1
  else
    echo "   ❌ $STATUS"
  fi
  echo
done

# ---- RTSP STREAMS ----
echo "📡 RTSP STREAM TESTING"
echo "----------------------"

# Check available tools
FFPROBE=$(which ffprobe 2>/dev/null)
CURL_RTSP=$(which curl 2>/dev/null)

if [[ -z "$FFPROBE" && -z "$CURL_RTSP" ]]; then
  echo "⚠️  No RTSP testing tools found (need ffmpeg or curl)"
  echo "   Install: sudo apt install ffmpeg"
  echo "   Manual test: mpv rtsp://${USER}:${PASS}@${IP}:554/stream1"
else
  # Test different RTSP ports first
  RTSP_PORTS=(554 8554 1935 88)
  
  RTSP_PATHS=(
    "/stream1"
    "/stream2" 
    "/h264"
    "/live"
    "/ch0"
    "/ch1"
    "/video1"
    "/video2"
    "/cam/realmonitor?channel=1&subtype=0"
    "/onvif1"
    "/onvif2"
    "/axis-media/media.amp"
    "/MediaInput/h264"
    "/MediaInput/mpeg4"
    "/11"
    "/12"
    "/1"
    "/2"
    ""
  )

  RTSP_FOUND=0
  
  # First, check if RTSP port is open
  echo "🔍 Checking RTSP ports..."
  for port in "${RTSP_PORTS[@]}"; do
    echo -n "   Port $port: "
    timeout 3 bash -c "</dev/tcp/${IP}/${port}" 2>/dev/null
    if [[ $? -eq 0 ]]; then
      echo "✅ OPEN"
      RTSP_PORT=$port
      break
    else
      echo "❌ closed"
    fi
  done
  
  if [[ -z "$RTSP_PORT" ]]; then
    echo "⚠️  No RTSP ports responding, trying default 554 anyway..."
    RTSP_PORT=554
  fi
  
  echo
  echo "🎥 Testing streams on port $RTSP_PORT..."
  
  for rtsp_path in "${RTSP_PATHS[@]}"; do
    RTSP_URL="rtsp://${USER}:${PASS}@${IP}:${RTSP_PORT}${rtsp_path}"
    echo "➡️  $RTSP_URL"
    
    # Try multiple methods
    SUCCESS=0
    
    # Method 1: ffprobe (most reliable)
    if [[ -n "$FFPROBE" ]]; then
      timeout 8 $FFPROBE -v quiet -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$RTSP_URL" >/dev/null 2>&1
      if [[ $? -eq 0 ]]; then
        SUCCESS=1
      fi
    fi
    
    # Method 2: curl RTSP DESCRIBE (faster, less reliable)
    if [[ $SUCCESS -eq 0 && -n "$CURL_RTSP" ]]; then
      timeout 5 curl -s --rtsp-request DESCRIBE -u "${USER}:${PASS}" "$RTSP_URL" >/dev/null 2>&1
      if [[ $? -eq 0 ]]; then
        SUCCESS=1
      fi
    fi
    
    # Method 3: Basic TCP connection test
    if [[ $SUCCESS -eq 0 ]]; then
      timeout 3 bash -c "echo 'DESCRIBE ${rtsp_path} RTSP/1.0' | nc ${IP} ${RTSP_PORT}" >/dev/null 2>&1
      if [[ $? -eq 0 ]]; then
        echo "   🔶 TCP responds (might be RTSP)"
      fi
    fi
    
    if [[ $SUCCESS -eq 1 ]]; then
      echo "   ✅ RTSP STREAM WORKING"
      echo "   🎬 Play with: mpv \"$RTSP_URL\""
      echo "   📱 VLC: vlc \"$RTSP_URL\""
      RTSP_FOUND=1
    else
      echo "   ❌ No response/timeout"
    fi
    echo
  done
  
  [[ "$RTSP_FOUND" == "0" ]] && echo "⚠️  No working RTSP streams found"
fi

echo

[[ "$FOUND" == "0" && "$RTSP_FOUND" == "0" ]] && echo "❌ No working streams found on this camera"

echo "Done."
