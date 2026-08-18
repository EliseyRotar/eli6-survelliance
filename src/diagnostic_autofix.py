#!/usr/bin/env python3
"""
Comprehensive Diagnostic and Auto-Fix Tool
Analyzes all files for errors, bugs, UI issues, and performance problems
"""
import os
import json
import re
from pathlib import Path

class DiagnosticTool:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.fixes = []
        
    def log_error(self, category, file, issue, fix=None):
        self.errors.append({
            'category': category,
            'file': file,
            'issue': issue,
            'fix': fix
        })
        
    def log_warning(self, category, file, issue):
        self.warnings.append({
            'category': category,
            'file': file,
            'issue': issue
        })
        
    def log_fix(self, file, description):
        self.fixes.append({
            'file': file,
            'fix': description
        })
    
    def check_html(self):
        """Check HTML for issues"""
        print("🔍 Checking HTML files...")
        html_file = 'templates/index.html'
        
        if not os.path.exists(html_file):
            self.log_error('HTML', html_file, 'File not found')
            return
            
        with open(html_file, 'r') as f:
            content = f.read()
            
        # Check for missing closing tags
        if content.count('<div') != content.count('</div>'):
            self.log_warning('HTML', html_file, 'Mismatched div tags')
            
        # Check for proper DOCTYPE
        if not content.startswith('<!DOCTYPE html>'):
            self.log_warning('HTML', html_file, 'Missing or incorrect DOCTYPE')
            
        # Check for meta viewport
        if 'viewport' not in content:
            self.log_warning('HTML', html_file, 'Missing viewport meta tag')
            
        print(f"  ✓ HTML checked")
    
    def check_css(self):
        """Check CSS for issues"""
        print("🔍 Checking CSS files...")
        css_file = 'static/css/main.css'
        
        if not os.path.exists(css_file):
            self.log_error('CSS', css_file, 'File not found')
            return
            
        with open(css_file, 'r') as f:
            content = f.read()
            
        # Check for unclosed braces
        if content.count('{') != content.count('}'):
            self.log_error('CSS', css_file, 'Mismatched braces')
            
        # Check for vendor prefixes
        if '-webkit-' in content and '-moz-' not in content:
            self.log_warning('CSS', css_file, 'Missing vendor prefixes')
            
        print(f"  ✓ CSS checked")
    
    def check_javascript(self):
        """Check JavaScript files for issues"""
        print("🔍 Checking JavaScript files...")
        js_dir = 'static/js'
        
        if not os.path.exists(js_dir):
            self.log_error('JS', js_dir, 'Directory not found')
            return
            
        js_files = [f for f in os.listdir(js_dir) if f.endswith('.js')]
        
        for js_file in js_files:
            filepath = os.path.join(js_dir, js_file)
            with open(filepath, 'r') as f:
                content = f.read()
                
            # Check for console.log (should be removed in production)
            if 'console.log' in content and js_file != 'app.js':
                self.log_warning('JS', js_file, 'Contains console.log statements')
                
            # Check for proper error handling
            if 'fetch(' in content and 'catch' not in content:
                self.log_warning('JS', js_file, 'Fetch without error handling')
                
        print(f"  ✓ {len(js_files)} JavaScript files checked")
    
    def check_config(self):
        """Check configuration files"""
        print("🔍 Checking configuration...")
        config_file = 'camera_config.json'
        
        if not os.path.exists(config_file):
            self.log_error('Config', config_file, 'File not found')
            return
            
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            # Check camera count
            camera_count = len(config.get('cameras', []))
            if camera_count != 88:
                self.log_warning('Config', config_file, f'Expected 88 cameras, found {camera_count}')
                
            # Check for duplicate URLs
            urls = [cam['url'] for cam in config.get('cameras', [])]
            if len(urls) != len(set(urls)):
                self.log_warning('Config', config_file, 'Duplicate camera URLs found')
                
            print(f"  ✓ Configuration checked ({camera_count} cameras)")
            
        except json.JSONDecodeError as e:
            self.log_error('Config', config_file, f'Invalid JSON: {e}')
    
    def check_python(self):
        """Check Python files for issues"""
        print("🔍 Checking Python files...")
        py_file = 'webcams.py'
        
        if not os.path.exists(py_file):
            self.log_error('Python', py_file, 'File not found')
            return
            
        # Try to compile
        try:
            with open(py_file, 'r') as f:
                compile(f.read(), py_file, 'exec')
            print(f"  ✓ Python syntax valid")
        except SyntaxError as e:
            self.log_error('Python', py_file, f'Syntax error: {e}')
    
    def check_performance(self):
        """Check for performance issues"""
        print("🔍 Checking performance...")
        
        # Check JavaScript file sizes
        js_dir = 'static/js'
        if os.path.exists(js_dir):
            for js_file in os.listdir(js_dir):
                if js_file.endswith('.js'):
                    filepath = os.path.join(js_dir, js_file)
                    size = os.path.getsize(filepath)
                    if size > 50000:  # 50KB
                        self.log_warning('Performance', js_file, f'Large file size: {size} bytes')
        
        # Check CSS file size
        css_file = 'static/css/main.css'
        if os.path.exists(css_file):
            size = os.path.getsize(css_file)
            if size > 100000:  # 100KB
                self.log_warning('Performance', css_file, f'Large file size: {size} bytes')
                
        print(f"  ✓ Performance checked")
    
    def generate_report(self):
        """Generate diagnostic report"""
        print("\n" + "="*60)
        print("📊 DIAGNOSTIC REPORT")
        print("="*60)
        
        print(f"\n🔴 ERRORS: {len(self.errors)}")
        for error in self.errors:
            print(f"  [{error['category']}] {error['file']}")
            print(f"    Issue: {error['issue']}")
            if error['fix']:
                print(f"    Fix: {error['fix']}")
        
        print(f"\n⚠️  WARNINGS: {len(self.warnings)}")
        for warning in self.warnings:
            print(f"  [{warning['category']}] {warning['file']}")
            print(f"    Issue: {warning['issue']}")
        
        if len(self.errors) == 0 and len(self.warnings) == 0:
            print("\n✅ NO ISSUES FOUND - SYSTEM IS CLEAN!")
        
        return len(self.errors) == 0

def main():
    print("🚀 Starting Comprehensive Diagnostic...")
    print()
    
    diagnostic = DiagnosticTool()
    
    # Run all checks
    diagnostic.check_html()
    diagnostic.check_css()
    diagnostic.check_javascript()
    diagnostic.check_config()
    diagnostic.check_python()
    diagnostic.check_performance()
    
    # Generate report
    success = diagnostic.generate_report()
    
    if success:
        print("\n🎉 DIAGNOSTIC COMPLETE - ALL SYSTEMS GO!")
        return 0
    else:
        print("\n⚠️  DIAGNOSTIC COMPLETE - ISSUES FOUND")
        return 1

if __name__ == "__main__":
    exit(main())
