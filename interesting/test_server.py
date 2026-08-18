#!/usr/bin/env python3
"""
Simple Flask server for testing the brute force tool
Educational purposes only
"""

from flask import Flask, request, jsonify, render_template_string, send_from_directory
import os
import json
from datetime import datetime

app = Flask(__name__)

# Valid credentials for testing
VALID_CREDENTIALS = {
    'admin': 'admin123',
    'user': 'password',
    'test': 'test123'
}

# Track login attempts
login_attempts = []

@app.route('/')
def index():
    """Serve the test login page"""
    try:
        with open('test_login.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "test_login.html not found. Please run the script from the correct directory."

@app.route('/login', methods=['POST'])
def login():
    """Handle login attempts"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    # Log the attempt
    attempt = {
        'timestamp': datetime.now().isoformat(),
        'username': username,
        'password': password,
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', '')
    }
    login_attempts.append(attempt)
    
    # Check credentials
    if username in VALID_CREDENTIALS and VALID_CREDENTIALS[username] == password:
        return jsonify({
            'success': True,
            'message': f'Welcome back, {username}!',
            'redirect': '/dashboard'
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': 'Invalid username or password'
        }), 401

@app.route('/dashboard')
def dashboard():
    """Simple dashboard page"""
    return """
    <html>
    <head><title>Dashboard</title></head>
    <body>
        <h1>🎉 Login Successful!</h1>
        <p>You have successfully logged in.</p>
        <a href="/">Back to Login</a>
    </body>
    </html>
    """

@app.route('/stats')
def stats():
    """Show login attempt statistics"""
    total_attempts = len(login_attempts)
    successful_attempts = sum(1 for attempt in login_attempts 
                            if attempt['username'] in VALID_CREDENTIALS 
                            and VALID_CREDENTIALS[attempt['username']] == attempt['password'])
    
    return jsonify({
        'total_attempts': total_attempts,
        'successful_attempts': successful_attempts,
        'failed_attempts': total_attempts - successful_attempts,
        'success_rate': (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0,
        'recent_attempts': login_attempts[-10:]  # Last 10 attempts
    })

@app.route('/reset-stats', methods=['POST'])
def reset_stats():
    """Reset login attempt statistics"""
    global login_attempts
    login_attempts = []
    return jsonify({'message': 'Statistics reset successfully'})

if __name__ == '__main__':
    print("Starting test server...")
    print("Valid credentials for testing:")
    for username, password in VALID_CREDENTIALS.items():
        print(f"  {username}:{password}")
    print("\nServer will run on http://localhost:5000")
    print("Use this URL with the brute force tool")
    print("\nEndpoints:")
    print("  / - Login page")
    print("  /login - Login endpoint (POST)")
    print("  /stats - View attempt statistics")
    print("  /reset-stats - Reset statistics (POST)")
    
    app.run(debug=True, host='0.0.0.0', port=5000)