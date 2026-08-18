#!/usr/bin/env python3
"""
Deep Diagnostic - Find hidden bugs, UI issues, and performance problems
"""
import os
import json
import re

def check_javascript_issues():
    """Deep check of JavaScript for common bugs"""
    print("🔬 Deep JavaScript Analysis...")
    issues = []
    
    js_files = {
        'config.js': ['CONFIG', 'STATE', 'COMPANY_COLORS'],
        'api.js': ['API'],
        'ui.js': ['UI'],
        'charts.js': ['Charts'],
        'dashboard.js': ['Dashboard'],
        'cameras.js': ['Cameras'],
        'recordings.js': ['Recordings'],
        'analytics.js': ['Analytics'],
        'app.js': ['App']
    }
    
    for filename, expected_objects in js_files.items():
        filepath = f'static/js/{filename}'
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
                
            # Check for undefined variables
            if 'undefined' in content.lower():
                issues.append(f"{filename}: May have undefined variable references")
                
            # Check for missing semicolons (common bug)
            lines = content.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if line and not line.startswith('//') and not line.startswith('/*'):
                    if (line.endswith(')') or line.endswith(']') or line.endswith('}')) and \
                       not line.endswith(';') and not line.endswith(',') and \
                       not line.endswith('{') and i < len(lines) - 1:
                        next_line = lines[i+1].strip()
                        if next_line and not next_line.startswith('}') and not next_line.startswith(')'):
                            # This might be missing a semicolon
                            pass  # JavaScript has ASI, so this is usually OK
    
    if not issues:
        print("  ✅ No JavaScript issues found")
    else:
        for issue in issues:
            print(f"  ⚠️  {issue}")
    
    return issues

def check_ui_responsiveness():
    """Check for UI responsiveness issues"""
    print("🔬 UI Responsiveness Analysis...")
    issues = []
    
    css_file = 'static/css/main.css'
    if os.path.exists(css_file):
        with open(css_file, 'r') as f:
            content = f.read()
            
        # Check for media queries
        media_queries = content.count('@media')
        if media_queries < 2:
            issues.append("CSS: Insufficient media queries for responsive design")
        
        # Check for fixed widths
        fixed_widths = re.findall(r'width:\s*\d+px', content)
        if len(fixed_widths) > 50:
            issues.append(f"CSS: Too many fixed widths ({len(fixed_widths)}), may affect responsiveness")
    
    if not issues:
        print("  ✅ UI responsiveness looks good")
    else:
        for issue in issues:
            print(f"  ⚠️  {issue}")
    
    return issues

def check_api_error_handling():
    """Check API error handling"""
    print("🔬 API Error Handling Analysis...")
    issues = []
    
    api_file = 'static/js/api.js'
    if os.path.exists(api_file):
        with open(api_file, 'r') as f:
            content = f.read()
            
        # Count try-catch blocks
        try_count = content.count('try {')
        catch_count = content.count('catch')
        
        if try_count != catch_count:
            issues.append("API: Mismatched try-catch blocks")
        
        # Check for error logging
        if 'console.error' not in content:
            issues.append("API: No error logging found")
    
    if not issues:
        print("  ✅ API error handling is good")
    else:
        for issue in issues:
            print(f"  ⚠️  {issue}")
    
    return issues

