#!/usr/bin/env python3
import requests
import time

# Test the cameras individually
cams = [
    ("http://187.140.117.185/web/tmpfs/snap.jpg", "admin", "admin", "Camera 1"),
    ("http://162.204.123.101/web/tmpfs/snap.jpg", "admin", "admin", "Camera 2"),
    ("http://133.232.94.137/web/tmpfs/snap.jpg", "admin", "admin", "Camera 4"),
]

def test_camera(url, user, password, name):
    print(f"Testing {name}...")
    try:
        start_time = time.time()
        r = requests.get(url, auth=(user, password), timeout=5, 
                        headers={"User-Agent": "Mozilla/5.0"})
        elapsed = time.time() - start_time
        
        print(f"  Status: {r.status_code}")
        print(f"  Response time: {elapsed:.2f}s")
        print(f"  Content length: {len(r.content)} bytes")
        print(f"  Content type: {r.headers.get('content-type', 'unknown')}")
        
        if r.status_code == 200 and len(r.content) > 1000:
            print(f"  ✓ {name} is working!")
        else:
            print(f"  ✗ {name} has issues")
            
    except Exception as e:
        print(f"  ✗ {name} failed: {e}")
    print()

if __name__ == "__main__":
    print("Testing individual cameras...\n")
    for url, user, pwd, name in cams:
        test_camera(url, user, pwd, name)