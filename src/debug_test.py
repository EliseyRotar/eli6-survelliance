#!/usr/bin/env python3

import sys
import traceback

# Test the specific methods that are causing issues
try:
    import webcams
    
    print("Creating viewer instance...")
    config = webcams.ConfigManager.load_config()
    viewer = webcams.InteractiveCameraViewer(config)
    
    print("Testing fetch_image_frame_advanced...")
    # Test with a simple camera
    url = "http://119.224.56.57:8081/out.jpg"
    user = ""
    password = ""
    name = "Test Camera"
    
    try:
        result = viewer.fetch_image_frame_advanced(url, user, password, name)
        print(f"Image method result type: {type(result)}")
        if result:
            print(f"Result length: {len(result)}")
            if len(result) == 2:
                print(f"Frame type: {type(result[0])}, Original frame type: {type(result[1])}")
        else:
            print("Result is None or empty")
    except Exception as e:
        print(f"Error in fetch_image_frame_advanced: {e}")
        traceback.print_exc()
    
    print("Testing fetch_video_frame_advanced...")
    # Test with a video camera
    try:
        result = viewer.fetch_video_frame_advanced(13, "http://213.144.145.239:8090/cam_1.cgi", "Test Video")
        print(f"Video method result type: {type(result)}")
        if result:
            print(f"Result length: {len(result)}")
            if len(result) == 2:
                print(f"Frame type: {type(result[0])}, Original frame type: {type(result[1])}")
        else:
            print("Result is None or empty")
    except Exception as e:
        print(f"Error in fetch_video_frame_advanced: {e}")
        traceback.print_exc()

except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()