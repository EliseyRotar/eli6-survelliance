#!/usr/bin/env python3
import json
import re
from urllib.parse import urlparse

# Load existing cameras
with open('camera_config.json', 'r') as f:
    config = json.load(f)

existing_cameras = config['cameras']
existing_ips = set()

# Extract existing IPs for duplicate checking
for cam in existing_cameras:
    parsed = urlparse(cam['url'])
    ip = parsed.hostname
    if ip:
        existing_ips.add(ip)

print(f"Starting with {len(existing_cameras)} existing cameras")

# Complete raw camera data from user
raw_data = """
http://87.139.62.155:81/IMAGE.JPG
http://153.222.169.170:8081/-wvhttp-01-/video.cgi
http://180.57.60.5:8081/-wvhttp-01-/video.cgi
http://61.44.165.156:8040/IMAGE.JPG
http://110.3.32.93:83/IMAGE.JPG
http://110.4.178.160:5986/-wvhttp-01-/video.cgi
http://119.242.104.211:82/IMAGE.JPG
http://125.199.56.127:81/IMAGE.JPG
http://62.215.52.101:80
{http://111.68.118.121:11082/video.cgi
http://111.68.118.121:12412/video.cgi
http://111.68.118.121:12410/video.cgi
http://111.68.118.121:12406/video.cgi
http://111.68.118.121:12404/video.cgi
http://111.68.118.121:12203/video.cgi
http://111.68.118.121:11434/video.cgi
http://111.68.118.121:11210/video.cgi
http://111.68.118.121:11082/video.cgi
http://111.68.118.121:10106/video.cgi
http://111.68.118.121:9113/video.cgi
http://111.68.118.121:9112/video.cgi
http://111.68.118.121:9103/video.cgi}
{http://72.142.24.116:10001/camera/index.html#/video
http://72.142.24.116:10004/camera/index.html#/video
http://72.142.24.116:10005/camera/index.html#/video
http://72.142.24.116:10006/camera/index.html#/video
http://72.142.24.116:10007/camera/index.html#/video
http://72.142.24.116:10009/camera/index.html#/video
http://72.142.24.116:10010/camera/index.html#/video
http://72.142.24.116:10011/camera/index.html#/video
http://72.142.24.116:10012/camera/index.html#/video
http://72.142.24.116:10013/camera/index.html#/video
http://72.142.24.116:10014/camera/index.html#/video}
http://118.243.218.106:81/portal/js_pane/131?action=controls.Restore
http://117.102.180.203:50000/GetImage.cgi
http://85.229.58.96/
http://62.2.85.226:8051/mjpg/video.mjpg
http://62.2.85.226:8052/mjpg/video.mjpg
http://94.125.55.139/
http://79.52.47.7:3791/eng/liveView.cgi
http://79.52.47.7:9200/eng/liveView.cgi
http://188.193.201.244:84/web/ptz.html
http://121.123.62.177/image
http://79.0.95.68:85/video.cgi
http://79.52.47.7:11211/eng/liveView.cgi
http://79.52.47.7:4321/eng/liveView.cgi
http://36.55.48.9:5001/-wvhttp-01-/video.cgi
http://110.4.178.160:5001/-wvhttp-01-/video.cgi
http://61.196.233.106:5001/-wvhttp-01-/video.cgi
http://115.65.166.141:5001/cgi-bin/camera
http://114.162.235.129:8089/cgi-bin/camera
http://37.123.131.43:96/video.cgi
http://104.158.1.86:9002/video.cgi
http://82.64.32.236/
http://176.139.112.250/
http://84.59.205.112:10000/GetImage.cgi?CH=0
http://117.102.180.203:50000/GetImage.cgi?CH=0
http://67.82.213.63:8081/GetImage.cgi?CH=0
http://220.128.115.31:8085/GetImage.cgi?CH=0
http://93.38.57.20:8080/ViewerFrame?Resolution=640x480&Quality=Standard&Size=STD&Language=5&Sound=Enable&Mode=JPEG&RPeriod=3&SendMethod=1&View=Full
http://194.32.174.72:80
http://2.115.171.20/mjpg/video.mjpg
http://2.47.47.117/cgi-bin/faststream.jpg?stream=full&fps=15
{http://185.144.75.107/mjpg/video.mjpg}
http://2.35.32.6:82/record/current.jpg?stream=full&fps=25
http://2.35.32.6:81/control/faststream.jpg?stream=full&fps=25
http://188.12.181.140:82/control/faststream.jpg?stream=full&fps=25
http://188.12.181.140:88/control/faststream.jpg?stream=full&fps=16
http://93.64.78.83:80
http://46.234.223.63:8200/video.mp4?line=1&inst=1&rec=0&buffer_ms=0
http://77.108.0.46:8083/control/faststream.jpg?stream=full&fps=16
http://79.7.31.219:8090/cgi-bin/faststream.jpg?stream=full&fps=16
http://213.137.36.178/jpg/image.jpg
http://79.7.75.166/cgi-bin/mjpeg?resolution=1280x960&quality=5
http://77.89.39.134:1024/cgi-bin/faststream.jpg?stream=full&fps=16
http://88.149.182.79:8080/control/faststream.jpg?stream=full&fps=4
http://84.33.89.170:85
http://194.116.34.4/mjpg/video.mjpg
http://79.0.95.68:84/image.jpg
http://94.94.93.50:50000/live/oneshot.html
http://94.94.93.50:50001/live/oneshot.html
http://94.177.176.113:8080/?action=stream
http://77.108.0.46:8081/control/faststream.jpg?stream=full&fps=16
http://37.116.21.2:8083/mjpg/video.mjpg
http://79.3.196.235/cgi-bin/mjpeg
http://77.242.135.139:8082/control/faststream.jpg?stream=full&fps=16
http://77.242.135.139:8083/control/faststream.jpg?stream=full&fps=16
http://77.242.135.139:8084/control/faststream.jpg?stream=full&fps=16
http://2.234.120.231:91/control/faststream.jpg?stream=full&fps=16
http://185.5.196.54:90/control/faststream.jpg?stream=full&fps=12
http://213.182.91.27:8082/ViewerFrame?Resolution=640x480&Quality=Clarity&Size=STD&Language=5&Sound=Enable&Mode=JPEG&RPeriod=3&SendMethod=1&View=Full
http://91.143.192.75/ViewerFrame?Resolution=640x480&Quality=Standard&Size=STD&Language=5&Sound=Enable&Mode=JPEG&RPeriod=3&SendMethod=1&View=Full
http://128.116.187.241:81 admin:admin
http://94.32.86.58:8090 admin:12345678
http://91.231.166.180:86/mjpg/video.mjpg
http://91.231.166.180:85/mjpg/video.mjpg
http://185.94.82.113/cgi-bin/faststream.jpg?stream=full&fps=16
http://185.97.122.32:8080/cgi-bin/faststream.jpg?stream=full&fps=16
http://185.124.182.119:80
http://185.87.69.220:8001/snap.jpg?JpegCam=1
http://185.87.69.220:8001/snap.jpg?JpegCam=2
http://185.87.69.220:8001/snap.jpg?JpegCam=3
http://185.87.69.220:8001/snap.jpg?JpegCam=4
http://188.10.94.195:9000/mjpg/video.mjpg
http://91.214.60.215/cgi-bin/faststream.jpg?stream=full&fps=16
http://218.219.214.248:50000/nphMotionJpeg?Resolution=640x480
http://218.219.195.24/nphMotionJpeg?Resolution=640x480
http://221.189.116.218:60001/nphMotionJpeg?Resolution=640x480
http://86.63.39.58:8080/axis-cgi/mjpg/video.cgi
http://83.48.75.113:8320/axis-cgi/mjpg/video.cgi
http://213.3.30.80:6001/axis-cgi/mjpg/video.cgi
http://213.123.122.163:1087/axis-cgi/mjpg/video.cgi
http://24.134.3.9:80/axis-cgi/mjpg/video.cgi
http://80.75.114.18:80/axis-cgi/mjpg/video.cgi
http://82.127.206.236:80/axis-cgi/mjpg/video.cgi
http://80.254.191.189:8008/axis-cgi/mjpg/video.cgi
http://77.110.245.165:80/axis-cgi/mjpg/video.cgi
http://85.196.146.82:3337/axis-cgi/mjpg/video.cgi
http://79.161.6.126:9092/axis-cgi/mjpg/video.cgi
http://185.108.19.197:10800/axis-cgi/mjpg/video.cgi
http://142.0.109.159:80/axis-cgi/mjpg/video.cgi
http://74.95.172.65:8100/axis-cgi/mjpg/video.cgi
http://77.60.226.189:8012/control/userimage.html
http://212.26.235.210:80/axis-cgi/mjpg/video.cgi
http://185.74.192.88:85/axis-cgi/mjpg/video.cgi
http://194.94.76.134:80/control/userimage.html
http://80.245.224.153:80/control/userimage.html
http://213.5.145.4:80/control/userimage.html
http://109.247.15.178:6001/mjpg/video.mjpg
http://208.124.240.178:80/axis-cgi/mjpg/video.cgi
http://82.77.203.219:8080/control/userimage.html
http://61.115.78.205:80/control/userimage.html
http://185.226.233.55:8001/axis-cgi/mjpg/video.cgi
http://74.113.182.246:9600/axis-cgi/mjpg/video.cgi
http://187.141.142.149:8010/axis-cgi/mjpg/video.cgi
http://63.42.216.178:8088/axis-cgi/mjpg/video.cgi
http://194.44.38.196:8083/view/viewer_index.shtml?id=493
http://77.89.48.20:8003/cgi-bin/faststream.jpg?stream=full&fps=25
http://89.97.231.70:8083/control/userimage.html
http://195.32.24.180:1024/mjpg/video.mjpg
http://173.165.152.129:8011/axis-cgi/mjpg/video.cgi
http://77.106.164.66:80/#view
http://72.253.153.216:81/view/index.shtml
http://115.179.100.76:8080/CgiStart?page=Single&Language=0
http://185.80.208.125:80/#view
http://14.160.87.118:82/live/index.html?Language=0
http://58.94.98.44:80/CgiStart?page=Single&Language=0
http://212.67.236.61:80/mjpg/video.mjpg
http://210.248.127.20:80/CgiStart?page=Single&Language=0
http://213.98.123.127:8050/cgi-bin/faststream.jpg?stream=full&fps=25
http://153.156.235.87:80/cgi-bin/faststream.jpg?stream=full&fps=25
http://218.45.173.232:8000/live/index.html?Language=1&ViewMode=pull
http://91.214.62.226:80/control/userimage.html
http://193.90.139.222:33445/mjpg/video.mjpg
http://193.214.75.118:80/mjpg/video.mjpg
http://63.41.124.38:80/control/userimage.html
http://91.133.105.85:50050/cgi-bin/faststream.jpg?stream=full&fps=25
http://87.224.70.147:1884/mjpg/video.mjpg
http://77.110.203.114:82/mjpg/video.mjpg
http://85.8.92.1:80/control/userimage.html
http://87.139.9.247:80/#view
http://50.197.223.169:80/#view
http://77.242.135.139:8082/cgi-bin/faststream.jpg?stream=full&fps=25
http://109.236.111.203:80/mjpg/video.mjpg
http://166.151.98.221:7001/cgi-bin/faststream.jpg?stream=full&fps=25
http://221.189.0.181:80/cgi-bin/guestimage.html
http://50.197.223.170:80/#view
http://97.68.104.34:80/aca/index.html#view
http://194.106.254.98:1080/control/userimage.html
http://77.222.181.11:8080/mjpg/video.mjpg
http://220.233.144.165:8888/mjpg/video.mjpg
http://204.106.237.68:88/mjpg/1/video.mjpg
http://63.142.190.238:6120/mjpg/video.mjpg
http://166.149.155.73:7001/cgi-bin/faststream.jpg?stream=full&fps=25
http://213.236.250.78:80/mjpg/video.mjpg
http://80.14.201.251:8010/mjpg/video.mjpg
http://83.136.176.101:10013/mjpg/video.mjpg
http://153.156.82.99:80/nphMotionJpeg
http://89.106.109.144:12060/mjpg/video.mjpg
http://212.67.231.233:80/mjpg/video.mjpg
http://78.31.82.246:80/mjpg/video.mjpg
http://67.53.46.161:65123/mjpg/video.mjpg
http://213.3.30.80:6001/mjpg/video.mjpg
http://159.130.70.206:80/mjpg/video.mjpg
http://104.243.223.162:8082/mjpg/video.mjpg
http://212.170.100.189:80/mjpg/video.mjpg
http://70.63.123.20:80/mjpg/1/video.mjpg
http://109.109.87.147:80/mjpg/video.mjpg
http://62.214.4.38:80/mjpg/video.mjpg
http://212.41.248.38:80/cgi-bin/hugesize.jpg?camera=4&motion=0
http://31.132.43.196:81/cgi-bin/fullsize.jpg?camera=2&motion=0
http://61.211.241.239:80/nphMotionJpeg?Resolution=640x480
http://37.128.212.84:80/mjpg/video.mjpg
http://31.132.43.196:81/cgi-bin/fullsize.jpg?camera=3&motion=0
http://46.14.58.189:80/mjpg/video.mjpg
http://82.134.72.194:80/mjpg/video.mjpg
http://78.186.26.188:80/mjpg/1/video.mjpg
http://81.167.114.67:84/mjpg/video.mjpg
http://212.41.248.38:80/cgi-bin/hugesize.jpg?camera=1&motion=0
http://202.174.60.121:80/-wvhttp-01-/image.cgi
http://199.104.253.4:80/mjpg/video.mjpg
http://212.41.248.38:80/cgi-bin/hugesize.jpg?camera=3&motion=0
barbadillodeherreros.dyndns.org:9001/axis-cgi/mjpg/video.cgi
http://207.194.15.97:80/mjpg/video.mjpg
webcam.anklam.de:80/axis-cgi/mjpg/video.cgi
http://185.49.169.66:1024/control/faststream.jpg?stream=full&fps=16
http://85.220.149.7:80/cgi-bin/guestimage.html
minigolf-paderborn.spdns.de:86/axis-cgi/mjpg/video.cgi
cam-mckeldin-eastview.umd.edu:80/axis-cgi/mjpg/video.cgi
live1.tusten.no:8080/axis-cgi/mjpg/video.cgi
webcam.fairharbormarina.com:80/nphMotionJpeg?Resolution=640x480
chalet-chuenis.internet-box.ch:80/axis-cgi/mjpg/video.cgi
http://96.91.10.219:80/mjpg/1/video.mjpg
montfarlagne.tacticddns.com:8081/axis-cgi/mjpg/video.cgi
shimamaki-camera.aa0.netvolante.jp:8001/nphMotionJpeg?Resolution=320x240
oceanmist.ddns.net:8084/axis-cgi/mjpg/video.cgi
webcam2.vilhelmina.se:80/axis-cgi/mjpg/video.cgi
renzo.dyndns.tv:80/mjpg/video.mjpg
museumhallevik2.ddns.net:9501/axis-cgi/mjpg/video.cgi
webcam1.vilhelmina.se:80/axis-cgi/mjpg/video.cgi
webcam4.vilhelmina.se:80/axis-cgi/mjpg/video.cgi
captainsbounty.dnsalias.com:80/mjpg/video.mjpg
webcam2.minden-wlan.de:10000/axis-cgi/mjpg/video.cgi
webcam3.vilhelmina.se:80/axis-cgi/mjpg/video.cgi
nasukashi.aa0.netvolante.jp:8192/axis-cgi/mjpg/video.cgi
mittaghorn.mine.nu:80/mjpg/video.mjpg
lafarge.sarl2e.fr:3100/mjpg/video.mjpg
eyc.synology.me:10001/mjpg/video.mjpg
camera.sissiboo.com:86/mjpg/video.mjpg
holmen.tplinkdns.com:80/mjpg/video.mjpg
https://webcam.vliegveldzeeland.nl:7171/axis-cgi/mjpg/video.cgi
https://webcamrm.loodswezen.nl:443/cgi-bin/faststream.jpg?stream=full&fps=25
yakumo-fishing-circle.aa0.netvolante.jp:80/nphMotionJpeg?Resolution=640x480
kamera.mikulov.cz:8888/mjpg/video.mjpg
webcam.agf-bw.info:8092/mjpg/video.mjpg
cam0819917993.ddns.komatsuelec.co.jp:80/nphMotionJpeg?Resolution=640x480&Quality=Clarity
camera6.city.satsumasendai.lg.jp:80/-wvhttp-01-/image.cgi
cam6284208.miemasu.net:80/nphMotionJpeg
yukijinjya.st.wakwak.ne.jp:80/control/userimage.html
hoybakken.dyndns.org:9876/mjpg/video.mjpg
honjin1.miemasu.net:80/nphMotionJpeg
casamellow.dyndns.org:80/mjpg/video.mjpg
abcmaingate.dyndns.info:8081/mjpg/video.mjpg
plassenburg-blick.iyxdveyshavdrmjx.myfritz.net:80/cgi-bin/faststream.jpg?stream=full&fps=25
skycam.sebewainggigvillage.com:80/mjpg/video.mjpg
mbr-cam.dyndns.org:8088/mjpg/video.mjpg
koupaliste.velkeopatovice.cz:80/mjpg/video.mjpg
alatsaeroclub.ddns.net:85/mjpg/video.mjpg
myrafjell.sodvin.no:80/mjpg/video.mjpg
ferienpenthouse34.spdns.de:4601/control/userimage.html
https://ipcam-1.byrd.osu.edu:443/mjpg/video.mjpg
mmb.aa1.netvolante.jp:1025/mjpg/video.mjpg?resolution=640x360&compression=50
adlerschanze.selfhost.eu:80/control/userimage.html
amrescam1.homeip.net:88/control/userimage.html
mmb.aa1.netvolante.jp:1025/mjpg/video.mjpg?resolution=640x360
view.dikemes.edu.gr:80/mjpg/video.mjpg
iyashi-webcam.st.wakwak.ne.jp:80/nphMotionJpeg?Resolution=320x240&Quality=Standard
e1480d3b88f7.sn.mynetname.net:91/mjpg/video.mjpg
www.groto.dy.fi:80/mjpg/video.mjpg
flightcam3.pr.erau.edu:80/view/view.shtml
"""

