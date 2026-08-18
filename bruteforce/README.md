# Advanced Educational Brute Force Tool Suite

## ⚠️ CRITICAL DISCLAIMER

This tool suite is created for **EDUCATIONAL PURPOSES ONLY**.

### Legal Use Only:

- ✅ Your own applications and systems
- ✅ Systems you have explicit written permission to test
- ✅ Controlled testing environments
- ✅ Security research with proper authorization

### Illegal Use:

- ❌ **NEVER** use on systems you don't own
- ❌ **NEVER** use without explicit written permission
- ❌ **NEVER** use for malicious purposes
- ❌ Unauthorized access is a crime in most jurisdictions

**You are solely responsible for how you use these tools. The authors assume no liability for misuse.**

## Tool Suite Overview

### 1. **bruteforce_test.py** - Basic brute force tool

Simple tool for testing your own login systems with toast popups.

### 2. **advanced_bruteforce.py** - Advanced brute force tool

Enhanced version with:

- Multi-threading support
- CSRF token handling
- User agent rotation
- Form field auto-discovery
- Smart success detection
- Comprehensive logging

### 3. **smart_bruteforce.py** - Intelligent website detector

Most advanced tool featuring:

- Automatic website type detection (WordPress, Drupal, Joomla, etc.)
- Targeted wordlist generation
- Login page discovery
- Form analysis and field extraction
- Website-specific configurations

### 4. **camera_bruteforce.py** - Camera/IoT device specialist

Specialized tool for IP cameras and IoT devices:

- HTTP Basic Authentication testing
- Form-based login testing
- Camera-specific credential database
- Interface discovery
- IoT device detection

### 5. **test_server.py** - Flask test server

Local server for safe testing with toast notifications.

### 6. **test_login.html** - Interactive test interface

Beautiful web interface with animated toast popups.

### 6. **website_configs.json** - Website configurations

Pre-configured settings for popular CMS and frameworks.

## Installation & Setup

### Prerequisites

```bash
pip install requests beautifulsoup4 flask
```

### Quick Start

1. **Test locally first:**

   ```bash
   cd bruteforce
   python test_server.py
   ```

   Open http://localhost:5000 in your browser

2. **Create wordlists:**

   ```bash
   python smart_bruteforce.py --create-wordlists
   ```

3. **Test against your local server:**
   ```bash
   python smart_bruteforce.py http://localhost:5000/login
   ```

## Usage Examples

### Camera/IoT Device Testing

```bash
# Test IP camera with default credentials
python camera_bruteforce.py http://192.168.1.100

# Test with custom credentials file
python camera_bruteforce.py http://192.168.1.100 -c my_camera_creds.txt

# Discovery mode only (find interfaces)
python camera_bruteforce.py http://192.168.1.100 --discover-only

# Slower testing for sensitive devices
python camera_bruteforce.py http://192.168.1.100 -d 5.0
```

### Basic Testing (Your Own Sites)

```bash
# Simple test with default wordlists
python smart_bruteforce.py https://your-test-site.com

# With custom wordlists
python smart_bruteforce.py https://your-test-site.com -u users.txt -p passwords.txt

# Slower, more respectful testing
python smart_bruteforce.py https://your-test-site.com -d 5.0

# Save results to file
python smart_bruteforce.py https://your-test-site.com -o results.json
```

### Advanced Options

```bash
# Skip auto-detection, use specific type
python smart_bruteforce.py https://your-wordpress-site.com --website-type wordpress

# Multi-threaded (use carefully!)
python smart_bruteforce.py https://your-test-site.com -t 3 -d 1.0

# List available website configurations
python smart_bruteforce.py --list-configs
```

### Manual Advanced Tool

```bash
# Auto-discover form fields
python advanced_bruteforce.py https://your-site.com/login --auto-discover

# Manual field specification
python advanced_bruteforce.py https://your-site.com/login --username-field email --password-field passwd

# Create comprehensive wordlists
python advanced_bruteforce.py --create-wordlists
```

## Supported Website Types

The smart tool automatically detects and configures for:

- **WordPress** - Detects wp-content, wp-admin paths
- **Drupal** - Identifies Drupal-specific headers and paths
- **Joomla** - Recognizes Joomla administrator interface
- **Laravel** - Detects CSRF tokens and Laravel patterns
- **Django** - Identifies Django admin interface
- **Flask** - Generic Flask application detection
- **phpMyAdmin** - Database administration interface
- **cPanel** - Hosting control panel
- **Plesk** - Alternative hosting control panel
- **Generic** - Fallback for unknown systems

## Features

### Smart Detection

- Automatically identifies website type
- Discovers login pages and forms
- Extracts form field names
- Handles CSRF tokens
- Generates targeted wordlists

### Security Features

- Configurable delays to avoid overwhelming servers
- User agent rotation
- Session management
- Respectful request patterns
- Comprehensive logging

### Success Detection

- HTTP status code analysis
- Response content analysis
- Redirect detection
- Cookie analysis
- JSON response parsing

## Configuration Files

### website_configs.json

Contains pre-configured settings for popular platforms:

