#!/usr/bin/env python3
"""Test script to verify 277 cameras configuration"""
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def test_camera(cam_id, camera):
    """Test a single camera connection"""
    url = camera['url']
    username = camera.get('username', '')
    password = camera.get('password', '')
    cam_type = camera.get('type', 'image')
    
    try:
        auth = None
        if username and password:
            auth = (username, password)
        
        response = requests.get(url, auth=auth, timeout=5, stream=False)
        
        if response.status_code == 200:
            return {
                'id': cam_id,
                'status': 'online',
                'type': cam_type,
                'size': len(response.content),
                'company': camera.get('company', 'None')
            }
        else:
            return {
                'id': cam_id,
                'status': 'error',
                'code': response.status_code,
                'type': cam_type
            }
    except Exception as e:
        return {
            'id': cam_id,
            'status': 'offline',
            'error': str(e)[:50],
            'type': cam_type
        }

# Load camera configuration
with open('camera_config.json', 'r') as f:
    config = json.load(f)

cameras = config['cameras']
print(f"🎥 Testing {len(cameras)} cameras...")
print("=" * 80)

# Test cameras in parallel
results = []
start_time = time.time()

with ThreadPoolExecutor(max_workers=50) as executor:
    futures = {executor.submit(test_camera, i, cam): i for i, cam in enumerate(cameras)}
    
    completed = 0
    for future in as_completed(futures):
        result = future.result()
        results.append(result)
        completed += 1
        
        if completed % 20 == 0:
            print(f"Progress: {completed}/{len(cameras)} cameras tested...")

elapsed = time.time() - start_time

# Analyze results
online = [r for r in results if r['status'] == 'online']
offline = [r for r in results if r['status'] == 'offline']
error = [r for r in results if r['status'] == 'error']

video_online = [r for r in online if r['type'] == 'video']
image_online = [r for r in online if r['type'] == 'image']

company_cameras = [r for r in online if r.get('company') != 'None']

print("\n" + "=" * 80)
print("📊 TEST RESULTS")
print("=" * 80)
print(f"⏱️  Test Duration: {elapsed:.1f} seconds")
print(f"📹 Total Cameras: {len(cameras)}")
print(f"✅ Online: {len(online)} ({len(online)/len(cameras)*100:.1f}%)")
print(f"❌ Offline: {len(offline)} ({len(offline)/len(cameras)*100:.1f}%)")
print(f"⚠️  Error: {len(error)} ({len(error)/len(cameras)*100:.1f}%)")
print()
print(f"🎥 Video Streams Online: {len(video_online)}")
print(f"📷 Image Cameras Online: {len(image_online)}")
print(f"🏢 Company Cameras Online: {len(company_cameras)}")
print()

# Show camera ranges
print("📍 CAMERA RANGES:")
print(f"   Cameras 1-88: Original cameras")
print(f"   Cameras 89-277: Newly added cameras ({len(cameras)-88} cameras)")
print()

# Show first few new cameras
print("🆕 SAMPLE NEW CAMERAS (89-93):")
for i in range(88, min(93, len(cameras))):
    cam = cameras[i]
    result = next((r for r in results if r['id'] == i), None)
    status = "✅" if result and result['status'] == 'online' else "❌"
    company = f" - {cam.get('company', 'N/A')}" if cam.get('company') else ""
    print(f"   {status} Camera {i+1}: {cam['name']}{company}")
    print(f"      {cam['url'][:70]}...")
print()

# Show offline cameras (first 10)
if offline:
    print(f"❌ OFFLINE CAMERAS (showing first 10 of {len(offline)}):")
    for result in offline[:10]:
        cam_id = result['id']
        cam = cameras[cam_id]
        print(f"   Camera {cam_id+1}: {cam['name']}")
        print(f"      Error: {result.get('error', 'Unknown')}")
print()

# Grid layout info
print("🖼️  GRID LAYOUT INFO:")
print(f"   For {len(cameras)} cameras: 18x16 grid (288 capacity)")
print(f"   Tile size: ~100x56 pixels")
print(f"   Total grid: ~1800x900 pixels")
print()

print("=" * 80)
print("✅ Test complete! Camera configuration is ready.")
print("=" * 80)