def get_location_from_ip(ip):
    """Determine location based on IP address ranges"""
    if ip.startswith(('2.', '31.', '37.', '46.', '77.', '78.', '79.', '80.', '81.', '82.', '83.', '84.', '85.', '86.', '87.', '88.', '89.', '91.', '93.', '94.', '109.', '128.', '142.', '153.', '159.', '173.', '185.', '188.', '193.', '194.', '195.', '212.', '213.')):
        return "Europe"
    elif ip.startswith(('14.', '36.', '58.', '61.', '110.', '114.', '115.', '117.', '118.', '119.', '121.', '125.', '153.', '180.', '202.', '210.', '218.', '220.', '221.')):
        return "Asia"
    elif ip.startswith(('24.', '50.', '63.', '67.', '70.', '72.', '74.', '96.', '97.', '104.', '166.', '187.', '199.', '204.', '207.', '208.')):
        return "USA"
    else:
        return "Unknown"

def determine_camera_type(url):
    """Determine if camera is video or image based on URL"""
    video_indicators = ['video.cgi', 'mjpg', 'axis-cgi', 'liveview', 'motion', 'stream', 'cam_', '.mp4']
    image_indicators = ['image.jpg', 'snap.jpg', 'getimage', 'oneshot', 'userimage']
    
    url_lower = url.lower()
    
    if any(indicator in url_lower for indicator in video_indicators):
        return "video"
    elif any(indicator in url_lower for indicator in image_indicators):
        return "image"
    else:
        # Default to image for simple URLs
        return "image"

