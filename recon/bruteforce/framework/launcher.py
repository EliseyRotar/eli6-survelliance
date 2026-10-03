#!/usr/bin/env python3
"""
Educational Brute Force Tool Launcher
Interactive launcher for the brute force tool suite
"""

import os
import sys
import subprocess
from urllib.parse import urlparse

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                Educational Brute Force Suite                 ║
║                                                              ║
║  ⚠️  FOR EDUCATIONAL PURPOSES ONLY                          ║
║  ⚠️  USE ONLY ON SYSTEMS YOU OWN OR HAVE PERMISSION        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import requests
        import bs4
        import flask
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install -r requirements.txt")
        return False

def validate_url(url):
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_user_choice():
    """Get user's tool choice"""
    print("\nAvailable Tools:")
    print("1. 🧪 Test Server - Start local test server with toast notifications")
    print("2. 🎯 Smart Brute Force - Intelligent website detection and testing")
    print("3. ⚙️  Advanced Brute Force - Manual configuration with advanced features")
    print("4. 🎥 Camera/IoT Brute Force - Specialized tool for IP cameras and IoT devices")
    print("5. 🏷️  Brand-Specific Camera Test - Target specific camera manufacturers")
    print("6. 📝 Create Wordlists - Generate comprehensive wordlists")
    print("7. 📋 List Website Configs - Show supported website types")
    print("8. ❌ Exit")
    
    while True:
        try:
            choice = int(input("\nSelect tool (1-8): "))
            if 1 <= choice <= 8:
                return choice
            else:
                print("Please enter a number between 1 and 8")
        except ValueError:
            print("Please enter a valid number")

def run_test_server():
    """Run the test server"""
    print("\n🧪 Starting test server...")
    print("Server will be available at: http://localhost:5000")
    print("Valid test credentials:")
    print("  admin:admin123")
    print("  user:password")
    print("  test:test123")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        subprocess.run([sys.executable, "test_server.py"])
    except KeyboardInterrupt:
        print("\n✅ Server stopped")

def run_smart_bruteforce():
    """Run smart brute force tool"""
    print("\n🎯 Smart Brute Force Tool")
    
    # Get target URL
    while True:
        url = input("Enter target URL (or 'back' to return): ").strip()
        if url.lower() == 'back':
            return
        if validate_url(url):
            break
        print("❌ Invalid URL format. Please include http:// or https://")
    
    # Get options
    print("\nOptions:")
    delay = input("Delay between requests in seconds (default: 2.0): ").strip()
    if not delay:
        delay = "2.0"
    
    custom_wordlists = input("Use custom wordlists? (y/N): ").strip().lower()
    
    # Build command
    cmd = [sys.executable, "smart_bruteforce.py", url, "-d", delay]
    
    if custom_wordlists == 'y':
        username_file = input("Username wordlist file (or press Enter to skip): ").strip()
        password_file = input("Password wordlist file (or press Enter to skip): ").strip()
        
        if username_file and os.path.exists(username_file):
            cmd.extend(["-u", username_file])
        if password_file and os.path.exists(password_file):
            cmd.extend(["-p", password_file])
    
    output_file = input("Save results to file (optional): ").strip()
    if output_file:
        cmd.extend(["-o", output_file])
    
    print(f"\n🚀 Running: {' '.join(cmd)}")
    print("Press Ctrl+C to stop the attack")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n⏹️  Attack stopped by user")

def run_advanced_bruteforce():
    """Run advanced brute force tool"""
    print("\n⚙️  Advanced Brute Force Tool")
    
    # Get target URL
    while True:
        url = input("Enter target URL (or 'back' to return): ").strip()
        if url.lower() == 'back':
            return
        if validate_url(url):
            break
        print("❌ Invalid URL format. Please include http:// or https://")
    
    # Get options
    print("\nConfiguration:")
    auto_discover = input("Auto-discover form fields? (Y/n): ").strip().lower()
    
    cmd = [sys.executable, "advanced_bruteforce.py", url]
    
    if auto_discover != 'n':
        cmd.append("--auto-discover")
    else:
        username_field = input("Username field name (default: username): ").strip()
        password_field = input("Password field name (default: password): ").strip()
        
        if username_field:
            cmd.extend(["--username-field", username_field])
        if password_field:
            cmd.extend(["--password-field", password_field])
    
    delay = input("Delay between requests in seconds (default: 1.0): ").strip()
    if delay:
        cmd.extend(["-d", delay])
    
    threads = input("Number of threads (default: 1, use with caution): ").strip()
    if threads and threads != "1":
        cmd.extend(["-t", threads])
    
    # Wordlists
    username_file = input("Username wordlist file (optional): ").strip()
    password_file = input("Password wordlist file (optional): ").strip()
    
    if username_file and os.path.exists(username_file):
        cmd.extend(["-u", username_file])
    if password_file and os.path.exists(password_file):
        cmd.extend(["-p", password_file])
    
    output_file = input("Save results to file (optional): ").strip()
    if output_file:
        cmd.extend(["-o", output_file])
    
    print(f"\n🚀 Running: {' '.join(cmd)}")
    print("Press Ctrl+C to stop the attack")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n⏹️  Attack stopped by user")

