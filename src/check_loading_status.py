#!/usr/bin/env python3
"""Check which cameras are loading and which are stuck"""
import time
import sys

print("Monitoring camera loading status...")
print("Press Ctrl+C to stop")
print()

try:
    while True:
        # Read the log file
        try:
            with open('surveillance.log', 'r') as f:
                lines = f.readlines()
            
            # Find loaded cameras
            loaded = set()
            for line in lines:
                if '✓ Camera' in line and 'loaded' in line:
                    try:
                        cam_num = int(line.split('Camera ')[1].split(' ')[0])
                        loaded.add(cam_num)
                    except:
                        pass
            
            # Find cameras with errors
            errors = set()
            for line in lines:
                if '⚠️  Camera' in line and 'error' in line:
                    try:
                        cam_num = int(line.split('Camera ')[1].split(' ')[0])
                        errors.add(cam_num)
                    except:
                        pass
            
            # Calculate stats
            total = 277
            loaded_count = len(loaded)
            error_count = len(errors)
            loading_count = total - loaded_count - error_count
            
            # Clear screen
            print('\033[2J\033[H', end='')
            
            print("=" * 60)
            print("CAMERA LOADING STATUS")
            print("=" * 60)
            print(f"Total Cameras: {total}")
            print(f"✅ Loaded: {loaded_count} ({loaded_count*100//total}%)")
            print(f"⚠️  Errors: {error_count} ({error_count*100//total}%)")
            print(f"⏳ Loading: {loading_count} ({loading_count*100//total}%)")
            print()
            
            # Show ranges
            if loaded:
                loaded_sorted = sorted(loaded)
                print(f"Loaded range: {min(loaded_sorted)}-{max(loaded_sorted)}")
                
                # Find gaps
                gaps = []
                for i in range(1, total + 1):
                    if i not in loaded and i not in errors:
                        gaps.append(i)
                
                if gaps:
                    # Show first 20 stuck cameras
                    print(f"\nStuck cameras (first 20): {gaps[:20]}")
                    if len(gaps) > 20:
                        print(f"... and {len(gaps) - 20} more")
            
            print()
            print("Refreshing in 3 seconds... (Ctrl+C to stop)")
            
        except FileNotFoundError:
            print("Log file not found. Is the system running?")
        
        time.sleep(3)
        
except KeyboardInterrupt:
    print("\n\nStopped monitoring.")
    sys.exit(0)