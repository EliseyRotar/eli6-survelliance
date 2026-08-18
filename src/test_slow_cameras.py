#!/usr/bin/env python3
"""
Test script for slow/stuck cameras
Tests cameras 3, 16, 23, 71, 72, 73, 75, 76, 84
"""
import json
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def test_camera_with_long_timeout(cam_id, camera):
    """Test a single camera with extended timeout"""
    url = camera['url']
    username = camera.get('username', '')
    password = camera.get('password', '')
    name = camera['name']
    
    result = {
        'id': cam_id,
        'name': name,
        'url': url,
        'status': 'unknown',
        'response_time': 0,
        'error': None
    }
    
    try:
        start_time = time.time()
        
        auth = (username, password) if username and password else None
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/jpeg,image/png,image/*,*/*;q=0.8",
            "Cache-Control": "no-cache"
        }
        
        # Use 15 second timeout for slow cameras
        response = requests.get(
            url, 
            auth=auth, 
            timeout=15.0,
            headers=headers,
            stream=True
        )
        
        response_time = time.time() - start_time
        result['response_time'] = response_time
        
        if response.status_code == 200:
            content = next(response.iter_content(chunk_size=1024), b'')
            if len(content) > 100:
                result['status'] = 'online'
                result['content_size'] = len(content)
            else:
                result['status'] = 'error'
                result['error'] = f'Content too small: {len(content)} bytes'
        else:
            result['status'] = 'error'
            result['error'] = f'HTTP {response.status_code}'
            
    except requests.exceptions.Timeout:
        result['status'] = 'timeout'
        result['error'] = 'Connection timeout (>15s)'
    except requests.exceptions.ConnectionError as e:
        result['status'] = 'offline'
        result['error'] = f'Connection refused: {str(e)[:50]}'
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)[:100]
    
    return result

def main():
    print("🔍 Testing Slow/Stuck Cameras")
    print("=" * 70)
    
    # Load configuration
    with open('camera_config.json', 'r') as f:
        config = json.load(f)
    
    cameras = config['cameras']
    
    # Test specific slow cameras (0-indexed, so subtract 1)
    slow_camera_ids = [2, 15, 22, 70, 71, 72, 74, 75, 83]  # 3, 16, 23, 71, 72, 73, 75, 76, 84
    
    print(f"Testing {len(slow_camera_ids)} slow cameras with 15s timeout...\n")
    
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(test_camera_with_long_timeout, i, cameras[i]): i 
                   for i in slow_camera_ids if i < len(cameras)}
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            status_icon = {
                'online': '✅',
                'offline': '❌',
                'timeout': '⏱️',
                'error': '⚠️',
                'unknown': '❓'
            }.get(result['status'], '❓')
            
            print(f"{status_icon} Camera {result['id']+1}: {result['name'][:50]}")
            print(f"   Status: {result['status'].upper()}", end='')
            if result['response_time'] > 0:
                print(f" | Response: {result['response_time']:.2f}s", end='')
            if result.get('content_size'):
                print(f" | Size: {result['content_size']} bytes", end='')
            if result['error']:
                print(f" | Error: {result['error']}", end='')
            print()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    online = sum(1 for r in results if r['status'] == 'online')
    offline = sum(1 for r in results if r['status'] == 'offline')
    timeout = sum(1 for r in results if r['status'] == 'timeout')
    error = sum(1 for r in results if r['status'] == 'error')
    
    print(f"✅ Online: {online}/{len(results)}")
    print(f"❌ Offline: {offline}/{len(results)}")
    print(f"⏱️  Timeout: {timeout}/{len(results)}")
    print(f"⚠️  Error: {error}/{len(results)}")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if timeout > 0:
        print(f"   • {timeout} cameras still timing out at 15s - may be truly offline")
    if error > 0:
        print(f"   • {error} cameras have errors - check URLs and credentials")
    if online == len(results):
        print("   • All cameras working! ✅")
    elif online > 0:
        print(f"   • {online} cameras working with extended timeout")
        print("   • System now configured with 10s timeout + 15s initial load timeout")
    
    return 0

if __name__ == "__main__":
    exit(main())
