#!/usr/bin/env python3

import sys
import traceback
import numpy as np

# Test the specific line that's causing issues
try:
    import webcams
    
    print("Creating viewer instance...")
    config = webcams.ConfigManager.load_config()
    viewer = webcams.InteractiveCameraViewer(config)
    
    # Test the exact scenario that's failing
    print("Testing the exact scenario...")
    
    # Create a mock result like what the methods return
    frame = np.zeros((288, 384, 3), dtype=np.uint8)  # Mock frame
    original_frame = np.zeros((480, 640, 3), dtype=np.uint8)  # Mock original frame
    result = (frame, original_frame)
    
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result)}")
    print(f"Result[0] type: {type(result[0])}")
    print(f"Result[0] is not None: {result[0] is not None}")
    
    # Test the exact condition that's failing
    try:
        condition1 = result is not None
        print(f"result is not None: {condition1}")
        
        condition2 = isinstance(result, tuple)
        print(f"isinstance(result, tuple): {condition2}")
        
        condition3 = len(result) == 2
        print(f"len(result) == 2: {condition3}")
        
        # This might be the problematic line
        frame_check = result[0] is not None
        print(f"result[0] is not None: {frame_check}")
        
        # Test the full condition
        full_condition = result is not None and isinstance(result, tuple) and len(result) == 2
        print(f"Full condition: {full_condition}")
        
        if full_condition:
            frame, original_frame = result
            frame_not_none = frame is not None
            print(f"frame is not None: {frame_not_none}")
            
    except Exception as e:
        print(f"Error in condition testing: {e}")
        traceback.print_exc()

except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()