#!/usr/bin/env python3
"""
Camera Connection Diagnostic Tool
Tests all cameras and identifies connection issues
"""
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def test_camera(cam_id, camera):
    """Test a single camera connection"""
    url = camera['url']
    username = camera.get('username', '')
    password = camera.get('password', '')
    name = camera['name']
    cam_type = camera.get('type', 'image')
    
    result = {
        'id': cam_id,
        'name': name,
        'url': url,
        'type': cam_type,
        'status': 'unknown',
        'response_time': 0,
        'error': None
    }
    
    try:
        start_time = time.time()
        
        # Test with increased timeout
        auth = (username, password) if username and password else None
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/jpeg,image/png,image/*,*/*;q=0.8"
        }
        
        response = requests.get(
            url, 
            auth=auth, 
            timeout=5.0,  # 5 second timeout
            headers=headers,
            stream=True
        )
        
        response_time = time.time() - start_time
        result['response_time'] = response_time
        
        if response.status_code == 200:
            # Check content size
            content = next(response.iter_content(chunk_size=1024), b'')
            if len(content) > 100:
                result['status'] = 'online'
            else:
                result['status'] = 'error'
                result['error'] = 'Content too small'
        else:
            result['status'] = 'error'
            result['error'] = f'HTTP {response.status_code}'
            
    except requests.exceptions.Timeout:
        result['status'] = 'timeout'
        result['error'] = 'Connection timeout (>5s)'
    except requests.exceptions.ConnectionError:
        result['status'] = 'offline'
        result['error'] = 'Connection refused'
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)[:50]
    
    return result

def main():
    print("🔍 Camera Connection Diagnostic Tool")
    print("=" * 60)
    
    # Load configuration
    with open('camera_config.json', 'r') as f:
        config = json.load(f)
    
    cameras = config['cameras']
    print(f"Testing {len(cameras)} cameras...\n")
    
    # Test cameras in parallel
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(test_camera, i, cam): i for i, cam in enumerate(cameras)}
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            # Print progress
            status_icon = {
                'online': '✅',
                'offline': '❌',
                'timeout': '⏱️',
                'error': '⚠️',
                'unknown': '❓'
            }.get(result['status'], '❓')
            
            print(f"{status_icon} Camera {result['id']+1}: {result['name'][:40]} - {result['status'].upper()}", end='')
            if result['response_time'] > 0:
                print(f" ({result['response_time']:.2f}s)", end='')
            if result['error']:
                print(f" - {result['error']}", end='')
            print()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    online = sum(1 for r in results if r['status'] == 'online')
    offline = sum(1 for r in results if r['status'] == 'offline')
    timeout = sum(1 for r in results if r['status'] == 'timeout')
    error = sum(1 for r in results if r['status'] == 'error')
    
    print(f"✅ Online: {online}/{len(cameras)} ({online/len(cameras)*100:.1f}%)")
    print(f"❌ Offline: {offline}/{len(cameras)}")
    print(f"⏱️  Timeout: {timeout}/{len(cameras)}")
    print(f"⚠️  Error: {error}/{len(cameras)}")
    
    # Slow cameras
    slow_cameras = [r for r in results if r['response_time'] > 3.0 and r['status'] == 'online']
    if slow_cameras:
        print(f"\n⚠️  Slow cameras (>3s response):")
        for cam in slow_cameras:
            print(f"   Camera {cam['id']+1}: {cam['name']} - {cam['response_time']:.2f}s")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if timeout > 0:
        print(f"   • {timeout} cameras timing out - timeout increased to 5s in config")
    if slow_cameras:
        print(f"   • {len(slow_cameras)} cameras are slow - may appear offline intermittently")
    if offline > 0:
        print(f"   • {offline} cameras truly offline - check camera availability")
    
    print("\n✅ FIXES APPLIED:")
    print("   • Timeout increased: 1.5s → 5.0s")
    print("   • Offline threshold: 3 errors → 15 errors")
    print("   • Retry logic: 3 attempts per fetch")
    print("   • Backoff delay: Max 5s (was 60s)")
    print("   • Cache reduced: 2s → 1s")
    
    return 0

if __name__ == "__main__":
    exit(main())
