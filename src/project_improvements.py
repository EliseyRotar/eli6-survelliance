#!/usr/bin/env python3
"""
Comprehensive Project Improvement Analysis
"""
import os
import json
import re

def analyze_webcams_py():
    """Analyze webcams.py for improvements"""
    print("🔍 Analyzing webcams.py...")
    improvements = []
    
    with open('webcams.py', 'r') as f:
        content = f.read()
    
    # Check for hardcoded values
    if '84' in content:
        improvements.append({
            'category': 'Hardcoded Values',
            'issue': 'Found hardcoded camera limit (84)',
            'fix': 'Use dynamic camera count from config',
            'priority': 'HIGH'
        })
    
    # Check for timeout values
    timeout_matches = re.findall(r'timeout[=\s]+(\d+\.?\d*)', content, re.IGNORECASE)
    if timeout_matches:
        improvements.append({
            'category': 'Configuration',
            'issue': f'Timeout values: {set(timeout_matches)}',
            'fix': 'Consider making timeouts configurable per camera type',
            'priority': 'MEDIUM'
        })
    
    # Check for error handling
    try_count = content.count('try:')
    except_count = content.count('except')
    if try_count != except_count:
        improvements.append({
            'category': 'Error Handling',
            'issue': 'Mismatched try-except blocks',
            'fix': 'Review error handling structure',
            'priority': 'HIGH'
        })
    
    # Check for logging
    if 'logger.debug' not in content:
        improvements.append({
            'category': 'Logging',
            'issue': 'No debug logging found',
            'fix': 'Add debug logging for troubleshooting',
            'priority': 'LOW'
        })
    
    # Check for camera retry logic
    if 'retry' not in content.lower():
        improvements.append({
            'category': 'Reliability',
            'issue': 'No explicit retry logic for failed cameras',
            'fix': 'Add configurable retry mechanism',
            'priority': 'MEDIUM'
        })
    
    return improvements

def analyze_config():
    """Analyze configuration for improvements"""
    print("🔍 Analyzing configuration...")
    improvements = []
    
    with open('camera_config.json', 'r') as f:
        config = json.load(f)
    
    cameras = config.get('cameras', [])
    settings = config.get('settings', {})
    
    # Check for missing fields
    required_fields = ['url', 'username', 'password', 'name', 'enabled', 'type']
    for i, cam in enumerate(cameras):
        missing = [f for f in required_fields if f not in cam]
        if missing:
            improvements.append({
                'category': 'Configuration',
                'issue': f'Camera {i+1} missing fields: {missing}',
                'fix': 'Add missing fields to camera config',
                'priority': 'HIGH'
            })
    
    # Check for duplicate URLs
    urls = [cam['url'] for cam in cameras]
    duplicates = [url for url in set(urls) if urls.count(url) > 1]
    if duplicates:
        improvements.append({
            'category': 'Configuration',
            'issue': f'Duplicate camera URLs found: {len(duplicates)}',
            'fix': 'Review and remove duplicate cameras',
            'priority': 'MEDIUM'
        })
    
    # Check for optimal settings
    if settings.get('timeout', 0) < 2:
        improvements.append({
            'category': 'Performance',
            'issue': 'Timeout may be too short for some cameras',
            'fix': 'Consider increasing timeout to 2-3 seconds',
            'priority': 'LOW'
        })
    
    return improvements

def analyze_web_interface():
    """Analyze web interface for improvements"""
    print("🔍 Analyzing web interface...")
    improvements = []
    
    # Check for caching headers
    if os.path.exists('webcams.py'):
        with open('webcams.py', 'r') as f:
            content = f.read()
            
        if 'Cache-Control' not in content:
            improvements.append({
                'category': 'Web Performance',
                'issue': 'No cache control headers',
                'fix': 'Add cache headers for static assets',
                'priority': 'MEDIUM'
            })
        
        if 'gzip' not in content.lower():
            improvements.append({
                'category': 'Web Performance',
                'issue': 'No compression enabled',
                'fix': 'Enable gzip compression for responses',
                'priority': 'MEDIUM'
            })
    
    # Check JavaScript files
    js_dir = 'static/js'
    if os.path.exists(js_dir):
        js_files = [f for f in os.listdir(js_dir) if f.endswith('.js')]
        total_size = sum(os.path.getsize(os.path.join(js_dir, f)) for f in js_files)
        
        if total_size > 200000:  # 200KB
            improvements.append({
                'category': 'Web Performance',
                'issue': f'JavaScript files total {total_size/1024:.1f}KB',
                'fix': 'Consider minification and bundling',
                'priority': 'LOW'
            })
    
    return improvements

