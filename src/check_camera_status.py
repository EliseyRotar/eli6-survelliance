#!/usr/bin/env python3
"""
Quick camera status checker to identify offline cameras
"""

import json
import requests
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def check_camera_status(camera_data, timeout=3):
    """Check if a single camera is accessible"""
    try:
        url, username, password, name, cam_type = camera_data[:5]
        
        if cam_type == "video":
            # Test video stream
            cap = cv2.VideoCapture(url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                return name, "✅ ONLINE", "Video stream accessible"
            else:
                return name, "❌ OFFLINE", "Cannot read video stream"
        else:
            # Test image URL
            auth = (username, password) if username and password else None
            headers = {"User-Agent": "Mozilla/5.0"}
            
            response = requests.get(url, auth=auth, timeout=timeout, headers=headers)
            
            if response.status_code == 200 and len(response.content) > 1000:
                return name, "✅ ONLINE", f"HTTP {response.status_code}, {len(response.content)} bytes"
            elif response.status_code == 401:
                return name, "🔐 AUTH", "Authentication required"
            else:
                return name, "❌ OFFLINE", f"HTTP {response.status_code}, {len(response.content)} bytes"
                
    except Exception as e:
        error_msg = str(e)[:50] + "..." if len(str(e)) > 50 else str(e)
        return name, "❌ ERROR", error_msg

def main():
    print("🔍 Camera Status Checker")
    print("=" * 60)
    
    # Load camera configuration
    with open('camera_config.json', 'r') as f:
        config = json.load(f)
    
    cameras = [cam for cam in config['cameras'] if cam['enabled']]
    print(f"Checking {len(cameras)} cameras...")
    print()
    
    # Check cameras in parallel
    online_count = 0
    offline_count = 0
    auth_count = 0
    error_count = 0
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        # Submit all camera checks
        future_to_camera = {
            executor.submit(check_camera_status, (
                cam['url'], 
                cam.get('username', ''), 
                cam.get('password', ''), 
                cam['name'], 
                cam.get('type', 'image')
            )): i for i, cam in enumerate(cameras)
        }
        
        # Collect results
        results = []
        for future in as_completed(future_to_camera):
            try:
                name, status, details = future.result()
                results.append((name, status, details))
                
                if "ONLINE" in status:
                    online_count += 1
                elif "AUTH" in status:
                    auth_count += 1
                elif "OFFLINE" in status:
                    offline_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                results.append(("Unknown", "❌ ERROR", str(e)))
    
    # Sort results by camera name
    results.sort(key=lambda x: x[0])
    
    # Display results
    print("📊 CAMERA STATUS RESULTS:")
    print("-" * 60)
    for name, status, details in results:
        print(f"{status} {name}")
        if "OFFLINE" in status or "ERROR" in status:
            print(f"    └─ {details}")
    
    print()
    print("📈 SUMMARY:")
    print(f"  ✅ Online: {online_count} cameras")
    print(f"  🔐 Auth Required: {auth_count} cameras")
    print(f"  ❌ Offline: {offline_count} cameras")
    print(f"  ⚠️  Errors: {error_count} cameras")
    print(f"  📊 Total: {len(cameras)} cameras")
    
    success_rate = (online_count + auth_count) / len(cameras) * 100
    print(f"  🎯 Success Rate: {success_rate:.1f}%")
    
    if offline_count > 0 or error_count > 0:
        print()
        print("💡 NOTE: Offline cameras are normal for internet IP cameras.")
        print("   The system will automatically retry with exponential backoff.")

if __name__ == "__main__":
    main()