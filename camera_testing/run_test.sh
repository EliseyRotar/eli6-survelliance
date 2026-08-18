#!/bin/bash
# Camera URL Testing Runner Script

echo "Camera URL Testing Tool"
echo "======================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Install requirements if needed
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip3 install -r requirements.txt
fi

# Run the test
echo "Starting camera tests..."
python3 test_camera_urls.py

echo "Test completed. Check the generated JSON file for detailed results."