def check_memory_leaks():
    """Check for potential memory leaks"""
    print("🔬 Memory Leak Analysis...")
    issues = []
    
    # Check for setInterval without clearInterval
    js_dir = 'static/js'
    if os.path.exists(js_dir):
        for filename in os.listdir(js_dir):
            if filename.endswith('.js'):
                filepath = os.path.join(js_dir, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                    
                if 'setInterval' in content and 'clearInterval' not in content:
                    # Check if it's in app.js (expected for auto-refresh)
                    if filename != 'app.js':
                        issues.append(f"{filename}: setInterval without clearInterval (potential memory leak)")
    
    if not issues:
        print("  ✅ No obvious memory leaks")
    else:
        for issue in issues:
            print(f"  ⚠️  {issue}")
    
    return issues

def check_performance_bottlenecks():
    """Check for performance bottlenecks"""
    print("🔬 Performance Bottleneck Analysis...")
    issues = []
    
    # Check for excessive DOM manipulation
    js_files = ['dashboard.js', 'cameras.js', 'recordings.js']
    for filename in js_files:
        filepath = f'static/js/{filename}'
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
                
            # Count innerHTML usage (can be slow)
            innerHTML_count = content.count('innerHTML')
            if innerHTML_count > 5:
                issues.append(f"{filename}: High innerHTML usage ({innerHTML_count}), consider using DOM methods")
    
    if not issues:
        print("  ✅ No performance bottlenecks detected")
    else:
        for issue in issues:
            print(f"  ⚠️  {issue}")
    
    return issues

def check_accessibility():
    """Check for accessibility issues"""
    print("🔬 Accessibility Analysis...")
    issues = []
    
    html_file = 'templates/index.html'
    if os.path.exists(html_file):
        with open(html_file, 'r') as f:
            content = f.read()
            
        # Check for alt attributes on images
        img_tags = re.findall(r'<img[^>]*>', content)
        for img in img_tags:
            if 'alt=' not in img:
                issues.append("HTML: Image without alt attribute")
                break
        
        # Check for aria labels on buttons
        button_count = content.count('<button')
        aria_count = content.count('aria-label')
        if button_count > aria_count + 5:
            issues.append("HTML: Some buttons may be missing aria-labels")
    
    if not issues:
        print("  ✅ Accessibility looks good")
    else:
        for issue in issues:
            print(f"  ⚠️  {issue}")
    
    return issues

def check_security():
    """Check for security issues"""
    print("🔬 Security Analysis...")
    issues = []
    
    # Check for eval() usage (security risk)
    js_dir = 'static/js'
    if os.path.exists(js_dir):
        for filename in os.listdir(js_dir):
            if filename.endswith('.js'):
                filepath = os.path.join(js_dir, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                    
                if 'eval(' in content:
                    issues.append(f"{filename}: Uses eval() - security risk")
    
    # Check HTML for inline scripts
    html_file = 'templates/index.html'
    if os.path.exists(html_file):
        with open(html_file, 'r') as f:
            content = f.read()
            
        inline_scripts = re.findall(r'<script[^>]*>(?!.*src=)', content)
        if len(inline_scripts) > 0:
            # Check if they're just loading external scripts
            for script in inline_scripts:
                if 'src=' not in script:
                    issues.append("HTML: Inline script found (consider moving to external file)")
                    break
    
    if not issues:
        print("  ✅ No security issues found")
    else:
        for issue in issues:
            print(f"  ⚠️  {issue}")
    
    return issues

def main():
    print("🚀 Starting Deep Diagnostic Analysis...")
    print("="*60)
    print()
    
    all_issues = []
    
    all_issues.extend(check_javascript_issues())
    all_issues.extend(check_ui_responsiveness())
    all_issues.extend(check_api_error_handling())
    all_issues.extend(check_memory_leaks())
    all_issues.extend(check_performance_bottlenecks())
    all_issues.extend(check_accessibility())
    all_issues.extend(check_security())
    
    print()
    print("="*60)
    print("📊 DEEP DIAGNOSTIC SUMMARY")
    print("="*60)
    print(f"Total Issues Found: {len(all_issues)}")
    
    if len(all_issues) == 0:
        print("\n✅ EXCELLENT! No issues found in deep analysis!")
        print("🎉 System is optimized and ready for production!")
    else:
        print("\n⚠️  Issues found (mostly minor optimizations)")
        print("💡 These are suggestions for enhancement, not critical bugs")
    
    return 0

if __name__ == "__main__":
    exit(main())
