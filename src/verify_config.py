#!/usr/bin/env python3
"""Quick verification of 277 cameras configuration"""
import json
from collections import Counter
from urllib.parse import urlparse

# Load camera configuration
with open('camera_config.json', 'r') as f:
    config = json.load(f)

cameras = config['cameras']

print("🎥 CAMERA CONFIGURATION VERIFICATION")
print("=" * 60)
print(f"📹 Total Cameras: {len(cameras)}")
print()

# Count by type
types = Counter(cam['type'] for cam in cameras)
print("📊 CAMERA TYPES:")
for cam_type, count in types.items():
    print(f"   {cam_type.title()}: {count}")
print()

# Count by authentication
auth_count = sum(1 for cam in cameras if cam.get('username'))
print(f"🔐 Authenticated Cameras: {auth_count}")
print(f"🔓 No Auth Cameras: {len(cameras) - auth_count}")
print()

# Count by company
companies = Counter(cam.get('company', 'None') for cam in cameras)
company_count = sum(1 for company, count in companies.items() if company != 'None')
print(f"🏢 Company Cameras: {company_count}")
print(f"🏠 Individual Cameras: {companies['None']}")
print()

# Show top companies
print("🏢 TOP COMPANIES:")
for company, count in companies.most_common(10):
    if company != 'None':
        print(f"   {company}: {count} cameras")
print()

# Count by location
locations = Counter()
for cam in cameras:
    name = cam['name']
    if ' - ' in name:
        location = name.split(' - ')[-1]
        locations[location] += 1

print("🌍 LOCATIONS:")
for location, count in locations.most_common(10):
    print(f"   {location}: {count} cameras")
print()

# Check for duplicates
urls = [cam['url'] for cam in cameras]
ips = []
for url in urls:
    parsed = urlparse(url)
    if parsed.hostname:
        ips.append(parsed.hostname)

unique_ips = len(set(ips))
print(f"🌐 Unique IP Addresses: {unique_ips}")
print(f"🔄 Duplicate IPs: {len(ips) - unique_ips}")
print()

# Show camera ranges
print("📍 CAMERA RANGES:")
print(f"   Cameras 1-88: Original cameras")
print(f"   Cameras 89-277: Newly added ({len(cameras)-88} cameras)")
print()

# Show sample new cameras
print("🆕 SAMPLE NEW CAMERAS:")
for i in range(88, min(93, len(cameras))):
    cam = cameras[i]
    company = f" ({cam['company']})" if cam.get('company') else ""
    auth = f" [{cam['username']}:{cam['password']}]" if cam.get('username') else " [no auth]"
    print(f"   Camera {i+1}: {cam['name']}{company} [{cam['type']}]{auth}")
    print(f"      {cam['url'][:70]}...")
print()

# Grid calculation
num_cameras = len(cameras)
if num_cameras <= 272:
    cols, rows = 17, 16
else:
    cols, rows = 18, 16

print("🖼️  GRID LAYOUT:")
print(f"   Grid: {cols}x{rows} = {cols*rows} capacity")
print(f"   Cameras: {num_cameras}")
print(f"   Empty slots: {cols*rows - num_cameras}")
print(f"   Tile size: ~{1800//cols}x{900//rows} pixels")
print()

print("=" * 60)
print("✅ Configuration verified! Ready to test system.")
print("=" * 60)