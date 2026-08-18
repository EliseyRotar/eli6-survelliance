#!/usr/bin/env python3
"""
Debug script to check which cameras are loading in the web interface
"""
import requests
import time
import json

def test_camera_thumbnails():
    """Test all camera thumbnail endpoints"""
    print("🔍 Testing Camera Thumbnail Loading")
    print("=" * 60)
    
    # Load camera config to get total count
    with open('camera_config.json', 'r') as f:
        config = json.load(f)
    
    total_cameras = len(config['cameras'])
    print(f"Testing {total_cameras} cameras...\n")
    
    base_url = "http://localhost:5000"
    
    # Test if web server is running
    try:
        response = requests.get(f"{base_url}/api/system/status", timeout=5)
        if response.status_code == 200:
            print("✅ Web server is running")
        else:
            print(f"⚠️  Web server returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Web server not accessible: {e}")
        print("Please start the system with: python3 webcams.py")
        return
    
    print("\nTesting camera thumbnails...")
    
    working_cameras = []
    stuck_cameras = []
    error_cameras = []
    
    for i in range(total_cameras):
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}/camera_thumbnail/{i}", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                content_length = len(response.content)
                if content_length > 1000:  # Valid image
                    working_cameras.append(i)
                    status = "✅ WORKING"
                else:
                    stuck_cameras.append(i)
                    status = "⏳ PLACEHOLDER"
                
                print(f"Camera {i+1:2d}: {status} ({response_time:.2f}s, {content_length} bytes)")
            else:
                error_cameras.append(i)
                print(f"Camera {i+1:2d}: ❌ ERROR (HTTP {response.status_code})")
                
        except requests.exceptions.Timeout:
            stuck_cameras.append(i)
            print(f"Camera {i+1:2d}: ⏱️  TIMEOUT (>10s)")
        except Exception as e:
            error_cameras.append(i)
            print(f"Camera {i+1:2d}: ❌ ERROR ({str(e)[:30]})")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    print(f"✅ Working cameras: {len(working_cameras)}/{total_cameras} ({len(working_cameras)/total_cameras*100:.1f}%)")
    print(f"⏳ Stuck/Loading: {len(stuck_cameras)}/{total_cameras}")
    print(f"❌ Error cameras: {len(error_cameras)}/{total_cameras}")
    
    if stuck_cameras:
        print(f"\n⏳ Stuck cameras (showing placeholder):")
        ranges = []
        start = stuck_cameras[0]
        end = start
        
        for i in range(1, len(stuck_cameras)):
            if stuck_cameras[i] == end + 1:
                end = stuck_cameras[i]
            else:
                if start == end:
                    ranges.append(f"Camera {start+1}")
                else:
                    ranges.append(f"Cameras {start+1}-{end+1}")
                start = stuck_cameras[i]
                end = start
        
        # Add the last range
        if start == end:
            ranges.append(f"Camera {start+1}")
        else:
            ranges.append(f"Cameras {start+1}-{end+1}")
        
        for range_str in ranges:
            print(f"   • {range_str}")
    
    if error_cameras:
        print(f"\n❌ Error cameras:")
        for cam_id in error_cameras:
            print(f"   • Camera {cam_id+1}")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if len(stuck_cameras) > 20:
        print("   • Many cameras stuck - likely thread pool or initialization issue")
        print("   • Check system logs: tail -f surveillance.log")
        print("   • Restart system: Ctrl+C then python3 webcams.py")
    elif len(stuck_cameras) > 0:
        print(f"   • {len(stuck_cameras)} cameras stuck at loading")
        print("   • These cameras may be slow to initialize")
        print("   • Wait 30-60 seconds and refresh browser")
    
    if len(working_cameras) == total_cameras:
        print("   • All cameras working perfectly! ✅")
    
    return working_cameras, stuck_cameras, error_cameras

def test_system_status():
    """Test system status API"""
    try:
        response = requests.get("http://localhost:5000/api/system/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"\n📊 System Status:")
            print(f"   • Active threads: {data.get('active_threads', 'N/A')}")
            print(f"   • Cache size: {data.get('cache_size', 'N/A')}")
            if 'system' in data:
                print(f"   • Active cameras: {data['system'].get('active_cameras', 'N/A')}")
                print(f"   • CPU usage: {data['system'].get('cpu_current', 'N/A'):.1f}%")
                print(f"   • Memory usage: {data['system'].get('memory_current', 'N/A'):.1f}%")
    except Exception as e:
        print(f"⚠️  Could not get system status: {e}")

if __name__ == "__main__":
    working, stuck, errors = test_camera_thumbnails()
    test_system_status()
    
    print(f"\n🚀 Quick Fix Commands:")
    print(f"   • Restart system: Ctrl+C in webcams.py terminal, then python3 webcams.py")
    print(f"   • Check logs: tail -f surveillance.log")
    print(f"   • Test specific camera: curl http://localhost:5000/camera_thumbnail/50")