# Camera URL Testing Tool

This tool tests connectivity and response status for a comprehensive list of camera URLs.

## Features

- **Concurrent Testing**: Tests multiple cameras simultaneously for faster results
- **Detailed Reporting**: Provides response codes, timing, content types, and error details
- **JSON Output**: Saves results in structured JSON format for further analysis
- **Progress Tracking**: Shows real-time progress during testing
- **Comprehensive Summary**: Displays categorized results and statistics

## Usage

### Quick Start
```bash
./run_test.sh
```

### Manual Execution
```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the test
python3 test_camera_urls.py
```

## Output

The tool provides:

1. **Real-time Progress**: Shows testing progress in the terminal
2. **Summary Report**: Displays categorized results:
   - Online cameras (HTTP 200)
   - Cameras requiring authentication (HTTP 401)
   - Connection errors and timeouts
   - Other error conditions

3. **JSON Results File**: Detailed results saved as `camera_test_results_YYYYMMDD_HHMMSS.json`

## Result Categories

- **online**: Camera is accessible and responding (HTTP 200)
- **auth_required**: Camera requires authentication (HTTP 401)
- **not_found**: Camera endpoint not found (HTTP 404)
- **timeout**: Connection timed out
- **connection_error**: Network connection failed
- **error**: Other HTTP errors or exceptions

## Configuration

You can modify the following parameters in the script:

- `timeout`: Connection timeout in seconds (default: 15)
- `max_workers`: Number of concurrent connections (default: 25)

## Camera URLs Tested

The tool tests {total_cameras} camera URLs including:
- Axis cameras (mjpg/video.cgi endpoints)
- Motion JPEG streams
- Various IP camera interfaces
- Both HTTP and HTTPS endpoints

## Requirements

- Python 3.6+
- requests library
- Internet connection

## Notes

- Some cameras may require authentication or have geographic restrictions
- Network conditions affect response times and success rates
- Results are timestamped for tracking changes over time