# Parse URLs and extract valid cameras
new_cameras = []
current_company = None
company_counter = {}

lines = raw_data.strip().split('\n')
for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Skip unwanted content
    if any(skip in line.lower() for skip in ['shodan', 'vnc', 'vncviewer', 'tigervnc', 'remmina', 'not supported', 'browser too new', 'house control', 'option 1:', 'option 2:', 'download', 'protocol:', 'server:']):
        continue
    
    # Handle company groupings
    if line.startswith('{'):
        current_company = "Company Group"
        continue
    elif line.endswith('}'):
        current_company = None
        continue
    
    # Extract credentials from line
    username = ""
    password = ""
    if "admin:admin" in line:
        username = "admin"
        password = "admin"
        line = line.replace(" admin:admin", "")
    elif "admin:12345678" in line:
        username = "admin"
        password = "12345678"
        line = line.replace(" admin:12345678", "")
    
    # Extract URL
    url = line.strip()
    
    # Handle domain names without http://
    if not url.startswith('http') and ('.' in url) and (':' in url):
        url = 'http://' + url
    
    if not url.startswith('http'):
        continue
    
    # Clean up URL (remove random parameters)
    url = re.sub(r'[&?]rand=\d+', '', url)
    url = re.sub(r'[&?]page=\d+', '', url)
    url = re.sub(r'&Quality=\w+', '', url)
    
    parsed = urlparse(url)
    ip = parsed.hostname
    
    if not ip:
        continue
        
    # Check for duplicates
    if ip in existing_ips:
        continue
    
    # Determine camera type
    cam_type = determine_camera_type(url)
    
    # Determine location
    location = get_location_from_ip(ip)
    
    # Company assignment based on IP patterns and groupings
    company = None
    if current_company:
        if ip.startswith('111.68.118.121'):
            company = "China Multi-Cam Network"
        elif ip.startswith('72.142.24.116'):
            company = "USA Security Systems"
        elif ip.startswith('185.144.75.107'):
            company = "Europe PTZ Cameras"
    
    # Special company detection based on IP patterns
    if ip.startswith('185.87.69.220'):
        company = "Multi-Channel Security"
    elif ip.startswith('62.2.85.226'):
        company = "Netherlands Cams"
    elif ip.startswith('79.52.47.7'):
        company = "Turkey Multi-Cam"
    elif ip.startswith('77.242.135.139'):
        company = "Europe Multi-Port"
    elif ip.startswith('94.94.93.50'):
        company = "Live Stream Systems"
    elif ip.startswith('91.231.166.180'):
        company = "Dual Camera Setup"
    elif ip.startswith('2.35.32.6') or ip.startswith('188.12.181.140'):
        company = "Europe Surveillance"
    elif ip.startswith('77.108.0.46'):
        company = "Europe Multi-Port"
    elif ip.startswith('212.41.248.38') or ip.startswith('31.132.43.196'):
        company = "Multi-Camera Array"
    elif 'vilhelmina.se' in url:
        company = "Vilhelmina Municipality"
    elif any(domain in url for domain in ['dyndns', 'ddns', 'netvolante', 'myfritz']):
        company = "Dynamic DNS Cameras"
    elif 'axis-cgi' in url:
        company = "Axis Communications"
    
    # Create camera entry
    camera_num = len(existing_cameras) + len(new_cameras) + 1
    
    new_camera = {
        "url": url,
        "username": username,
        "password": password,
        "name": f"Camera {camera_num} - {location}",
        "enabled": True,
        "type": cam_type
    }
    
    if company:
        new_camera["company"] = company
        new_camera["name"] = f"Camera {camera_num} ({company}) - {location}"
    
    new_cameras.append(new_camera)
    existing_ips.add(ip)  # Add to prevent duplicates within new cameras

