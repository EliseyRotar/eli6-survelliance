#!/bin/bash

echo "🔧 Setting up Educational Brute Force Tool Suite"
echo "================================================"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
major_version=$(echo $python_version | cut -d. -f1)
minor_version=$(echo $python_version | cut -d. -f2)

if [ "$major_version" -gt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -ge 6 ]); then
    echo "✅ Python 3.6+ detected: $(python3 --version)"
else
    echo "❌ Python 3.6+ required. Current version: $(python3 --version)"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Make scripts executable
echo "🔐 Making scripts executable..."
chmod +x *.py

# Create initial wordlists
echo "📝 Creating initial wordlists..."
python3 advanced_bruteforce.py --create-wordlists

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Usage:"
echo "  ./launcher.py          - Interactive launcher"
echo "  ./test_server.py       - Start test server"
echo "  ./smart_bruteforce.py  - Smart brute force tool"
echo ""
echo "⚠️  Remember: Use only on systems you own or have permission to test!"
echo ""