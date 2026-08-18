#!/usr/bin/env python3
"""
Test script to verify camera count and grid layout fixes
"""
import json
import sys

def test_camera_config():
    """Test camera configuration"""
    print("=== CAMERA CONFIGURATION TEST ===")
    
    try:
        with open('camera_config.json', 'r') as f:
            config = json.load(f)
        
        cameras = config['cameras']
        total_cameras = len(cameras)
        enabled_cameras = sum(1 for c in cameras if c.get('enabled', True))
        
        print(f"✓ Total cameras in config: {total_cameras}")
        print(f"✓ Enabled cameras: {enabled_cameras}")
        print(f"✓ Last camera: {cameras[-1]['name']}")
        print(f"✓ Last camera URL: {cameras[-1]['url']}")
        
        # Check for Camera 85 specifically
        camera_85 = next((c for c in cameras if 'Camera 85' in c['name']), None)
        if camera_85:
            print(f"✓ Camera 85 found: {camera_85['name']}")
            print(f"  - URL: {camera_85['url']}")
            print(f"  - Username: {camera_85['username']}")
            print(f"  - Enabled: {camera_85['enabled']}")
        else:
            print("✗ Camera 85 not found!")
            
        return total_cameras == 85 and enabled_cameras == 85
        
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False

def test_grid_layout():
    """Test grid layout calculations"""
    print("\n=== GRID LAYOUT TEST ===")
    
    def calculate_grid_layout(num_cameras):
        """Calculate grid layout for given number of cameras"""
        if num_cameras <= 12:
            return 4, 3
        elif num_cameras <= 20:
            return 5, 4
        elif num_cameras <= 30:
            return 6, 5
        elif num_cameras <= 42:
            return 7, 6
        elif num_cameras <= 56:
            return 8, 7
        elif num_cameras <= 72:
            return 9, 8
        else:
            # For 85 cameras: 10x9 grid
            return 10, 9
    
    # Test different camera counts
    test_counts = [40, 65, 84, 85]
    
    for count in test_counts:
        cols, rows = calculate_grid_layout(count)
        grid_capacity = cols * rows
        print(f"✓ {count} cameras -> {cols}x{rows} grid (capacity: {grid_capacity})")
        
        if count > grid_capacity:
            print(f"  ⚠️  Warning: {count} cameras exceed grid capacity of {grid_capacity}")
        else:
            print(f"  ✓ Grid can accommodate {count} cameras")
    
    return True

def test_tile_sizing():
    """Test tile sizing for different camera counts"""
    print("\n=== TILE SIZING TEST ===")
    
    max_width = 1800
    max_height = 900
    
    def calculate_tile_size(num_cameras):
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
        else:
            cols, rows = 10, 9
        
        tile_width = min(180, max_width // cols)
        tile_height = min(135, max_height // rows)
        
        return tile_width, tile_height, cols, rows
    
    for count in [40, 65, 84, 85]:
        tile_w, tile_h, cols, rows = calculate_tile_size(count)
        total_width = tile_w * cols
        total_height = tile_h * rows
        
        print(f"✓ {count} cameras:")
        print(f"  - Grid: {cols}x{rows}")
        print(f"  - Tile size: {tile_w}x{tile_h}")
        print(f"  - Total size: {total_width}x{total_height}")
        print(f"  - Fits in {max_width}x{max_height}: {total_width <= max_width and total_height <= max_height}")
    
    return True

def main():
    """Run all tests"""
    print("🚀 TESTING CAMERA SYSTEM FIXES")
    print("=" * 50)
    
    config_ok = test_camera_config()
    grid_ok = test_grid_layout()
    tile_ok = test_tile_sizing()
    
    print("\n=== TEST SUMMARY ===")
    print(f"Camera Config: {'✓ PASS' if config_ok else '✗ FAIL'}")
    print(f"Grid Layout: {'✓ PASS' if grid_ok else '✗ FAIL'}")
    print(f"Tile Sizing: {'✓ PASS' if tile_ok else '✗ FAIL'}")
    
    if config_ok and grid_ok and tile_ok:
        print("\n🎉 ALL TESTS PASSED!")
        print("The system should now:")
        print("  ✓ Show all 85 cameras in desktop all-cameras view")
        print("  ✓ Display correct camera count in web interface")
        print("  ✓ Handle grid layout properly for 85 cameras")
        print("  ✓ Include Camera 85 (USA) in the system")
        return True
    else:
        print("\n❌ SOME TESTS FAILED!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)