#!/usr/bin/env python3
"""
Test script to show what the new camera overlays will look like
"""
import json

def extract_camera_info(camera_config, cam_id):
    """Extract camera number, company, and city from camera config"""
    camera = camera_config['cameras'][cam_id]
    name = camera['name']
    
    # Camera number
    camera_number = cam_id + 1
    
    # Extract city from name (format: "Camera X - City" or "Camera X (Type) - City")
    city = ""
    if " - " in name:
        city = name.split(" - ")[-1]  # Get everything after last " - "
    
    # Get company if available
    company = camera.get('company', '')
    
    # Build display lines - only show what's available
    display_lines = []
    
    # Camera number (always show)
    display_lines.append(f"Camera {camera_number}")
    
    # Company (only if available and not 'Unknown')
    if company and company != 'Unknown':
        display_lines.append(company)
    
    # City (only if available)
    if city:
        display_lines.append(city)
    
    return display_lines

def main():
    print("🎥 Camera Overlay Preview")
    print("=" * 50)
    
    # Load camera config
    with open('camera_config.json', 'r') as f:
        config = json.load(f)
    
    print("New overlay format will show:")
    print("• Camera number (always)")
    print("• Company (only if available)")
    print("• City/Country (extracted from name)")
    print()
    
    # Show examples for different camera types
    test_cameras = [0, 17, 40, 52, 70, 85]  # Different types of cameras
    
    for cam_id in test_cameras:
        if cam_id < len(config['cameras']):
            camera = config['cameras'][cam_id]
            display_lines = extract_camera_info(config, cam_id)
            
            print(f"Camera {cam_id + 1} ({camera['name']}):")
            print("  Overlay will show:")
            for line in display_lines:
                print(f"    {line}")
            print()
    
    print("Benefits of new overlay:")
    print("✅ Clean, minimal text")
    print("✅ Only essential information")
    print("✅ Camera number always visible")
    print("✅ Company shown when available")
    print("✅ City/country for location context")
    print("✅ No technical details cluttering the view")
    
    return 0

if __name__ == "__main__":
    exit(main())