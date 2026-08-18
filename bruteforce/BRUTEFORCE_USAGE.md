# Educational Brute Force Tool Usage Guide

## ⚠️ IMPORTANT DISCLAIMER

This tool is created for **educational purposes only**. Use it only on:

- Your own applications and systems
- Systems you have explicit written permission to test
- Controlled testing environments

**Never use this tool on systems you don't own or lack permission to test.**

## Files Created

1. **bruteforce_test.py** - Main brute force testing tool
2. **test_server.py** - Flask server for testing
3. **test_login.html** - HTML page with JS toast popups
4. **BRUTEFORCE_USAGE.md** - This usage guide

## Quick Start

### 1. Install Dependencies

```bash
pip install flask requests
```

### 2. Start the Test Server

```bash
python test_server.py
```

The server will start on `http://localhost:5000`

### 3. Test the Web Interface

Open your browser and go to `http://localhost:5000` to see the login page with toast popups.

Valid test credentials:

- admin:admin123
- user:password
- test:test123

### 4. Run the Brute Force Tool

#### Create default wordlists:

```bash
python bruteforce_test.py --create-wordlists
```

#### Test against your server:

```bash
python bruteforce_test.py http://localhost:5000/login
```

#### Use custom wordlists:

```bash
python bruteforce_test.py http://localhost:5000/login -u usernames.txt -p passwords.txt
```

#### Add delay between requests:

```bash
python bruteforce_test.py http://localhost:5000/login -d 2.0
```

## Tool Features

### Brute Force Tool (bruteforce_test.py)

- Tests username/password combinations
- Configurable delay between requests
- Custom wordlist support
- Success detection based on HTTP status and content
- Progress tracking and results summary

### Test Server (test_server.py)

- Simple Flask-based login system
- Multiple valid test accounts
- Login attempt logging
- Statistics endpoint (`/stats`)
- Reset statistics endpoint (`/reset-stats`)

### Web Interface (test_login.html)

- Modern, responsive design
- Animated toast notifications
- Real-time statistics tracking
- Success/failure indicators

## Command Line Options

```bash
python bruteforce_test.py [URL] [OPTIONS]

Arguments:
  url                    Target login URL

Options:
  -u, --usernames       Username wordlist file
  -p, --passwords       Password wordlist file
  -d, --delay          Delay between requests (seconds, default: 1.0)
  --create-wordlists   Create default wordlists
  -h, --help           Show help message
```

## Example Usage Scenarios

### 1. Test Your Toast Popup System

1. Start the test server
2. Open the web interface in your browser
3. Try different login combinations manually
4. Watch the toast notifications appear

### 2. Automated Testing

1. Run the brute force tool against your server
2. Monitor the server logs
3. Check the `/stats` endpoint for attempt statistics
4. Verify your rate limiting and security measures

### 3. Custom Testing

1. Modify the valid credentials in `test_server.py`
2. Create custom wordlists for your specific test case
3. Adjust the success detection logic in `bruteforce_test.py`

## Security Testing Tips

- Test rate limiting by reducing the delay (`-d 0.1`)
- Monitor server logs for suspicious activity detection
- Test account lockout mechanisms
- Verify CAPTCHA integration (if implemented)
- Check for proper error message handling

## Monitoring Results

### View Statistics

```bash
curl http://localhost:5000/stats
```

### Reset Statistics

```bash
curl -X POST http://localhost:5000/reset-stats
```

## Customization

### Adding New Test Accounts

Edit the `VALID_CREDENTIALS` dictionary in `test_server.py`:

```python
VALID_CREDENTIALS = {
    'admin': 'admin123',
    'user': 'password',
    'test': 'test123',
    'newuser': 'newpass'  # Add your test account
}
```

### Custom Success Detection

Modify the `check_success()` method in `bruteforce_test.py` to match your application's response patterns.

### Custom Wordlists

Create your own username and password files:

```bash
echo -e "admin\nroot\nuser" > custom_users.txt
echo -e "password\n123456\nadmin" > custom_passes.txt
python bruteforce_test.py http://localhost:5000/login -u custom_users.txt -p custom_passes.txt
```

## Educational Value

This tool demonstrates:

- HTTP request handling and session management
- Response analysis and pattern matching
- Rate limiting and timing considerations
- Web security testing methodologies
- Toast notification systems and user feedback

Remember: Always use responsibly and only on systems you own or have permission to test!