```json
{
  "wordpress": {
    "login_path": "/wp-login.php",
    "username_field": "log",
    "password_field": "pwd",
    "success_indicators": ["dashboard", "wp-admin"],
    "failure_indicators": ["incorrect username"]
  }
}
```

### Custom Wordlists

Create targeted wordlists:

```bash
# Usernames
echo -e "admin\nuser\ntest" > custom_users.txt

# Passwords
echo -e "password\n123456\nadmin" > custom_passwords.txt

# Use them
python smart_bruteforce.py https://your-site.com -u custom_users.txt -p custom_passwords.txt
```

## Testing Your Own Applications

### 1. Local Development

```bash
# Start test server
python test_server.py

# Test in browser (watch toast notifications)
open http://localhost:5000

# Run automated test
python smart_bruteforce.py http://localhost:5000/login
```

### 2. Staging Environment

```bash
# Test your staging site with delays
python smart_bruteforce.py https://staging.yoursite.com -d 3.0

# Monitor server logs simultaneously
tail -f /var/log/nginx/access.log
```

### 3. Production Testing (With Permission)

```bash
# Very slow, respectful testing
python smart_bruteforce.py https://yoursite.com -d 10.0 -t 1

# Limited wordlist for production
python smart_bruteforce.py https://yoursite.com -u small_users.txt -p small_passwords.txt
```

## Security Best Practices

### For Testers

- Always get written permission before testing
- Use appropriate delays (2+ seconds)
- Monitor target server resources
- Test during low-traffic periods
- Document all testing activities
- Respect rate limiting and blocks

### For Defenders

- Implement account lockouts
- Use CAPTCHA after failed attempts
- Monitor for brute force patterns
- Implement rate limiting
- Log all authentication attempts
- Use strong password policies
- Enable two-factor authentication

## Command Reference

### smart_bruteforce.py

```
usage: smart_bruteforce.py [-h] [-u USERNAMES] [-p PASSWORDS] [-d DELAY]
                          [-t THREADS] [--timeout TIMEOUT] [--skip-detection]
                          [--website-type {wordpress,drupal,joomla,...}]
                          [-o OUTPUT] [--create-wordlists] [--list-configs]
                          url

Arguments:
  url                    Target website URL

Options:
  -u, --usernames       Custom username wordlist file
  -p, --passwords       Custom password wordlist file
  -d, --delay          Delay between requests (default: 2.0 seconds)
  -t, --threads        Number of threads (use with caution)
  --timeout            Request timeout in seconds
  --skip-detection     Skip automatic website detection
  --website-type       Manually specify website type
  -o, --output         Output file for results (JSON)
  --create-wordlists   Create comprehensive wordlists
  --list-configs       List available website configurations
```

### advanced_bruteforce.py

```
usage: advanced_bruteforce.py [-h] [-u USERNAMES] [-p PASSWORDS] [-d DELAY]
                             [-t THREADS] [--timeout TIMEOUT] [--auto-discover]
                             [--username-field USERNAME_FIELD]
                             [--password-field PASSWORD_FIELD]
                             [--create-wordlists] [-o OUTPUT]
                             url

Similar options to smart_bruteforce.py with additional:
  --auto-discover      Automatically discover login form fields
  --username-field     Username field name (if not auto-discovering)
  --password-field     Password field name (if not auto-discovering)
```

## Monitoring and Results

### View Results

```bash
# Check saved results
cat results.json | jq '.'

# Monitor server stats during test
curl http://localhost:5000/stats

# Reset test server stats
curl -X POST http://localhost:5000/reset-stats
```

### Log Analysis

The tools provide detailed logging:

- Request/response details
- Success/failure indicators
- Timing information
- Error messages
- Progress tracking

## Troubleshooting

### Common Issues

**No login pages found:**

- Check if the URL is correct
- Try specifying the login path manually
- Use `--skip-detection` for custom forms

**CSRF token errors:**

- The tool handles most CSRF implementations
- Check if the site uses custom token names
- Monitor network requests in browser dev tools

**Rate limiting:**

- Increase delay with `-d` option
- Reduce thread count
- Check server response headers

**False positives/negatives:**

- Customize success/failure indicators
- Check response content manually
- Adjust detection logic if needed

## Educational Value

This tool suite teaches:

- Web application security testing
- HTTP request/response analysis
- Form handling and CSRF protection
- Rate limiting and defensive measures
- Automated security testing
- Responsible disclosure practices

## Contributing

To add support for new website types:

1. Add configuration to `website_configs.json`
2. Update detection patterns in `smart_bruteforce.py`
3. Test thoroughly on your own systems
4. Submit pull request with documentation

## Legal Notice

These tools are provided for educational and authorized testing purposes only. Users must:

- Obtain proper authorization before testing
- Comply with all applicable laws
- Use tools responsibly and ethically
- Respect system resources and availability

Unauthorized access to computer systems is illegal. The authors are not responsible for misuse of these tools.

## Support

For educational use and legitimate security testing questions:

- Review the documentation thoroughly
- Test on your own systems first
- Follow responsible disclosure practices
- Respect others' systems and data

Remember: With great power comes great responsibility. Use these tools to make the internet more secure, not less.