def suggest_new_features():
    """Suggest new features"""
    print("🔍 Suggesting new features...")
    features = [
        {
            'feature': 'Camera Groups',
            'description': 'Group cameras by location/company for easier management',
            'benefit': 'Better organization for 88+ cameras',
            'priority': 'HIGH'
        },
        {
            'feature': 'Motion Detection',
            'description': 'Detect motion in camera feeds and trigger alerts',
            'benefit': 'Automated surveillance',
            'priority': 'HIGH'
        },
        {
            'feature': 'Snapshot Scheduling',
            'description': 'Schedule automatic snapshots at intervals',
            'benefit': 'Historical record keeping',
            'priority': 'MEDIUM'
        },
        {
            'feature': 'Camera Health Dashboard',
            'description': 'Dedicated page showing camera uptime, errors, response times',
            'benefit': 'Better monitoring and troubleshooting',
            'priority': 'MEDIUM'
        },
        {
            'feature': 'Export/Import Config',
            'description': 'Export camera config to file and import from file',
            'benefit': 'Easy backup and migration',
            'priority': 'MEDIUM'
        },
        {
            'feature': 'Camera Search/Filter',
            'description': 'Search cameras by name, location, company, status',
            'benefit': 'Quick access to specific cameras',
            'priority': 'HIGH'
        },
        {
            'feature': 'Timelapse Creation',
            'description': 'Create timelapse videos from camera feeds',
            'benefit': 'Long-term monitoring visualization',
            'priority': 'LOW'
        },
        {
            'feature': 'Multi-user Support',
            'description': 'Different users with different permissions',
            'benefit': 'Security and access control',
            'priority': 'MEDIUM'
        },
        {
            'feature': 'Mobile App',
            'description': 'Native mobile app for iOS/Android',
            'benefit': 'Monitor on the go',
            'priority': 'LOW'
        },
        {
            'feature': 'Alert System',
            'description': 'Email/SMS alerts for camera offline, motion detected, etc.',
            'benefit': 'Proactive monitoring',
            'priority': 'HIGH'
        }
    ]
    
    return features

def main():
    print("🚀 Comprehensive Project Improvement Analysis")
    print("=" * 60)
    print()
    
    # Analyze different aspects
    webcams_improvements = analyze_webcams_py()
    config_improvements = analyze_config()
    web_improvements = analyze_web_interface()
    new_features = suggest_new_features()
    
    # Print results
    print("\n" + "=" * 60)
    print("📊 IMPROVEMENT REPORT")
    print("=" * 60)
    
    all_improvements = webcams_improvements + config_improvements + web_improvements
    
    if all_improvements:
        print(f"\n🔧 IMPROVEMENTS NEEDED: {len(all_improvements)}")
        
        # Group by priority
        high = [i for i in all_improvements if i['priority'] == 'HIGH']
        medium = [i for i in all_improvements if i['priority'] == 'MEDIUM']
        low = [i for i in all_improvements if i['priority'] == 'LOW']
        
        if high:
            print(f"\n🔴 HIGH PRIORITY ({len(high)}):")
            for imp in high:
                print(f"  [{imp['category']}] {imp['issue']}")
                print(f"    → Fix: {imp['fix']}")
        
        if medium:
            print(f"\n🟡 MEDIUM PRIORITY ({len(medium)}):")
            for imp in medium:
                print(f"  [{imp['category']}] {imp['issue']}")
                print(f"    → Fix: {imp['fix']}")
        
        if low:
            print(f"\n🟢 LOW PRIORITY ({len(low)}):")
            for imp in low:
                print(f"  [{imp['category']}] {imp['issue']}")
                print(f"    → Fix: {imp['fix']}")
    else:
        print("\n✅ No critical improvements needed!")
    
    # Print feature suggestions
    print(f"\n💡 NEW FEATURE SUGGESTIONS: {len(new_features)}")
    
    high_features = [f for f in new_features if f['priority'] == 'HIGH']
    medium_features = [f for f in new_features if f['priority'] == 'MEDIUM']
    low_features = [f for f in new_features if f['priority'] == 'LOW']
    
    if high_features:
        print(f"\n🔴 HIGH PRIORITY FEATURES ({len(high_features)}):")
        for feat in high_features:
            print(f"  • {feat['feature']}")
            print(f"    {feat['description']}")
            print(f"    Benefit: {feat['benefit']}")
    
    if medium_features:
        print(f"\n🟡 MEDIUM PRIORITY FEATURES ({len(medium_features)}):")
        for feat in medium_features:
            print(f"  • {feat['feature']}")
            print(f"    {feat['description']}")
    
    if low_features:
        print(f"\n🟢 LOW PRIORITY FEATURES ({len(low_features)}):")
        for feat in low_features:
            print(f"  • {feat['feature']}")
    
    print("\n" + "=" * 60)
    print("✅ Analysis Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
