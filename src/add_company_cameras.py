#!/usr/bin/env python3
"""
Helper script to add multiple cameras from the same company
Usage: python3 add_company_cameras.py
"""

import json
import sys

def add_company_cameras():
    """Add multiple cameras from the same company"""
    
    # Load current configuration
    try:
        with open('camera_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: camera_config.json not found!")
        return
    
    print("🎥 Add Multiple Cameras from Same Company")
    print("=" * 50)
    
    # Get company information
    company_name = input("Enter company name: ").strip()
    if not company_name:
        company_name = "Unknown Company"
    
    camera_type = input("Camera type (image/video) [image]: ").strip().lower()
    if camera_type not in ['image', 'video']:
        camera_type = 'image'
    
    username = input("Username (leave empty if no auth): ").strip()
    password = input("Password (leave empty if no auth): ").strip()
    
    print(f"\nAdding cameras for company: {company_name}")
    print(f"Type: {camera_type}")
    print(f"Auth: {'Yes' if username else 'No'}")
    print()
    
    cameras_added = 0
    current_camera_num = len(config['cameras']) + 1
    
    while True:
        print(f"Camera {current_camera_num}:")
        url = input("  Enter camera URL (or 'done' to finish): ").strip()
        
        if url.lower() == 'done':
            break
        
        if not url:
            print("  Skipping empty URL")
            continue
        
        # Create camera entry
        camera_name = input(f"  Camera name [Camera {current_camera_num}]: ").strip()
        if not camera_name:
            camera_name = f"Camera {current_camera_num}"
        
        new_camera = {
            "url": url,
            "username": username,
            "password": password,
            "name": camera_name,
            "enabled": True,
            "type": camera_type,
            "company": company_name
        }
        
        config['cameras'].append(new_camera)
        cameras_added += 1
        current_camera_num += 1
        
        print(f"  ✓ Added: {camera_name}")
        print()
    
    if cameras_added > 0:
        # Save updated configuration
        try:
            with open('camera_config.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"✅ Successfully added {cameras_added} cameras from {company_name}")
            print(f"📊 Total cameras in system: {len(config['cameras'])}")
            print()
            print("🔄 Restart the surveillance system to load new cameras:")
            print("   python3 webcams.py")
            
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
    else:
        print("No cameras were added.")

if __name__ == "__main__":
    add_company_cameras()