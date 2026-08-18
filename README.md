# ELI6 Surveillance System

A professional Python-based multi-camera surveillance system for monitoring IP cameras in real time, featuring a modern web dashboard, frame caching, parallel fetching, and video recording.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-2.3+-black?logo=flask)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green?logo=opencv)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

- **Multi-camera monitoring** — support for 200+ IP cameras simultaneously
- **Web dashboard** — real-time browser interface with camera grid, groups, search, and analytics
- **Frame caching** — LRU memory cache with configurable size limit for fast frame delivery
- **Parallel fetching** — threaded camera polling via `ThreadPoolExecutor`
- **Video recording** — record individual camera streams to AVI files
- **Camera groups** — organise cameras into named groups
- **Search & filter** — live search across all cameras by name or location
- **Configuration UI** — add, edit, and remove cameras from the browser at `/config`
- **JSON config** — manage cameras via `camera_config.json`
- **Performance metrics** — live CPU, disk, and memory stats in the header
- **Screenshot capture** — save the current grid view with a timestamp
- **Connection management** — automatic reconnection and manual reset

---

## Project Structure

```
eli6-survelliance/
├── src/
│   ├── webcams.py                  # Main Flask application
│   ├── test_cameras.py             # Basic camera connectivity test
│   ├── test_camera_connections.py  # Advanced connection diagnostics
│   ├── verify_config.py            # Validate camera_config.json
│   ├── check_camera_status.py      # Live camera status checker
│   ├── check_loading_status.py     # Loading performance checker
│   ├── debug_camera_loading.py     # Debug camera loading issues
│   ├── fix_stuck_cameras.py        # Fix cameras stuck in loading state
│   ├── add_new_cameras.py          # Bulk add cameras to config
│   ├── parse_new_cameras.py        # Parse camera lists from text
│   └── project_improvements.py    # Project enhancement utilities
├── camera_testing/
│   ├── test_camera_urls.py         # Batch URL tester with concurrency
│   ├── analyze_results.py          # Analyze test results
│   ├── extract_working_cameras.py  # Filter working cameras from results
│   ├── run_test.sh                 # Shell wrapper for camera tests
│   └── README.md                   # Camera testing documentation
├── templates/
│   ├── index.html                  # Main dashboard template
│   └── config.html                 # Camera configuration UI
├── static/
│   ├── css/main.css                # Main stylesheet (dark theme)
│   └── js/
│       ├── cameras.js              # Camera grid and stream handling
│       ├── dashboard.js            # Dashboard widgets and stats
│       ├── groups.js               # Camera group management
│       ├── search.js               # Live search functionality
│       ├── recordings.js           # Recording controls
│       ├── charts.js               # Performance charts (Chart.js)
│       ├── api.js                  # API client helpers
│       ├── ui.js                   # UI utilities
│       ├── performance.js          # Performance monitoring
│       ├── error-handler.js        # Global error handling
│       ├── analytics.js            # Analytics module
│       ├── app.js                  # App bootstrap
│       ├── config.js               # Client-side config
│       └── main.js                 # Entry point
├── docs/                           # Development notes and changelogs
├── recordings/                     # Recorded camera streams (gitignored)
├── backups/                        # Config backups (gitignored)
├── cache/                          # Frame cache (gitignored)
├── camera_config.json              # Active camera configuration
├── camera_config.example.json      # Example config template
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── CONTRIBUTING.md                 # Contribution guide
└── LICENSE                         # MIT License
```

---

## Requirements

- Python 3.8+
- pip

Install dependencies:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install opencv-python pillow requests numpy flask psutil
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/EliseyRotar/eli6-survelliance.git
cd eli6-survelliance
```

### 2. Set up a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate      # Linux / macOS
# venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 3. Configure cameras

Copy the example config and edit it with your camera details:

```bash
cp camera_config.example.json camera_config.json
```

```json
{
  "cameras": [
    {
      "url": "http://192.168.1.100/web/tmpfs/snap.jpg",
      "username": "admin",
      "password": "admin",
      "name": "Front Door",
      "enabled": true,
      "type": "image"
    }
  ]
}
```

Supported `type` values: `"image"` (MJPEG snapshot URL) or `"video"` (RTSP stream).

### 4. Test cameras (optional)

```bash
python3 camera_testing/test_camera_urls.py
python3 src/verify_config.py
```

### 5. Run the application

```bash
python3 src/webcams.py
```

Open your browser:
- Dashboard: `http://localhost:5000`
- Config UI: `http://localhost:5000/config`

---

## Configuration

Edit `camera_config.json` or use the web UI at `/config`.

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Camera snapshot or stream URL |
| `username` | string | HTTP Basic Auth username |
| `password` | string | HTTP Basic Auth password |
| `name` | string | Display name |
| `enabled` | bool | Enable/disable this camera |
| `type` | string | `"image"` or `"video"` |

### Performance Tuning

| Setting | Default | Description |
|---------|---------|-------------|
| `timeout` | 10 | Request timeout in seconds |
| `delay` | 1.0 | Refresh interval per camera (seconds) |
| `cam_width` | 320 | Camera frame width |
| `cam_height` | 240 | Camera frame height |
| `use_threading` | true | Enable parallel camera fetching |
| `max_workers` | 20 | ThreadPoolExecutor worker count |
| `cache_memory_mb` | 256 | LRU frame cache size (MB) |

---

## Web Interface

| URL | Description |
|-----|-------------|
| `/` | Main dashboard with camera grid |
| `/config` | Camera configuration panel |
| `/api/cameras` | JSON list of all cameras and status |
| `/api/camera/<id>/frame` | Latest frame for a specific camera |
| `/api/stats` | System performance metrics |
| `/api/camera/<id>/record` | Start/stop recording for a camera |

---

## Common Camera URL Formats

| Brand | URL Pattern |
|-------|-------------|
| Generic | `http://ip:port/path/to/snap.jpg` |
| Axis | `http://ip/axis-cgi/jpg/image.cgi` |
| Hikvision | `http://ip/ISAPI/Streaming/channels/1/picture` |
| Dahua | `http://ip/cgi-bin/snapshot.cgi` |
| Foscam | `http://ip/cgi-bin/CGIProxy.fcgi?cmd=snapPicture2` |
| RTSP | `rtsp://user:pass@ip:554/stream` |

---

## Troubleshooting

**Cameras show "OFFLINE" or "ERROR"**
- Run `python3 camera_testing/test_camera_urls.py` to test individual connectivity
- Verify the URL, username, and password in `camera_config.json`
- Increase `timeout` for slow or distant cameras

**Poor performance with many cameras**
- Reduce `cam_width` / `cam_height`
- Increase `delay` to poll less frequently
- Increase `max_workers` for faster parallel fetching
- Reduce `cache_memory_mb` if RAM is limited

**Cameras stuck on loading**
- Run `python3 src/fix_stuck_cameras.py`
- Run `python3 src/check_loading_status.py` for diagnostics

**Application crashes or hangs**
- Check `surveillance.log` for error details
- Run `python3 src/deep_diagnostic.py` for a full diagnostic report

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.