def run_camera_bruteforce():
    """Run camera/IoT brute force tool"""
    print("\n🎥 Camera/IoT Device Brute Force Tool")
    print("Specialized for IP cameras, DVRs, NVRs, and IoT devices")
    
    # Get target URL/IP
    while True:
        target = input("Enter camera IP or URL (or 'back' to return): ").strip()
        if target.lower() == 'back':
            return
        if target:
            # Add http:// if no protocol specified
            if not target.startswith(('http://', 'https://')):
                target = 'http://' + target
            break
        print("❌ Please enter a valid IP address or URL")
    
    # Get options
    print("\nOptions:")
    delay = input("Delay between requests in seconds (default: 2.0): ").strip()
    if not delay:
        delay = "2.0"
    
    discover_only = input("Discovery mode only? (y/N): ").strip().lower()
    
    # Build command
    cmd = [sys.executable, "camera_bruteforce.py", target, "-d", delay]
    
    if discover_only == 'y':
        cmd.append("--discover-only")
    
    custom_creds = input("Use custom credentials file? (y/N): ").strip().lower()
    if custom_creds == 'y':
        creds_file = input("Credentials file path: ").strip()
        if creds_file and os.path.exists(creds_file):
            cmd.extend(["-c", creds_file])
    
    output_file = input("Save results to file (optional): ").strip()
    if output_file:
        cmd.extend(["-o", output_file])
    
    print(f"\n🚀 Running: {' '.join(cmd)}")
    print("Press Ctrl+C to stop the attack")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n⏹️  Attack stopped by user")

def run_brand_specific_bruteforce():
    """Run brand-specific camera brute force tool"""
    print("\n🏷️  Brand-Specific Camera Brute Force Tool")
    print("Target specific camera manufacturers with known credentials")
    
    # List brands first
    print("\nAvailable brands:")
    try:
        subprocess.run([sys.executable, "brand_specific_bruteforce.py", "--list-brands"])
    except Exception as e:
        print(f"❌ Error listing brands: {e}")
        return
    
    # Get target URL/IP
    while True:
        target = input("\nEnter camera IP or URL (or 'back' to return): ").strip()
        if target.lower() == 'back':
            return
        if target:
            # Add http:// if no protocol specified
            if not target.startswith(('http://', 'https://')):
                target = 'http://' + target
            break
        print("❌ Please enter a valid IP address or URL")
    
    # Get brand
    brand = input("Enter camera brand (e.g., hikvision, dahua, axis): ").strip()
    if not brand:
        print("❌ Brand is required")
        return
    
    # Get options
    delay = input("Delay between requests in seconds (default: 2.0): ").strip()
    if not delay:
        delay = "2.0"
    
    # Build command
    cmd = [sys.executable, "brand_specific_bruteforce.py", target, "-b", brand, "-d", delay]
    
    output_file = input("Save results to file (optional): ").strip()
    if output_file:
        cmd.extend(["-o", output_file])
    
    print(f"\n🚀 Running: {' '.join(cmd)}")
    print("Press Ctrl+C to stop the attack")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n⏹️  Attack stopped by user")

def create_wordlists():
    """Create comprehensive wordlists"""
    print("\n📝 Creating comprehensive wordlists...")
    
    try:
        subprocess.run([sys.executable, "smart_bruteforce.py", "--create-wordlists"])
        print("✅ Wordlists created successfully!")
        print("Files created:")
        print("  - usernames.txt")
        print("  - passwords.txt")
    except Exception as e:
        print(f"❌ Error creating wordlists: {e}")

def run_camera_bruteforce():
    """Run camera/IoT brute force tool"""
    print("\n🎥 Camera/IoT Brute Force Tool")
    print("Specialized for IP cameras and IoT devices")
    
    # Get target URL/IP
    while True:
        target = input("Enter camera IP or URL (or 'back' to return): ").strip()
        if target.lower() == 'back':
            return
        
        # Add http:// if no protocol specified
        if not target.startswith(('http://', 'https://')):
            target = 'http://' + target
        
        if validate_url(target):
            break
        print("❌ Invalid URL/IP format")
    
    # Get options
    print("\nOptions:")
    delay = input("Delay between requests in seconds (default: 2.0): ").strip()
    if not delay:
        delay = "2.0"
    
    discover_only = input("Only discover camera interface? (y/N): ").strip().lower()
    
    # Build command
    cmd = [sys.executable, "camera_bruteforce.py", target, "-d", delay]
    
    if discover_only == 'y':
        cmd.append("--discover-only")
    
    custom_creds = input("Use custom credentials file? (y/N): ").strip().lower()
    if custom_creds == 'y':
        creds_file = input("Credentials file path: ").strip()
        if creds_file and os.path.exists(creds_file):
            cmd.extend(["-c", creds_file])
    
    output_file = input("Save results to file (optional): ").strip()
    if output_file:
        cmd.extend(["-o", output_file])
    
    print(f"\n🚀 Running: {' '.join(cmd)}")
    if not discover_only == 'y':
        print("⚠️  This will test camera default credentials")
        print("Press Ctrl+C to stop the attack")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n⏹️  Attack stopped by user")

def list_configs():
    """List available website configurations"""
    print("\n📋 Available website configurations:")
    
    try:
        subprocess.run([sys.executable, "smart_bruteforce.py", "--list-configs"])
    except Exception as e:
        print(f"❌ Error listing configurations: {e}")

def main():
    print_banner()
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Check if we're in the right directory
    if not os.path.exists("smart_bruteforce.py"):
        print("❌ Please run this script from the bruteforce directory")
        return
    
    while True:
        choice = get_user_choice()
        
        if choice == 1:
            run_test_server()
        elif choice == 2:
            run_smart_bruteforce()
        elif choice == 3:
            run_advanced_bruteforce()
        elif choice == 4:
            run_camera_bruteforce()
        elif choice == 5:
            run_brand_specific_bruteforce()
        elif choice == 6:
            create_wordlists()
        elif choice == 7:
            list_configs()
        elif choice == 8:
            print("\n👋 Goodbye! Remember to use these tools responsibly.")
            break
        
        if choice != 8:
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()