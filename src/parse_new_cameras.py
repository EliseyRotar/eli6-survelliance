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

print(f"Found {len(existing_ips)} existing unique IPs")
print("Existing IPs:", sorted(list(existing_ips))[:10], "...")

# Raw camera data from user
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
http://2.47.47.117/cgi-bin/faststream.jpg?stream=full&fps=15&rand=441656
{http://185.144.75.107/mjpg/video.mjpg}
http://2.35.32.6:82/record/current.jpg?stream=full&fps=25&rand=825086
http://2.35.32.6:81/control/faststream.jpg?stream=full&fps=25&rand=825086
http://188.12.181.140:82/control/faststream.jpg?stream=full&fps=25&rand=446146
http://188.12.181.140:88/control/faststream.jpg?stream=full&fps=16&rand=914321
http://93.64.78.83:80
http://46.234.223.63:8200/video.mp4?line=1&inst=1&rec=0&buffer_ms=0&rnd=10153
http://77.108.0.46:8083/control/faststream.jpg?stream=full&fps=16&rand=414609
http://79.7.31.219:8090/cgi-bin/faststream.jpg?stream=full&fps=16&rand=790403
http://213.137.36.178/jpg/image.jpg
http://79.7.75.166/cgi-bin/mjpeg?resolution=1280x960&quality=5&page=1768507886060&Language=5
http://77.89.39.134:1024/cgi-bin/faststream.jpg?stream=full&fps=16&rand=396651
http://88.149.182.79:8080/control/faststream.jpg?stream=full&fps=4&rand=523676
http://84.33.89.170:85
http://194.116.34.4/mjpg/video.mjpg
http://79.0.95.68:84/image.jpg
http://94.94.93.50:50000/live/oneshot.html
http://94.94.93.50:50001/live/oneshot.html
http://94.177.176.113:8080/?action=stream
http://77.108.0.46:8081/control/faststream.jpg?stream=full&fps=16&rand=246180
http://37.116.21.2:8083/mjpg/video.mjpg
http://79.3.196.235/cgi-bin/mjpeg
http://77.242.135.139:8082/control/faststream.jpg?stream=full&fps=16&rand=607927
http://77.242.135.139:8083/control/faststream.jpg?stream=full&fps=16&rand=821986
http://77.242.135.139:8084/control/faststream.jpg?stream=full&fps=16&rand=15854
http://2.234.120.231:91/control/faststream.jpg?stream=full&fps=16&rand=759605
http://185.5.196.54:90/control/faststream.jpg?stream=full&fps=12&rand=999599
http://213.182.91.27:8082/ViewerFrame?Resolution=640x480&Quality=Clarity&Size=STD&Language=5&Sound=Enable&Mode=JPEG&RPeriod=3&SendMethod=1&View=Full
http://91.143.192.75/ViewerFrame?Resolution=640x480&Quality=Standard&Size=STD&Language=5&Sound=Enable&Mode=JPEG&RPeriod=3&SendMethod=1&View=Full
http://128.116.187.241:81
http://94.32.86.58:8090
http://91.231.166.180:86/mjpg/video.mjpg
http://91.231.166.180:85/mjpg/video.mjpg
http://185.94.82.113/cgi-bin/faststream.jpg?stream=full&fps=16&rand=635365
http://185.97.122.32:8080/cgi-bin/faststream.jpg?stream=full&fps=16&rand=681968
http://185.124.182.119:80
http://185.87.69.220:8001/snap.jpg?JpegCam=1
http://185.87.69.220:8001/snap.jpg?JpegCam=2
http://185.87.69.220:8001/snap.jpg?JpegCam=3
http://185.87.69.220:8001/snap.jpg?JpegCam=4
http://188.10.94.195:9000/mjpg/video.mjpg
http://91.214.60.215/cgi-bin/faststream.jpg?stream=full&fps=16&rand=281684
http://218.219.214.248:50000/nphMotionJpeg?Resolution=640x480
http://218.219.195.24/nphMotionJpeg?Resolution=640x480
http://221.189.116.218:60001/nphMotionJpeg?Resolution=640x480
"""

print("Starting to parse new cameras...")
# Parse URLs and extract valid cameras
new_cameras = []
company_groups = {}
current_company = None

lines = raw_data.strip().split('\n')
for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Skip shodan, vnc, and non-camera related content
    if any(skip in line.lower() for skip in ['shodan', 'vnc', 'vncviewer', 'tigervnc', 'remmina', 'not supported', 'browser too new', 'house control']):
        continue
    
    # Handle company groupings
    if line.startswith('{'):
        current_company = "Company Group"
        continue
    elif line.endswith('}'):
        current_company = None
        continue
    
    # Extract URLs
    if line.startswith('http'):
        # Clean up URL (remove random parameters)
        url = re.sub(r'[&?]rand=\d+', '', line)
        url = re.sub(r'[&?]page=\d+', '', url)
        
        parsed = urlparse(url)
        ip = parsed.hostname
        
        if not ip:
            continue
            
        # Check for duplicates
        if ip in existing_ips:
            print(f"DUPLICATE FOUND: {ip} - skipping {url}")
            continue
        
        # Determine camera type
        cam_type = "video" if any(vid in url.lower() for vid in ['video.cgi', 'mjpg', 'axis-cgi', 'liveview', 'motion']) else "image"
        
        # Extract credentials if mentioned
        username = ""
        password = ""
        if "admin:admin" in line:
            username = "admin"
            password = "admin"
        elif "admin:12345678" in line:
            username = "admin"
            password = "12345678"
        
        # Determine location from IP ranges (basic geolocation)
        location = "Unknown"
        if ip.startswith('2.') or ip.startswith('77.') or ip.startswith('79.') or ip.startswith('80.') or ip.startswith('82.') or ip.startswith('85.') or ip.startswith('87.') or ip.startswith('88.') or ip.startswith('91.') or ip.startswith('94.') or ip.startswith('185.') or ip.startswith('188.') or ip.startswith('194.') or ip.startswith('212.') or ip.startswith('213.'):
            location = "Europe"
        elif ip.startswith('36.') or ip.startswith('58.') or ip.startswith('61.') or ip.startswith('110.') or ip.startswith('114.') or ip.startswith('115.') or ip.startswith('117.') or ip.startswith('118.') or ip.startswith('119.') or ip.startswith('121.') or ip.startswith('125.') or ip.startswith('153.') or ip.startswith('180.') or ip.startswith('202.') or ip.startswith('210.') or ip.startswith('218.') or ip.startswith('220.') or ip.startswith('221.'):
            location = "Asia"
        elif ip.startswith('24.') or ip.startswith('63.') or ip.startswith('67.') or ip.startswith('70.') or ip.startswith('72.') or ip.startswith('74.') or ip.startswith('96.') or ip.startswith('97.') or ip.startswith('104.') or ip.startswith('128.') or ip.startswith('142.') or ip.startswith('159.') or ip.startswith('166.') or ip.startswith('173.') or ip.startswith('187.') or ip.startswith('199.') or ip.startswith('204.') or ip.startswith('207.') or ip.startswith('208.'):
            location = "USA"
        
        # Company assignment
        company = None
        if current_company:
            if ip.startswith('111.68.118.121'):
                company = "China Multi-Cam Network"
            elif ip.startswith('72.142.24.116'):
                company = "USA Security Systems"
            elif ip.startswith('185.144.75.107'):
                company = "Europe PTZ Cameras"
        
        # Special company detection
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
        
        new_camera = {
            "url": url,
            "username": username,
            "password": password,
            "name": f"Camera {len(existing_cameras) + len(new_cameras) + 1} - {location}",
            "enabled": True,
            "type": cam_type
        }
        
        if company:
            new_camera["company"] = company
            new_camera["name"] = f"Camera {len(existing_cameras) + len(new_cameras) + 1} ({company}) - {location}"
        
        new_cameras.append(new_camera)
        existing_ips.add(ip)  # Add to prevent duplicates within new cameras

print(f"\nFound {len(new_cameras)} new valid cameras")
print(f"Total cameras will be: {len(existing_cameras) + len(new_cameras)}")

# Show first few new cameras
for i, cam in enumerate(new_cameras[:5]):
    print(f"{i+1}. {cam['name']} - {cam['url'][:50]}...")

print(f"... and {len(new_cameras)-5} more cameras")