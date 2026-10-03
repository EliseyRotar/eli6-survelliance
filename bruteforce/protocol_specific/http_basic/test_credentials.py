#!/usr/bin/env python3
"""
Quick Credential Tester
Test specific username/password combinations against a webcam
"""

import requests
import base64
import argparse
from urllib.parse import urlparse

def test_single_credential(target_url, username, password):
    """Test a single credential combination"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print(f"🎯 Testing: {username}:{password if password else '(empty)'}")
    print(f"🌐 Target: {target_url}")
    print("-" * 50)
    
    try:
        # Test HTTP Basic Auth
        auth_string = f"{username}:{password}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = session.headers.copy()
        headers['Authorization'] = f'Basic {encoded_auth}'
        
        response = session.get(target_url, headers=headers, timeout=10)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📏 Response Length: {len(response.text)} bytes")
        print(f"🔗 Final URL: {response.url}")
        
        # Show headers
        print("\n📋 Response Headers:")
        for key, value in response.headers.items():
            print(f"   {key}: {value}")
        
        # Show content preview
        print(f"\n📄 Content Preview (first 500 chars):")
        content_preview = response.text[:500].replace('\n', '\\n').replace('\r', '\\r')
        print(f"   {content_preview}")
        
        if len(response.text) > 500:
            print("   ... (truncated)")
        
        # Analysis
        print(f"\n🔍 Analysis:")
        if response.status_code == 200:
            print("   ✅ HTTP 200 OK - Likely successful authentication")
            if len(response.text) > 1000:
                print("   ✅ Substantial content returned - Strong success indicator")
            elif len(response.text) > 100:
                print("   🤔 Moderate content - Possible success")
            else:
                print("   ⚠️  Minimal content - May be error page")
        elif response.status_code == 401:
            print("   ❌ HTTP 401 Unauthorized - Credentials rejected")
        elif response.status_code == 403:
            print("   ❌ HTTP 403 Forbidden - Access denied")
        else:
            print(f"   🤔 HTTP {response.status_code} - Unusual response")
        
        # Content analysis
        content_lower = response.text.lower()
        camera_keywords = [
            'camera', 'video', 'stream', 'live', 'snapshot', 'image',
            'jpeg', 'mjpeg', 'rtsp', 'onvif', 'webcam', 'ipcam'
        ]
        
        found_keywords = [kw for kw in camera_keywords if kw in content_lower]
        if found_keywords:
            print(f"   📹 Camera keywords found: {', '.join(found_keywords)}")
        
        # Final verdict
        print(f"\n🎯 VERDICT:")
        if response.status_code == 200 and (len(response.text) > 500 or found_keywords):
            print("   🎉 CREDENTIALS LIKELY WORK!")
            return True
        elif response.status_code == 200:
            print("   🤔 POSSIBLE SUCCESS - Manual verification recommended")
            return True
        else:
            print("   ❌ CREDENTIALS DO NOT WORK")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("🔌 Connection error - check URL and network")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test specific webcam credentials')
    parser.add_argument('target', help='Webcam URL')
    parser.add_argument('username', help='Username to test')
    parser.add_argument('password', nargs='?', default='', help='Password to test (empty if not provided)')
    
    args = parser.parse_args()
    
    # Format URL
    target = args.target
    if not target.startswith(('http://', 'https://')):
        target = 'http://' + target
    
    print("🔐 Webcam Credential Tester")
    print("=" * 50)
    
    success = test_single_credential(target, args.username, args.password)
    
    if success:
        print(f"\n🌐 Try accessing: {target}")
        print(f"🔑 Use credentials: {args.username}:{args.password if args.password else '(empty)'}")

if __name__ == "__main__":
    main()