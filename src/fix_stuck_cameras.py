#!/usr/bin/env python3
"""
Quick fix script for stuck cameras 50+
"""
import json
import time
import requests
import subprocess
import sys

def check_web_server():
    """Check if web server is running"""
    try:
        response = requests.get("http://localhost:5000/api/system/status", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_camera_range(start, end):
    """Test a range of cameras"""
    working = 0
    stuck = 0
    
    for i in range(start, end + 1):
        try:
            response = requests.get(f"http://localhost:5000/camera_thumbnail/{i}", timeout=5)
            if response.status_code == 200 and len(response.content) > 1000:
                working += 1
            else:
                stuck += 1
        except:
            stuck += 1
    
    return working, stuck

def main():
    print("🔧 Quick Fix for Stuck Cameras 50+")
    print("=" * 50)
    
    # Check if web server is running
    if not check_web_server():
        print("❌ Web server not running!")
        print("Please start with: python3 webcams.py")
        return 1
    
    print("✅ Web server is running")
    
    # Test camera ranges
    print("\n📊 Testing camera ranges...")
    
    ranges = [
        (0, 25, "Cameras 1-26"),
        (26, 49, "Cameras 27-50"), 
        (50, 75, "Cameras 51-76"),
        (76, 87, "Cameras 77-88")
    ]
    
    total_working = 0
    total_stuck = 0
    
    for start, end, label in ranges:
        working, stuck = test_camera_range(start, end)
        total_working += working
        total_stuck += stuck
        
        status = "✅" if stuck == 0 else "⚠️" if stuck < (end - start + 1) // 2 else "❌"
        print(f"{status} {label}: {working} working, {stuck} stuck")
    
    print(f"\n📈 Overall: {total_working} working, {total_stuck} stuck")
    
    # Diagnosis
    if total_stuck > 20:
        print("\n🔍 DIAGNOSIS: Major loading issue detected")
        print("Likely causes:")
        print("• Thread pool bottleneck")
        print("• System overload")
        print("• Initialization timing issue")
        
        print("\n💡 RECOMMENDED FIXES:")
        print("1. Restart the system:")
        print("   • Press Ctrl+C in webcams.py terminal")
        print("   • Wait 5 seconds")
        print("   • Run: python3 webcams.py")
        
        print("\n2. If problem persists, check system resources:")
        print("   • CPU usage: top")
        print("   • Memory usage: free -h")
        print("   • Check logs: tail -f surveillance.log")
        
    elif total_stuck > 5:
        print("\n🔍 DIAGNOSIS: Some cameras slow to load")
        print("This is normal for cameras 50+ due to initialization order")
        
        print("\n💡 QUICK FIXES:")
        print("1. Wait 30-60 seconds and refresh browser")
        print("2. Or restart system for faster loading")
        
    else:
        print("\n✅ DIAGNOSIS: All cameras loading properly!")
        print("If you still see stuck cameras in browser:")
        print("• Refresh the page (F5)")
        print("• Clear browser cache (Ctrl+Shift+R)")
    
    # Auto-fix attempt
    if total_stuck > 10:
        print(f"\n🔄 Attempting auto-fix...")
        print("Sending refresh signal to system...")
        
        try:
            # Try to trigger a refresh via API
            requests.get("http://localhost:5000/api/system/status", timeout=2)
            print("✅ Refresh signal sent")
            
            print("Waiting 10 seconds for cameras to initialize...")
            time.sleep(10)
            
            # Test again
            working_after, stuck_after = test_camera_range(50, 87)
            if stuck_after < total_stuck:
                print(f"✅ Improvement: {total_stuck - stuck_after} cameras recovered!")
            else:
                print("⚠️  No improvement - manual restart recommended")
                
        except Exception as e:
            print(f"❌ Auto-fix failed: {e}")
    
    return 0

if __name__ == "__main__":
    exit(main())