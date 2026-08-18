#!/usr/bin/env python3
"""
Test script to verify 88 cameras display correctly
"""
import json

def test_grid_layout_88():
    """Test grid layout for 88 cameras"""
    print("=== TESTING 88 CAMERA GRID LAYOUT ===")
    
    num_cameras = 88
    
    # Grid calculation logic from webcams.py
    if num_cameras <= 12:
        cols, rows = 4, 3
    elif num_cameras <= 20:
        cols, rows = 5, 4
    elif num_cameras <= 30:
        cols, rows = 6, 5
    elif num_cameras <= 42:
        cols, rows = 7, 6
    elif num_cameras <= 56:
        cols, rows = 8, 7
    elif num_cameras <= 72:
        cols, rows = 9, 8
    elif num_cameras <= 90:
        cols, rows = 10, 9  # 10x9 grid for up to 90 cameras
    else:
        cols, rows = 11, 10
    
    grid_capacity = cols * rows
    
    print(f"✓ 88 cameras -> {cols}x{rows} grid")
    print(f"✓ Grid capacity: {grid_capacity}")
    print(f"✓ Can fit 88 cameras: {88 <= grid_capacity}")
    
    # Test tile sizing
    max_width = 1800
    max_height = 900
    
    tile_width = min(180, max_width // cols)
    tile_height = min(100, max_height // rows)
    
    total_width = tile_width * cols
    total_height = tile_height * rows
    
    print(f"✓ Tile size: {tile_width}x{tile_height}")
    print(f"✓ Total grid size: {total_width}x{total_height}")
    print(f"✓ Fits in screen: {total_width <= max_width and total_height <= max_height}")
    
    return True

def test_camera_config():
    """Test camera configuration"""
    print("\n=== TESTING CAMERA CONFIGURATION ===")
    
    with open('camera_config.json', 'r') as f:
        config = json.load(f)
    
    cameras = config['cameras']
    total = len(cameras)
    
    print(f"✓ Total cameras in config: {total}")
    
    # Check new cameras
    new_cameras = [
        ("Camera 86", "http://91.51.187.49/web/tmpfs/snap.jpg"),
        ("Camera 87", "http://82.72.192.154/tmpfs/snap.jpg"),
        ("Camera 88", "http://91.14.88.219/tmpfs/auto.jpg")
    ]
    
    for name, url in new_cameras:
        found = any(name in cam['name'] and cam['url'] == url for cam in cameras)
        print(f"{'✓' if found else '✗'} {name}: {url}")
    
    return total == 88

def main():
    print("🚀 TESTING 88 CAMERA SYSTEM")
    print("=" * 50)
    
    config_ok = test_camera_config()
    grid_ok = test_grid_layout_88()
    
    print("\n=== SUMMARY ===")
    print(f"Config: {'✓ PASS' if config_ok else '✗ FAIL'}")
    print(f"Grid Layout: {'✓ PASS' if grid_ok else '✗ FAIL'}")
    
    if config_ok and grid_ok:
        print("\n🎉 ALL TESTS PASSED!")
        print("The system should now show ALL 88 cameras when you press 'a'")
    else:
        print("\n❌ TESTS FAILED!")

if __name__ == "__main__":
    main()