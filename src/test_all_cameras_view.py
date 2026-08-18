#!/usr/bin/env python3
"""
Test the all cameras view functionality
"""

import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from webcams import InteractiveCameraViewer, ConfigManager

def test_all_cameras_view():
    print("🔍 Testing All Cameras View")
    print("=" * 40)
    
    # Load config and create viewer
    config = ConfigManager.load_config()
    viewer = InteractiveCameraViewer(config)
    
    print(f"Total cameras: {len(viewer.cams)}")
    print(f"Initial show_all_cameras: {viewer.show_all_cameras}")
    
    # Create some dummy frames for testing
    print("Creating dummy frames for testing...")
    for i in range(min(10, len(viewer.cams))):  # Create frames for first 10 cameras
        dummy_frame = np.zeros((viewer.settings['cam_height'], viewer.settings['cam_width'], 3), dtype=np.uint8)
        # Add camera number
        cv2.putText(dummy_frame, f"CAM {i+1}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(dummy_frame, "DUMMY FRAME", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        viewer.frames[i] = dummy_frame
    
    print(f"Created {len(viewer.frames)} dummy frames")
    
    # Test paged view
    print("\n📄 Testing paged view...")
    viewer.show_all_cameras = False
    try:
        paged_frame = viewer.get_display_frame()
        print(f"✅ Paged view frame created: {paged_frame.shape}")
    except Exception as e:
        print(f"❌ Paged view error: {e}")
    
    # Test all cameras view
    print("\n📺 Testing all cameras view...")
    viewer.show_all_cameras = True
    try:
        all_cameras_frame = viewer.get_all_cameras_frame()
        print(f"✅ All cameras view frame created: {all_cameras_frame.shape}")
        
        # Save a test image
        cv2.imwrite("test_all_cameras_view.jpg", all_cameras_frame)
        print("✅ Test image saved as 'test_all_cameras_view.jpg'")
        
    except Exception as e:
        print(f"❌ All cameras view error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test toggle functionality
    print("\n🔄 Testing toggle functionality...")
    for i in range(3):
        old_state = viewer.show_all_cameras
        viewer.show_all_cameras = not viewer.show_all_cameras
        new_state = viewer.show_all_cameras
        mode = "all cameras" if new_state else "paged"
        print(f"   Toggle {i+1}: {old_state} → {new_state} ({mode})")
    
    print("\n🎯 All cameras view test completed!")

if __name__ == "__main__":
    test_all_cameras_view()