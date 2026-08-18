#!/usr/bin/env python3
"""
Camera Test Results Analyzer
Analyzes and filters camera test results
"""

import json
import sys
from datetime import datetime
import argparse

def load_results(filename):
    """Load results from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{filename}'")
        return None

def filter_by_status(results, status):
    """Filter results by status"""
    return [r for r in results if r['status'] == status]

def analyze_response_times(results):
    """Analyze response times for successful connections"""
    online_results = filter_by_status(results, 'online')
    if not online_results:
        return None
    
    times = [r['response_time'] for r in online_results if r['response_time']]
    if not times:
        return None
    
    return {
        'count': len(times),
        'min': min(times),
        'max': max(times),
        'avg': sum(times) / len(times),
        'median': sorted(times)[len(times) // 2]
    }

def generate_working_cameras_list(results):
    """Generate a list of working camera URLs"""
    online_cameras = filter_by_status(results, 'online')
    return [cam['url'] for cam in online_cameras]

def main():
    parser = argparse.ArgumentParser(description='Analyze camera test results')
    parser.add_argument('filename', help='JSON results file to analyze')
    parser.add_argument('--status', help='Filter by status (online, auth_required, etc.)')
    parser.add_argument('--export-working', action='store_true', 
                       help='Export working camera URLs to a text file')
    parser.add_argument('--show-errors', action='store_true',
                       help='Show detailed error information')
    
    args = parser.parse_args()
    
    # Load results
    results = load_results(args.filename)
    if not results:
        return 1
    
    print(f"Analyzing {len(results)} camera test results")
    print("=" * 50)
    
    # Status breakdown
    status_counts = {}
    for result in results:
        status = result['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("Status Summary:")
    for status, count in sorted(status_counts.items()):
        percentage = (count / len(results)) * 100
        print(f"  {status.upper()}: {count} ({percentage:.1f}%)")
    
    # Response time analysis
    time_stats = analyze_response_times(results)
    if time_stats:
        print(f"\nResponse Time Analysis ({time_stats['count']} online cameras):")
        print(f"  Fastest: {time_stats['min']:.3f}s")
        print(f"  Slowest: {time_stats['max']:.3f}s")
        print(f"  Average: {time_stats['avg']:.3f}s")
        print(f"  Median:  {time_stats['median']:.3f}s")
    
    # Filter by status if requested
    if args.status:
        filtered = filter_by_status(results, args.status)
        print(f"\nCameras with status '{args.status}' ({len(filtered)}):")
        for cam in filtered:
            print(f"  {cam['url']}")
            if args.show_errors and cam.get('error'):
                print(f"    Error: {cam['error']}")
    
    # Export working cameras
    if args.export_working:
        working_cameras = generate_working_cameras_list(results)
        if working_cameras:
            output_file = 'working_cameras.txt'
            with open(output_file, 'w') as f:
                for url in working_cameras:
                    f.write(url + '\n')
            print(f"\nExported {len(working_cameras)} working camera URLs to {output_file}")
        else:
            print("\nNo working cameras found to export")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())