#!/usr/bin/env python3
import json
import sys
from urllib.parse import urlparse

def extract_working_cameras(json_data):
    """Extract working camera URLs and format them"""
    working_urls = []
    
    for camera in json_data:
        if camera['status'] == 'online':
            url = camera['url']
            parsed = urlparse(url)
            
            # Format: IP:PORT/path
            if parsed.port:
                formatted = f"{parsed.hostname}:{parsed.port}{parsed.path}"
            else:
                # Default ports
                port = 443 if parsed.scheme == 'https' else 80
                formatted = f"{parsed.hostname}:{port}{parsed.path}"
            
            # Add query parameters if they exist
            if parsed.query:
                formatted += f"?{parsed.query}"
                
            working_urls.append(formatted)
    
    return working_urls

# Read the JSON data from the provided string
json_string = '''[{"url": "http://80.28.111.68:82/axis-cgi/mjpg/video.cgi","status": "connection_error","response_code": null,"response_time": null,"content_type": null,"content_length": null,"error": "Connection failed","timestamp": "2026-01-15T22:04:16.495182"},{"url": "http://213.3.30.80:6001/axis-cgi/mjpg/video.cgi","status": "online","response_code": 200,"response_time": 0.149,"content_type": "multipart/x-mixed-replace; boundary=myboundary","content_length": "unknown","error": null,"timestamp": "2026-01-15T22:04:16.477108"}]'''

# Parse and extract
data = json.loads(json_string)
working_cameras = extract_working_cameras(data)

for camera in working_cameras:
    print(camera)