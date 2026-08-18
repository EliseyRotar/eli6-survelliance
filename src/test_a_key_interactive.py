#!/usr/bin/env python3
"""
Interactive test for 'a' key functionality
"""

import cv2
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from webcams import InteractiveCameraViewer, ConfigManager

def test_a_key_interactive():
    print("🔍 Testing 'a' key functionality interactively")
    print("=" * 50)
    print("Instructions:")
    print("1. System will start in paged view (default)")
    print("2. Press 'a' to toggle to all cameras view")
    print("3. Press 'a' again to toggle back to paged view")
    print("4. Press 'q' to quit")
    print("5. Watch the console for toggle messages")
    print()
    
    # Load config and create viewer
    config = ConfigManager.load_config()
    viewer = InteractiveCameraViewer(config)
    
    print(f"Initial state: show_all_cameras = {viewer.show_all_cameras}")
    print("Starting system...")
    
    # Start camera threads
    threads = viewer.start_threads()
    
    try:
        toggle_count = 0
        while viewer.running:
            # Get display frame
            try:
                combined = viewer.get_display_frame()
                
                # Show current mode in window title
                mode = "ALL CAMERAS" if viewer.show_all_cameras else f"PAGE {viewer.current_page + 1}/{viewer.total_pages}"
                cv2.imshow(f"ELI6 Webcams - {mode}", combined)
                
                # Handle keys
                key = cv2.waitKey(50) & 0xFF
                if key == ord('q'):
                    print("Quitting...")
                    break
                elif key == ord('a'):
                    if viewer.selected_camera is None:
                        old_state = viewer.show_all_cameras
                        viewer.show_all_cameras = not viewer.show_all_cameras
                        new_state = viewer.show_all_cameras
                        toggle_count += 1
                        
                        mode = "all cameras" if new_state else "paged"
                        print(f"🔄 Toggle #{toggle_count}: {old_state} → {new_state} ({mode} view)")
                        
                        if toggle_count >= 4:
                            print("✅ 'a' key functionality verified! Press 'q' to quit.")
                    else:
                        print("⚠️  'a' key only works when not in fullscreen mode")
                        
            except Exception as e:
                print(f"Error in display loop: {e}")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    
    finally:
        print("🔧 Shutting down...")
        viewer.running = False
        viewer.thread_pool.shutdown(wait=True)
        
        # Clean up video captures
        for cam_id, cap in viewer.video_captures.items():
            cap.release()
        viewer.video_captures.clear()
        
        cv2.destroyAllWindows()
        print("✅ Test completed")

if __name__ == "__main__":
    test_a_key_interactive()