print(f"Found {len(new_cameras)} new valid cameras")
print(f"Total cameras will be: {len(existing_cameras) + len(new_cameras)}")

# Add new cameras to config
config['cameras'].extend(new_cameras)

# Save updated configuration
with open('camera_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print(f"\n✅ Successfully added {len(new_cameras)} new cameras!")
print(f"📹 Total cameras now: {len(config['cameras'])}")

# Show summary of new cameras
print(f"\n📊 NEW CAMERAS SUMMARY:")
print(f"🎥 Video cameras: {sum(1 for cam in new_cameras if cam['type'] == 'video')}")
print(f"📷 Image cameras: {sum(1 for cam in new_cameras if cam['type'] == 'image')}")
print(f"🏢 Company cameras: {sum(1 for cam in new_cameras if 'company' in cam)}")
print(f"🔐 Authenticated cameras: {sum(1 for cam in new_cameras if cam['username'])}")

# Show first few new cameras
print(f"\n🆕 FIRST 5 NEW CAMERAS:")
for i, cam in enumerate(new_cameras[:5]):
    auth_info = f" ({cam['username']}:{cam['password']})" if cam['username'] else ""
    company_info = f" - {cam['company']}" if 'company' in cam else ""
    print(f"{i+1}. {cam['name']}{company_info} [{cam['type']}]{auth_info}")
    print(f"   {cam['url'][:80]}...")

if len(new_cameras) > 5:
    print(f"... and {len(new_cameras)-5} more cameras")