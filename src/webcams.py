import cv2
import numpy as np
import requests
from io import BytesIO
from PIL import Image
import time
import threading
import json
import os
from flask import Flask, render_template, jsonify, request, Response
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, PriorityQueue
import logging
from datetime import datetime, timedelta
import psutil
from collections import deque, defaultdict
import hashlib
from threading import Lock
import gc

# Configuration file path
CONFIG_FILE = "camera_config.json"
BACKUP_DIR = "backups"
RECORDINGS_DIR = "recordings"
CACHE_DIR = "cache"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('surveillance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create directories
for directory in [BACKUP_DIR, RECORDINGS_DIR, CACHE_DIR]:
    os.makedirs(directory, exist_ok=True)

class FrameCache:
    """Advanced frame caching with LRU and memory management"""
    def __init__(self, max_memory_mb=256):  # Reduced from 512MB for 277 cameras
        self.max_memory = max_memory_mb * 1024 * 1024  # Convert to bytes
        self.cache = {}
        self.access_times = {}
        self.memory_usage = 0
        self.lock = Lock()
        
    def get(self, key):
        with self.lock:
            if key in self.cache:
                self.access_times[key] = time.time()
                return self.cache[key]
            return None
    
    def put(self, key, frame):
        with self.lock:
            # Estimate frame size
            frame_size = frame.nbytes if hasattr(frame, 'nbytes') else len(frame.tobytes())
            
            # Clean cache if needed
            while self.memory_usage + frame_size > self.max_memory and self.cache:
                self._evict_lru()
            
            # Store frame
            self.cache[key] = frame.copy()
            self.access_times[key] = time.time()
            self.memory_usage += frame_size
    
    def _evict_lru(self):
        if not self.access_times:
            return
        
        # Find least recently used
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        
        # Remove from cache
        if lru_key in self.cache:
            frame = self.cache[lru_key]
            frame_size = frame.nbytes if hasattr(frame, 'nbytes') else len(frame.tobytes())
            self.memory_usage -= frame_size
            del self.cache[lru_key]
            del self.access_times[lru_key]

class SystemMonitor:
    """Enhanced system performance monitoring with real PC data"""
    def __init__(self):
        self.cpu_history = deque(maxlen=60)  # Last 60 readings
        self.memory_history = deque(maxlen=60)
        self.disk_history = deque(maxlen=60)
        self.network_history = deque(maxlen=60)
        self.camera_stats = defaultdict(lambda: {
            'fps': 0, 'errors': 0, 'last_update': None, 'quality': 'unknown'
        })
        self.start_time = time.time()
        self.last_network_bytes = self._get_network_bytes()
        self.last_network_time = time.time()
        
    def _get_network_bytes(self):
        """Get total network bytes sent/received"""
        try:
            net_io = psutil.net_io_counters()
            return net_io.bytes_sent + net_io.bytes_recv
        except:
            return 0
        
    def update_system_stats(self):
        """Update system performance metrics with real PC data"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_history.append(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.memory_history.append(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.disk_history.append(disk_percent)
            
            # Network usage (MB/s)
            current_time = time.time()
            current_bytes = self._get_network_bytes()
            time_diff = current_time - self.last_network_time
            
            if time_diff > 0:
                bytes_diff = current_bytes - self.last_network_bytes
                network_mbps = (bytes_diff / time_diff) / (1024 * 1024)  # Convert to MB/s
                self.network_history.append(network_mbps)
            else:
                self.network_history.append(0)
                
            self.last_network_bytes = current_bytes
            self.last_network_time = current_time
            
        except Exception as e:
            logger.error(f"Error updating system stats: {e}")
            # Fallback values
            self.cpu_history.append(0)
            self.memory_history.append(0)
            self.disk_history.append(0)
            self.network_history.append(0)
        
    def update_camera_stats(self, cam_id, fps=None, error=False, quality=None):
        """Update camera-specific statistics"""
        stats = self.camera_stats[cam_id]
        if fps is not None:
            stats['fps'] = fps
        if error:
            stats['errors'] += 1
        if quality:
            stats['quality'] = quality
        stats['last_update'] = time.time()
        
    def get_system_info(self):
        """Get comprehensive system information with real PC data"""
        uptime = time.time() - self.start_time
        
        try:
            # Get real system information
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get temperature if available (Linux systems)
            temperature = None
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Try to get CPU temperature
                    for name, entries in temps.items():
                        if 'cpu' in name.lower() or 'core' in name.lower():
                            if entries:
                                temperature = entries[0].current
                                break
                    # If no CPU temp found, use first available
                    if temperature is None:
                        for name, entries in temps.items():
                            if entries:
                                temperature = entries[0].current
                                break
            except:
                temperature = None
            
            return {
                'uptime': uptime,
                'cpu_avg': sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0,
                'memory_avg': sum(self.memory_history) / len(self.memory_history) if self.memory_history else 0,
                'disk_avg': sum(self.disk_history) / len(self.disk_history) if self.disk_history else 0,
                'network_avg': sum(self.network_history) / len(self.network_history) if self.network_history else 0,
                'cpu_current': self.cpu_history[-1] if self.cpu_history else 0,
                'memory_current': self.memory_history[-1] if self.memory_history else 0,
                'disk_current': self.disk_history[-1] if self.disk_history else 0,
                'network_current': self.network_history[-1] if self.network_history else 0,
                'cpu_count': cpu_count,
                'memory_total': memory.total,
                'memory_available': memory.available,
                'disk_total': disk.total,
                'disk_free': disk.free,
                'temperature': temperature,
                'active_cameras': len([s for s in self.camera_stats.values() 
                                     if s['last_update'] and time.time() - s['last_update'] < 10]),
                'performance_history': {
                    'cpu': list(self.cpu_history),
                    'memory': list(self.memory_history),
                    'disk': list(self.disk_history),
                    'network': list(self.network_history)
                }
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {
                'uptime': uptime,
                'cpu_avg': 0, 'memory_avg': 0, 'disk_avg': 0, 'network_avg': 0,
                'cpu_current': 0, 'memory_current': 0, 'disk_current': 0, 'network_current': 0,
                'cpu_count': 1, 'memory_total': 0, 'memory_available': 0,
                'disk_total': 0, 'disk_free': 0, 'temperature': None,
                'active_cameras': 0,
                'performance_history': {'cpu': [], 'memory': [], 'disk': [], 'network': []}
            }

class CameraHealthMonitor:
    """Monitor camera health and connectivity"""
    def __init__(self):
        self.health_stats = defaultdict(lambda: {
            'status': 'unknown',
            'last_success': None,
            'consecutive_errors': 0,
            'total_errors': 0,
            'avg_response_time': 0,
            'response_times': deque(maxlen=10)
        })
        
    def record_success(self, cam_id, response_time):
        """Record successful camera access"""
        stats = self.health_stats[cam_id]
        stats['status'] = 'online'
        stats['last_success'] = time.time()
        stats['consecutive_errors'] = 0
        stats['response_times'].append(response_time)
        stats['avg_response_time'] = sum(stats['response_times']) / len(stats['response_times'])
        
    def record_error(self, cam_id, error_type='connection'):
        """Record camera error - FIXED to prevent false offline detection"""
        stats = self.health_stats[cam_id]
        stats['consecutive_errors'] += 1
        stats['total_errors'] += 1
        
        # FIXED: Much more lenient thresholds
        # Only mark offline after 15 consecutive errors (not 3!)
        # This prevents false offline detection from temporary network issues
        if stats['consecutive_errors'] >= 15:
            stats['status'] = 'offline'
        elif stats['consecutive_errors'] >= 5:
            stats['status'] = 'unstable'
        else:
            # Keep as online if we had recent success
            if stats['last_success'] and (time.time() - stats['last_success']) < 30:
                stats['status'] = 'online'  # Still consider online if successful within 30 seconds
            
    def get_camera_health(self, cam_id):
        """Get health status for specific camera"""
        return self.health_stats[cam_id]
    
    def get_all_health(self):
        """Get health status for all cameras"""
        return dict(self.health_stats)

class ConfigBackupManager:
    """Automatic configuration backup and restore"""
    def __init__(self):
        self.backup_interval = 3600  # 1 hour
        self.max_backups = 24  # Keep 24 backups (1 day)
        
    def create_backup(self, config):
        """Create timestamped backup of configuration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"config_backup_{timestamp}.json")
        
        try:
            with open(backup_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Clean old backups
            self._cleanup_old_backups()
            logger.info(f"Configuration backup created: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def _cleanup_old_backups(self):
        """Remove old backup files"""
        try:
            backup_files = [f for f in os.listdir(BACKUP_DIR) if f.startswith('config_backup_')]
            backup_files.sort(reverse=True)  # Newest first
            
            for old_backup in backup_files[self.max_backups:]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
                logger.info(f"Removed old backup: {old_backup}")
        except Exception as e:
            logger.error(f"Failed to cleanup backups: {e}")
    
    def list_backups(self):
        """List available backups"""
        try:
            backup_files = [f for f in os.listdir(BACKUP_DIR) if f.startswith('config_backup_')]
            backups = []
            for backup_file in sorted(backup_files, reverse=True):
                file_path = os.path.join(BACKUP_DIR, backup_file)
                stat = os.stat(file_path)
                backups.append({
                    'filename': backup_file,
                    'timestamp': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'size': stat.st_size
                })
            return backups
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []

class RecordingManager:
    """Handle camera recording and playback"""
    def __init__(self):
        self.recording_sessions = {}
        self.recording_lock = Lock()
        
    def start_recording(self, camera_id, camera_name, duration_minutes=None):
        """Start recording for a specific camera"""
        with self.recording_lock:
            if camera_id in self.recording_sessions:
                return False, "Camera already recording"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"camera_{camera_id}_{camera_name}_{timestamp}.avi"
            filepath = os.path.join(RECORDINGS_DIR, filename)
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            writer = cv2.VideoWriter(filepath, fourcc, 10.0, (640, 480))
            
            session = {
                'writer': writer,
                'filepath': filepath,
                'start_time': time.time(),
                'duration': duration_minutes * 60 if duration_minutes else None,
                'frame_count': 0
            }
            
            self.recording_sessions[camera_id] = session
            logger.info(f"Started recording camera {camera_id} to {filepath}")
            return True, filepath
    
    def stop_recording(self, camera_id):
        """Stop recording for a specific camera"""
        with self.recording_lock:
            if camera_id not in self.recording_sessions:
                return False, "Camera not recording"
            
            session = self.recording_sessions[camera_id]
            session['writer'].release()
            
            duration = time.time() - session['start_time']
            logger.info(f"Stopped recording camera {camera_id}. Duration: {duration:.1f}s, Frames: {session['frame_count']}")
            
            filepath = session['filepath']
            del self.recording_sessions[camera_id]
            return True, filepath
    
    def record_frame(self, camera_id, frame):
        """Add frame to recording if active"""
        with self.recording_lock:
            if camera_id not in self.recording_sessions:
                return
            
            session = self.recording_sessions[camera_id]
            
            # Check duration limit
            if session['duration'] and (time.time() - session['start_time']) > session['duration']:
                self.stop_recording(camera_id)
                return
            
            # Resize frame for recording
            frame_resized = cv2.resize(frame, (640, 480))
            session['writer'].write(frame_resized)
            session['frame_count'] += 1
    
    def get_recording_status(self):
        """Get status of all active recordings"""
        with self.recording_lock:
            status = {}
            for cam_id, session in self.recording_sessions.items():
                duration = time.time() - session['start_time']
                status[cam_id] = {
                    'duration': duration,
                    'frame_count': session['frame_count'],
                    'filepath': session['filepath']
                }
            return status
DEFAULT_CONFIG = {
    "cameras": [
        {"url": "http://187.140.117.185/web/tmpfs/snap.jpg", "username": "admin", "password": "admin", "name": "Camera 1", "enabled": True, "type": "image", "company": "Generic IP Cams"},
        {"url": "http://162.204.123.101/web/tmpfs/snap.jpg", "username": "admin", "password": "admin", "name": "Camera 2", "enabled": True, "type": "image"},
        {"url": "http://190.20.231.202/web/tmpfs/snap.jpg", "username": "admin", "password": "admin", "name": "Camera 3", "enabled": True, "type": "image"},
        {"url": "http://133.232.94.137/web/tmpfs/snap.jpg", "username": "admin", "password": "admin", "name": "Camera 4", "enabled": True, "type": "image"},
        {"url": "http://187.37.20.35/tmpfs/snap.jpg", "username": "guest", "password": "guest", "name": "Camera 5", "enabled": True, "type": "image"},
        {"url": "http://121.116.26.50/tmpfs/snap.jpg", "username": "admin", "password": "admin", "name": "Camera 6", "enabled": True, "type": "image"},
        {"url": "http://83.87.104.50:1029/web/tmpfs/snap.jpg", "username": "admin", "password": "admin", "name": "Camera 7", "enabled": True, "type": "image"},
        {"url": "http://185.73.190.212/web/tmpfs/snap.jpg", "username": "user", "password": "user", "name": "Camera 8", "enabled": True, "type": "image"},
        {"url": "http://75.82.132.7/web/tmpfs/snap.jpg", "username": "user", "password": "user", "name": "Camera 9", "enabled": True, "type": "image"},
        {"url": "http://85.165.118.60/web/tmpfs/snap.jpg", "username": "admin", "password": "admin", "name": "Camera 10", "enabled": True, "type": "image"},
        {"url": "http://66.74.41.152/tmpfs/snap.jpg", "username": "admin", "password": "admin", "name": "Camera 11", "enabled": True, "type": "image"},
        {"url": "http://222.10.11.86/tmpfs/snap.jpg", "username": "user", "password": "user", "name": "Camera 12", "enabled": True, "type": "image"},
        {"url": "http://213.144.145.239:8090/cam_1.cgi", "username": "", "password": "", "name": "Camera 13 (Video)", "enabled": True, "type": "video"},
        {"url": "http://195.223.180.50/cam_1.cgi", "username": "", "password": "", "name": "Camera 14 (Video)", "enabled": True, "type": "video"},
        {"url": "http://119.224.56.57:8081/out.jpg", "username": "", "password": "", "name": "Camera 15 (No Auth)", "enabled": True, "type": "image"},
        {"url": "http://116.82.9.82:5001/out.jpg", "username": "", "password": "", "name": "Camera 16 (No Auth)", "enabled": True, "type": "image"},
        {"url": "http://61.78.164.58:8089/cam_1.cgi", "username": "", "password": "", "name": "Camera 17 (Video)", "enabled": True, "type": "video"},
        {"url": "http://72.199.200.5:8080/cam_1.cgi", "username": "", "password": "", "name": "Camera 18 (Video)", "enabled": True, "type": "video"},
        {"url": "http://95.255.183.164:8080/cam_2.cgi", "username": "", "password": "", "name": "Camera 19 (Video)", "enabled": True, "type": "video"},
        {"url": "http://75.149.26.30:1024/cam_1.cgi", "username": "", "password": "", "name": "Camera 20 (Video)", "enabled": True, "type": "video"},
        {"url": "http://72.199.200.5:8080/cam_2.cgi", "username": "", "password": "", "name": "Camera 21 (Video)", "enabled": True, "type": "video"},
        {"url": "http://74.105.120.201:444/cam_1.cgi", "username": "", "password": "", "name": "Camera 22 (Video)", "enabled": True, "type": "video"},
        {"url": "http://191.113.29.26:8082/cam_1.jpg", "username": "", "password": "", "name": "Camera 23 (No Auth)", "enabled": True, "type": "image"},
        {"url": "http://188.6.81.94:8080/cam_1.jpg", "username": "", "password": "", "name": "Camera 24 (No Auth)", "enabled": True, "type": "image"},
        {"url": "http://188.6.81.94:8080/cam_3.jpg", "username": "", "password": "", "name": "Camera 25 (No Auth)", "enabled": True, "type": "image"},
        {"url": "http://37.123.131.43:97/image.jpg", "username": "", "password": "", "name": "Camera 26 (No Auth)", "enabled": True, "type": "image"},
        {"url": "http://96.3.20.210:81/image.jpg", "username": "", "password": "", "name": "Camera 27 (No Auth)", "enabled": True, "type": "image"},
        {"url": "http://2.85.145.112:8080/cam_1.cgi", "username": "", "password": "", "name": "Camera 28 (Video)", "enabled": True, "type": "video"},
        {"url": "http://69.140.27.58:10001/cam_1.cgi", "username": "", "password": "", "name": "Camera 29 (Video)", "enabled": True, "type": "video"},
        {"url": "http://151.75.126.105/image.jpg", "username": "", "password": "", "name": "Camera 30 (No Auth)", "enabled": True, "type": "image"},
        {"url": "http://82.65.168.85:8005/image.jpg", "username": "", "password": "", "name": "Camera 31 (No Auth)", "enabled": True, "type": "image"},
        {"url": "http://82.65.168.85:8001/image.jpg", "username": "", "password": "", "name": "Camera 32 (No Auth)", "enabled": True, "type": "image"},
        {"url": "http://96.236.138.17:8888/cam_1.cgi", "username": "", "password": "", "name": "Camera 33 (Video)", "enabled": True, "type": "video"},
        {"url": "http://80.61.63.103:81/cam_1.cgi", "username": "", "password": "", "name": "Camera 34 (Video)", "enabled": True, "type": "video"},
        {"url": "http://82.64.212.123:4444/out.jpg", "username": "", "password": "", "name": "Camera 35 (No Auth)", "enabled": True, "type": "image"},
        {"url": "http://79.136.47.231:8083/video.cgi", "username": "", "password": "", "name": "Camera 36 (Video)", "enabled": True, "type": "video"},
        {"url": "http://91.158.41.198/video.cgi", "username": "", "password": "", "name": "Camera 37 (Video)", "enabled": True, "type": "video"},
        {"url": "http://62.20.188.15:89/video.cgi", "username": "", "password": "", "name": "Camera 38 (Video)", "enabled": True, "type": "video"},
        {"url": "http://62.92.246.134:1024/video.cgi", "username": "", "password": "", "name": "Camera 39 (Video)", "enabled": True, "type": "video"},
        {"url": "http://71.115.155.24:93/cam_1.cgi", "username": "", "password": "", "name": "Camera 40 (Video)", "enabled": True, "type": "video"}
    ],
    "settings": {
        "cam_width": 384,
        "cam_height": 288,
        "fullscreen_width": 1200,
        "fullscreen_height": 900,
        "timeout": 5.0,  # Increased from 1.5 to 5.0 - prevents false offline detection
        "refresh_delay": 0.5,
        "web_port": 5000,
        "web_host": "0.0.0.0",
        "max_grid_width": 1920,
        "max_grid_height": 1080,
        "cameras_per_page": 12,
        "high_quality": False,
        "jpeg_quality": 85
    }
}

class ConfigManager:
    @staticmethod
    def load_config():
        """Load configuration from file or create default"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return DEFAULT_CONFIG
        else:
            ConfigManager.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
    
    @staticmethod
    def save_config(config):
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    @staticmethod
    def get_enabled_cameras(config):
        """Get list of enabled cameras with company and nsfw information"""
        cameras = []
        for cam in config['cameras']:
            if cam['enabled']:
                cameras.append((
                    cam['url'], 
                    cam['username'], 
                    cam['password'], 
                    cam['name'], 
                    cam.get('type', 'image'),
                    cam.get('company', 'Unknown'),
                    cam.get('nsfw', False)
                ))
        return cameras

class InteractiveCameraViewer:
    def __init__(self, config=None):
        self.config = config or ConfigManager.load_config()
        self.cams = ConfigManager.get_enabled_cameras(self.config)
        self.settings = self.config['settings']
        
        # Advanced components
        self.frame_cache = FrameCache(max_memory_mb=256)  # Reduced from 512MB
        self.system_monitor = SystemMonitor()
        self.health_monitor = CameraHealthMonitor()
        self.backup_manager = ConfigBackupManager()
        self.recording_manager = RecordingManager()
        
        # Thread pool for camera management - OPTIMIZED for 277 cameras
        # Use enough workers to handle all cameras without queuing
        max_workers = len(self.cams)  # One thread per camera for best performance
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.camera_tasks = {}
        
        # Session management - OPTIMIZED
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        # Reduce connection pool size to save memory
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=1)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.frames = {}
        self.original_frames = {}
        self.running = True
        self.selected_camera = None
        self.mouse_callback_set = False
        self.paused_cameras = set()
        self.active_camera = None
        
        # Paging system
        self.current_page = 0
        self.cameras_per_page = self.settings.get('cameras_per_page', 12)
        self.total_pages = max(1, (len(self.cams) + self.cameras_per_page - 1) // self.cameras_per_page)
        self.show_all_cameras = False
        
        # Zoom functionality
        self.zoom_level = 1.0
        self.zoom_center_x = 0.5
        self.zoom_center_y = 0.5
        self.max_zoom = 5.0
        self.min_zoom = 1.0
        
        # Video capture objects
        self.video_captures = {}
        self.video_frame_counts = {}
        
        # Performance monitoring - OPTIMIZED
        self.last_backup = time.time()
        self.performance_thread = threading.Thread(target=self._performance_monitor, daemon=True)
        self.performance_thread.start()
        
        # Web interface optimization
        self.web_active_streams = set()  # Track active web streams
        self.web_stream_limit = 10  # Limit concurrent web streams
        
        logger.info(f"Initialized surveillance system with {len(self.cams)} cameras (max {max_workers} workers)")
    
    def _performance_monitor(self):
        """Background thread for performance monitoring - OPTIMIZED"""
        while self.running:
            try:
                self.system_monitor.update_system_stats()
                
                # Auto backup every 2 hours (was 1 hour)
                if time.time() - self.last_backup > 7200:
                    self.backup_manager.create_backup(self.config)
                    self.last_backup = time.time()
                
                # Memory cleanup less frequently
                if len(self.frame_cache.cache) > 200:
                    gc.collect()
                
                # Longer sleep to reduce CPU usage
                time.sleep(60)  # Update every 60 seconds (was 30)
            except Exception as e:
                logger.error(f"Performance monitor error: {e}")
                time.sleep(120)  # Longer sleep on error
    
    def pause_background_cameras(self, active_camera_id):
        """Pause all cameras except the active one for performance optimization"""
        for i in range(len(self.cams)):
            if i != active_camera_id:
                self.paused_cameras.add(i)
        self.active_camera = active_camera_id  # Set active camera for fast updates
    
    def resume_all_cameras(self):
        """Resume all paused cameras when returning to grid view"""
        if self.paused_cameras:
            self.paused_cameras.clear()
        self.active_camera = None  # Clear active camera
        
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks and scroll for zoom"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.selected_camera is None:  # Currently in grid view
                # Calculate which camera was clicked
                camera_id = self.get_clicked_camera(x, y)
                if camera_id is not None:
                    self.selected_camera = camera_id
                    self.zoom_level = 1.0  # Reset zoom when selecting camera
                    # Pause background cameras for optimization
                    self.pause_background_cameras(camera_id)
                    print(f"Selected Camera {camera_id + 1} for fullscreen view")
            else:  # Currently in single camera view
                # Check if back button was clicked (top-left corner)
                if x < 100 and y < 50:
                    self.selected_camera = None
                    self.zoom_level = 1.0  # Reset zoom
                    # Resume all cameras when returning to grid
                    self.resume_all_cameras()
                    print("Returning to grid view")
                else:
                    # Update zoom center for panning
                    self.zoom_center_x = x / self.settings['fullscreen_width']
                    self.zoom_center_y = y / self.settings['fullscreen_height']
        
        elif event == cv2.EVENT_MOUSEWHEEL and self.selected_camera is not None:
            # Zoom in/out with mouse wheel in fullscreen mode
            zoom_delta = 0.1 if flags > 0 else -0.1
            old_zoom = self.zoom_level
            self.zoom_level = max(self.min_zoom, min(self.max_zoom, self.zoom_level + zoom_delta))
            
            if self.zoom_level != old_zoom:
                print(f"Zoom: {self.zoom_level:.1f}x")
    
    def get_clicked_camera(self, x, y):
        """Determine which camera was clicked based on coordinates"""
        if self.show_all_cameras:
            return self.get_clicked_camera_all_view(x, y)
        else:
            return self.get_clicked_camera_paged_view(x, y)
    
    def get_clicked_camera_all_view(self, x, y):
        """Handle clicks in all cameras view with dynamic tile sizing"""
        # Calculate tile size (same logic as in get_all_cameras_frame)
        max_width = 1800
        max_height = 900
        
        num_cameras = len(self.cams)
        
        # Calculate grid layout - MUST MATCH get_all_cameras_frame EXACTLY
        if num_cameras <= 12:
            cols, rows = 4, 3
        elif num_cameras <= 20:
            cols, rows = 5, 4
        elif num_cameras <= 30:
            cols, rows = 6, 5
        elif num_cameras <= 42:
            cols, rows = 7, 6
        elif num_cameras <= 56:
            cols, rows = 8, 7
        elif num_cameras <= 72:
            cols, rows = 9, 8
        elif num_cameras <= 90:
            cols, rows = 10, 9
        elif num_cameras <= 110:
            cols, rows = 11, 10
        elif num_cameras <= 132:
            cols, rows = 12, 11
        elif num_cameras <= 156:
            cols, rows = 13, 12
        elif num_cameras <= 182:
            cols, rows = 14, 13
        elif num_cameras <= 210:
            cols, rows = 15, 14
        elif num_cameras <= 240:
            cols, rows = 16, 15
        elif num_cameras <= 272:
            cols, rows = 17, 16
        else:
            # For 277+ cameras: 18x16 grid (288 capacity)
            cols, rows = 18, 16
        
        tile_width = min(100, max_width // cols)
        tile_height = min(56, max_height // rows)
        
        # Calculate which camera was clicked
        col = x // tile_width
        row = (y - 70) // tile_height  # Account for title offset
        
        if row < 0:  # Clicked on title area
            return None
            
        camera_id = row * cols + col
        
        # Make sure it's a valid camera
        if camera_id < len(self.cams):
            return camera_id
        return None
    
    def get_clicked_camera_paged_view(self, x, y):
        """Handle clicks in paged view"""
        current_cameras = self.get_current_page_cameras()
        num_cameras = len(current_cameras)
        
        if num_cameras == 0:
            return None
        
        # Determine grid layout for current page
        cols, rows = self.calculate_grid_layout(num_cameras)
        
        # Calculate camera dimensions in the combined frame
        grid_width = cols * self.settings['cam_width']
        grid_height = rows * self.settings['cam_height']
        
        # Account for page info offset (page info is at y=30, so offset should be 30)
        adjusted_y = y - 30  # Account for page info at top
        
        # Check if click is within the grid
        if x >= grid_width or adjusted_y < 0 or adjusted_y >= grid_height:
            return None
        
        # Calculate which camera was clicked
        col = x // self.settings['cam_width']
        row = adjusted_y // self.settings['cam_height']
        page_camera_id = row * cols + col
        
        # Convert to global camera ID
        if page_camera_id < len(current_cameras):
            return current_cameras[page_camera_id][0]  # Return global camera index
        return None
    
    def get_current_page_cameras(self):
        """Get cameras for current page with their global indices"""
        start_idx = self.current_page * self.cameras_per_page
        end_idx = min(start_idx + self.cameras_per_page, len(self.cams))
        
        current_cameras = []
        for i in range(start_idx, end_idx):
            current_cameras.append((i, self.cams[i]))  # (global_index, camera_data)
        
        return current_cameras
    
    def calculate_grid_layout(self, num_cameras):
        """Calculate optimal grid layout for given number of cameras"""
        if num_cameras <= 4:
            return 2, 2
        elif num_cameras <= 6:
            return 3, 2
        elif num_cameras <= 9:
            return 3, 3
        elif num_cameras <= 12:
            return 4, 3
        elif num_cameras <= 16:
            return 4, 4
        else:
            return 4, 4  # Keep 4x4 for pages

    def fetch_camera_advanced(self, cam_id, url, user, password, name, cam_type="image"):
        """Advanced camera fetching with health monitoring and caching - OPTIMIZED for 277 cameras"""
        consecutive_errors = 0
        last_frame_time = time.time()
        retry_count = 0
        max_retries = 2  # Quick retries for faster loading
        
        # Use shorter timeouts for faster loading with many cameras
        is_initial_load = cam_id not in self.frames
        timeout = 8.0 if is_initial_load else 5.0  # Reduced from 15s/10s
        
        while self.running:
            start_time = time.time()
            
            try:
                # Skip if paused
                if cam_id in self.paused_cameras:
                    time.sleep(1.0)
                    continue
                
                # Check cache first (but only for very recent frames)
                cache_key = f"{cam_id}_{int(time.time() // 1)}"  # 1-second cache
                cached_frame = self.frame_cache.get(cache_key)
                
                if cached_frame is not None and cam_id != self.active_camera:
                    # Use cached frame for non-active cameras
                    self.frames[cam_id] = cached_frame
                    time.sleep(0.2)  # Faster updates
                    continue
                
                # Fetch new frame with retry logic
                result = None
                for attempt in range(max_retries):
                    try:
                        if cam_type == "video":
                            result = self.fetch_video_frame_advanced(cam_id, url, name, timeout)
                        else:
                            result = self.fetch_image_frame_advanced(url, user, password, name, timeout)
                        
                        if result is not None:
                            break  # Success, exit retry loop
                    except Exception as retry_error:
                        if attempt < max_retries - 1:
                            time.sleep(0.2)  # Very short delay between retries
                            continue
                        else:
                            raise retry_error  # Re-raise on final attempt
                
                if result is not None and isinstance(result, tuple) and len(result) == 2:
                    frame, original_frame = result
                    if frame is not None:
                        # Add overlays
                        frame = self.add_camera_overlays(frame, name, cam_type, cam_id)
                        
                        # Store frames
                        self.frames[cam_id] = frame
                        if original_frame is not None:
                            self.original_frames[cam_id] = original_frame
                        
                        # Cache frame
                        self.frame_cache.put(cache_key, frame)
                        
                        # Record for recording if active
                        recording_frame = original_frame if original_frame is not None else frame
                        self.recording_manager.record_frame(cam_id, recording_frame)
                        
                        # Update health and performance stats
                        response_time = time.time() - start_time
                        self.health_monitor.record_success(cam_id, response_time)
                        
                        # Calculate FPS
                        current_time = time.time()
                        fps = 1.0 / (current_time - last_frame_time) if last_frame_time else 0
                        last_frame_time = current_time
                        self.system_monitor.update_camera_stats(cam_id, fps=fps)
                        
                        consecutive_errors = 0
                        retry_count = 0
                        
                        # Log only first successful load to reduce spam
                        if is_initial_load:
                            logger.info(f"✓ Camera {cam_id + 1} loaded ({response_time:.1f}s)")
                            is_initial_load = False
                    else:
                        consecutive_errors += 1
                        self.health_monitor.record_error(cam_id)
                else:
                    consecutive_errors += 1
                    self.health_monitor.record_error(cam_id)
                    
            except Exception as e:
                consecutive_errors += 1
                retry_count += 1
                self.health_monitor.record_error(cam_id, str(e))
                
                # Only log errors occasionally to reduce spam
                if consecutive_errors == 1:  # Log only first error
                    error_msg = str(e)[:40] + "..." if len(str(e)) > 40 else str(e)
                    logger.warning(f"⚠️  Camera {cam_id + 1} error: {error_msg}")
                
                # Create error frame after fewer failures for faster feedback
                if consecutive_errors >= 5:  # Reduced from 8
                    error_frame = self.create_error_frame(name, str(e))
                    self.frames[cam_id] = error_frame
            
            # OPTIMIZED: Faster delay logic for 277 cameras
            if consecutive_errors > 0:
                # Very fast backoff: 0.3s, 0.5s, 1s, 2s max
                if consecutive_errors <= 1:
                    delay = 0.3
                elif consecutive_errors <= 3:
                    delay = 0.5
                elif consecutive_errors <= 6:
                    delay = 1.0
                else:
                    delay = 2.0  # Max 2 seconds
            else:
                delay = self.calculate_optimal_delay(cam_type, cam_id, consecutive_errors)
            
            time.sleep(delay)
    
    def add_camera_overlays(self, frame, name, cam_type, cam_id):
        """Add clean overlays to camera frame - SIMPLIFIED"""
        # Check if camera has NSFW content and apply blur in grid view
        camera_config = self.config['cameras'][cam_id] if cam_id < len(self.config['cameras']) else {}
        is_nsfw = camera_config.get('nsfw', False)
        
        # Apply NSFW protection (blur) only in grid view, not in fullscreen
        if is_nsfw and self.selected_camera != cam_id:
            # Apply strong blur to hide NSFW content
            frame = cv2.GaussianBlur(frame, (51, 51), 0)
            
            # Add NSFW overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            
            # Add warning text
            cv2.putText(frame, "PRIVATE", (frame.shape[1]//2-40, frame.shape[0]//2-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.putText(frame, "CLICK TO VIEW", (frame.shape[1]//2-60, frame.shape[0]//2+20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Extract camera number and city from name
        camera_number = cam_id + 1
        
        # Extract city from name (format: "Camera X - City" or "Camera X (Type) - City")
        city = ""
        if " - " in name:
            city = name.split(" - ")[-1]  # Get everything after last " - "
        
        # Get company if available
        company = camera_config.get('company', '')
        
        # Build display text - only show what's available
        display_lines = []
        
        # Camera number (always show)
        display_lines.append(f"Camera {camera_number}")
        
        # Company (only if available and not 'Unknown')
        if company and company != 'Unknown':
            display_lines.append(company)
        
        # City (only if available)
        if city:
            display_lines.append(city)
        
        # Calculate text area size
        max_width = 0
        line_height = 20
        for line in display_lines:
            text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            max_width = max(max_width, text_size[0])
        
        # Create background for text
        bg_height = len(display_lines) * line_height + 10
        overlay = frame.copy()
        cv2.rectangle(overlay, (5, 5), (max_width + 20, bg_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Draw text lines
        y_pos = 20
        for line in display_lines:
            cv2.putText(frame, line, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_pos += line_height
        
        # Status indicator (small dot in top-right)
        health = self.health_monitor.get_camera_health(cam_id)
        status_color = (0, 255, 0) if health['status'] == 'online' else (0, 165, 255) if health['status'] == 'unstable' else (0, 0, 255)
        cv2.circle(frame, (frame.shape[1] - 15, 15), 6, status_color, -1)
        
        # Recording indicator (small red dot below status if recording)
        if cam_id in self.recording_manager.recording_sessions:
            cv2.circle(frame, (frame.shape[1] - 15, 30), 4, (0, 0, 255), -1)
        
        return frame
    
    def create_error_frame(self, name, error_msg):
        """Create clean error frame"""
        error_frame = np.zeros((self.settings['cam_height'], self.settings['cam_width'], 3), dtype=np.uint8)
        
        # Error background
        cv2.rectangle(error_frame, (0, 0), (self.settings['cam_width'], self.settings['cam_height']), (20, 20, 20), -1)
        
        # Error icon (X)
        center_x, center_y = self.settings['cam_width'] // 2, self.settings['cam_height'] // 2
        cv2.line(error_frame, (center_x - 20, center_y - 20), (center_x + 20, center_y + 20), (0, 0, 255), 3)
        cv2.line(error_frame, (center_x - 20, center_y + 20), (center_x + 20, center_y - 20), (0, 0, 255), 3)
        
        # Extract camera number from name
        camera_number = "Camera"
        if "Camera" in name and " - " in name:
            try:
                camera_number = name.split(" - ")[0]  # "Camera X"
            except:
                camera_number = name[:15]  # Fallback
        
        # Error text - simplified
        cv2.putText(error_frame, "OFFLINE", (10, center_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(error_frame, camera_number, (10, center_y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
        
        return error_frame
    
    def calculate_optimal_delay(self, cam_type, cam_id, consecutive_errors):
        """Calculate optimal delay based on camera type, status, and errors - OPTIMIZED"""
        base_delay = {
            'video': 0.03 if cam_id == self.active_camera else 0.05,  # Faster video refresh
            'image': 0.15 if cam_id == self.active_camera else self.settings.get('refresh_delay', 0.3)  # Faster image refresh
        }
        
        delay = base_delay.get(cam_type, 0.3)
        
        # Minimal increase for errors
        if consecutive_errors > 0:
            delay *= (1 + consecutive_errors * 0.3)
        
        # Reduce delay for high-priority cameras
        if cam_id == self.active_camera:
            delay *= 0.4
        
        return min(delay, 3.0)  # Max 3 second delay (reduced from 5)
    
    def fetch_image_frame_advanced(self, url, user, password, name, timeout=None):
        """Advanced image fetching with better error handling and configurable timeout"""
        if timeout is None:
            timeout = self.settings['timeout']
            
        try:
            auth = (user, password) if user and password else None
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/jpeg,image/png,image/*,*/*;q=0.8",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache"
            }
            
            r = self.session.get(url, auth=auth, timeout=timeout, 
                               stream=True, headers=headers)
            
            if r.status_code == 200:
                content = b''
                for chunk in r.iter_content(chunk_size=8192):
                    content += chunk
                    if len(content) > 8000000:  # 8MB limit
                        break
                
                if len(content) > 1000:
                    img = Image.open(BytesIO(content))
                    if img.mode != 'RGB':
                        img = img.convert("RGB")
                    
                    original_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    grid_frame = cv2.resize(original_frame, 
                                          (self.settings['cam_width'], self.settings['cam_height']), 
                                          interpolation=cv2.INTER_LINEAR)
                    
                    return grid_frame, original_frame
                else:
                    # Only log content size warnings occasionally
                    if hasattr(self, '_content_warnings'):
                        self._content_warnings[name] = self._content_warnings.get(name, 0) + 1
                        if self._content_warnings[name] <= 3 or self._content_warnings[name] % 20 == 0:
                            logger.debug(f"⚠️  {name} content too small: {len(content)} bytes")
                    else:
                        self._content_warnings = {name: 1}
                        logger.debug(f"⚠️  {name} content too small: {len(content)} bytes")
                    return None, None
            else:
                # Only log HTTP errors occasionally
                if hasattr(self, '_http_warnings'):
                    self._http_warnings[name] = self._http_warnings.get(name, 0) + 1
                    if self._http_warnings[name] <= 3 or self._http_warnings[name] % 20 == 0:
                        logger.debug(f"⚠️  {name} HTTP {r.status_code}")
                else:
                    self._http_warnings = {name: 1}
                    logger.debug(f"⚠️  {name} HTTP {r.status_code}")
                return None, None
                
        except Exception as e:
            raise e
    
    def fetch_video_frame_advanced(self, cam_id, url, name, timeout=None):
        """Advanced video fetching with better connection management and configurable timeout"""
        if timeout is None:
            timeout = self.settings['timeout']
            
        try:
            if cam_id not in self.video_captures:
                logger.info(f"Initializing video stream for {name}...")
                cap = cv2.VideoCapture(url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FPS, 25)
                # Set timeout in milliseconds
                try:
                    cap.set(cv2.CAP_PROP_TIMEOUT, int(timeout * 1000))
                except:
                    pass  # Ignore if timeout property not available
                
                # Test connection with timeout
                ret, test_frame = cap.read()
                if not ret or (test_frame is None):
                    logger.warning(f"⚠️  Cannot initialize video stream for {name} - stream may be offline")
                    cap.release()
                    # Return None to trigger error frame creation
                    raise Exception("Video stream initialization failed - camera offline")
                
                self.video_captures[cam_id] = cap
                self.video_frame_counts[cam_id] = 0
                
                # Return test frame
                grid_frame = cv2.resize(test_frame, 
                                      (self.settings['cam_width'], self.settings['cam_height']), 
                                      interpolation=cv2.INTER_LINEAR)
                return grid_frame, test_frame
            
            cap = self.video_captures[cam_id]
            ret, original_frame = cap.read()
            
            if ret and (original_frame is not None):
                self.video_frame_counts[cam_id] += 1
                grid_frame = cv2.resize(original_frame, 
                                      (self.settings['cam_width'], self.settings['cam_height']), 
                                      interpolation=cv2.INTER_LINEAR)
                return grid_frame, original_frame
            else:
                # Video stream failed - clean up and trigger error
                logger.warning(f"Video stream disconnected for {name} - camera offline")
                if cam_id in self.video_captures:
                    cap.release()
                    del self.video_captures[cam_id]
                    if cam_id in self.video_frame_counts:
                        del self.video_frame_counts[cam_id]
                # Raise exception to trigger error frame creation with "OFFLINE" status
                raise Exception("Video stream disconnected - camera offline")
                
        except Exception as e:
            # Clean up video capture
            if cam_id in self.video_captures:
                self.video_captures[cam_id].release()
                del self.video_captures[cam_id]
            if cam_id in self.video_frame_counts:
                del self.video_frame_counts[cam_id]
            # Re-raise to trigger error frame creation in main fetch function
            raise e
    
    def fetch_video_frame(self, cam_id, url, name):
        """Fetch frame from video stream with high quality"""
        try:
            # Initialize video capture if not exists
            if cam_id not in self.video_captures:
                print(f"Initializing video stream for {name}...")
                cap = cv2.VideoCapture(url)
                
                # Set properties with error checking
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FPS, 25)  # More conservative FPS
                
                # Test if the stream is accessible
                ret, test_frame = cap.read()
                if not ret or (test_frame is None):
                    print(f"✗ {name} - Cannot initialize video stream")
                    cap.release()
                    return None, None
                
                print(f"✓ {name} - Video stream initialized successfully")
                self.video_captures[cam_id] = cap
                self.video_frame_counts[cam_id] = 0
                
                # Return the test frame
                grid_frame = cv2.resize(test_frame, (self.settings['cam_width'], self.settings['cam_height']), 
                                      interpolation=cv2.INTER_LINEAR)
                return grid_frame, test_frame
            
            cap = self.video_captures[cam_id]
            
            # Read frame from video stream
            ret, original_frame = cap.read()
            if ret and (original_frame is not None):
                self.video_frame_counts[cam_id] += 1
                
                # Create grid-sized frame for display
                grid_frame = cv2.resize(original_frame, (self.settings['cam_width'], self.settings['cam_height']), 
                                      interpolation=cv2.INTER_LINEAR)
                
                return grid_frame, original_frame
            else:
                # Try to reconnect
                print(f"Reconnecting video stream for {name}...")
                if cam_id in self.video_captures:
                    cap.release()
                    del self.video_captures[cam_id]
                    if cam_id in self.video_frame_counts:
                        del self.video_frame_counts[cam_id]
                return None, None
                
        except Exception as e:
            print(f"Video stream error for {name}: {e}")
            # Clean up failed connection
            if cam_id in self.video_captures:
                self.video_captures[cam_id].release()
                del self.video_captures[cam_id]
            if cam_id in self.video_frame_counts:
                del self.video_frame_counts[cam_id]
            return None, None
    
    def fetch_image_frame(self, url, user, password, name):
        """Fetch frame from image snapshot with high quality for specific cameras"""
        try:
            auth = (user, password) if user and password else None
            # Use optimized headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/jpeg,image/png,image/*,*/*;q=0.8"
            }
            
            r = self.session.get(url, auth=auth, timeout=self.settings['timeout'], 
                               stream=True, headers=headers)
            if r.status_code == 200:
                # Read content with reasonable size limit
                content = b''
                for chunk in r.iter_content(chunk_size=8192):
                    content += chunk
                    if len(content) > 8000000:  # 8MB limit for high quality
                        break
                
                if len(content) > 1000:  # Minimum size check
                    # Process image with quality preservation
                    img = Image.open(BytesIO(content))
                    
                    # Convert to RGB if needed
                    if img.mode != 'RGB':
                        img = img.convert("RGB")
                    
                    # Convert to OpenCV format - this is the original high-res frame
                    original_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    
                    # For grid display, resize to standard size
                    frame = cv2.resize(original_frame, (self.settings['cam_width'], self.settings['cam_height']), 
                                     interpolation=cv2.INTER_LINEAR)
                    
                    return frame, original_frame
                else:
                    print(f"✗ {name} content too small: {len(content)} bytes")
                    return None, None
            else:
                print(f"✗ {name} HTTP {r.status_code}")
                return None, None
        except Exception as e:
            raise e  # Re-raise to be handled by main fetch_camera method
    
    def start_threads(self):
        """Start camera threads using thread pool with STAGGERED LOADING for 277 cameras"""
        logger.info("Starting camera threads with staggered loading...")
        
        # Start cameras in smaller batches with shorter delays
        batch_size = 25  # 25 cameras at a time
        batch_delay = 1.0  # 1 second between batches
        
        total_cameras = len(self.cams)
        batches = (total_cameras + batch_size - 1) // batch_size  # Round up
        
        logger.info(f"Loading {total_cameras} cameras in {batches} batches of {batch_size}...")
        logger.info(f"Thread pool: {self.thread_pool._max_workers} workers")
        
        for batch_num in range(batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_cameras)
            
            # Start this batch of cameras
            batch_started = 0
            for i in range(start_idx, end_idx):
                camera_data = self.cams[i]
                if len(camera_data) >= 7:
                    url, user, pwd, name, cam_type, company, nsfw = camera_data
                else:
                    # Handle legacy format without nsfw field
                    url, user, pwd, name, cam_type, company = camera_data
                    nsfw = False
                
                try:
                    future = self.thread_pool.submit(self.fetch_camera_advanced, i, url, user, pwd, name, cam_type)
                    self.camera_tasks[i] = future
                    batch_started += 1
                except Exception as e:
                    logger.error(f"Failed to start camera {i+1}: {e}")
            
            logger.info(f"✓ Batch {batch_num + 1}/{batches}: Cameras {start_idx + 1}-{end_idx} submitted ({batch_started} cameras)")
            
            # Wait between batches (except for last batch)
            if batch_num < batches - 1:
                time.sleep(batch_delay)
        
        logger.info(f"✅ All {len(self.camera_tasks)} camera threads submitted to pool")
        
        # Start a progress monitor thread
        def monitor_progress():
            """Monitor and log camera loading progress"""
            last_count = 0
            start_time = time.time()
            check_interval = 5  # Check every 5 seconds
            
            while self.running:
                time.sleep(check_interval)
                current_count = len(self.frames)
                
                if current_count >= len(self.cams):
                    logger.info(f"🎉 All {current_count} cameras loaded!")
                    break
                
                if current_count > last_count:
                    elapsed = time.time() - start_time
                    rate = current_count / elapsed if elapsed > 0 else 0
                    remaining = len(self.cams) - current_count
                    eta = remaining / rate if rate > 0 else 0
                    logger.info(f"📊 Progress: {current_count}/{len(self.cams)} cameras ({current_count*100//len(self.cams)}%) - Rate: {rate:.1f}/s - ETA: {int(eta)}s")
                    last_count = current_count
                
                # Stop monitoring after 5 minutes
                if elapsed > 300:
                    logger.info(f"⏱️  Monitoring stopped after 5 minutes. {current_count}/{len(self.cams)} cameras loaded.")
                    break
        
        progress_thread = threading.Thread(target=monitor_progress, daemon=True)
        progress_thread.start()
        
        # Give cameras time to initialize
        logger.info("⏳ Waiting for initial camera connections...")
        time.sleep(2)
        
        # Check how many cameras have loaded
        loaded_count = len(self.frames)
        logger.info(f"📹 Initial load: {loaded_count}/{len(self.cams)} cameras ready")
        logger.info("🔄 Cameras will continue loading in background...")
        
        return list(self.camera_tasks.values())
    
    def get_system_status(self):
        """Get comprehensive system status for API"""
        system_info = self.system_monitor.get_system_info()
        health_info = self.health_monitor.get_all_health()
        recording_status = self.recording_manager.get_recording_status()
        
        # Camera status summary
        camera_status = {}
        for i, camera_data in enumerate(self.cams):
            if len(camera_data) >= 7:
                url, user, pwd, name, cam_type, company, nsfw = camera_data
            else:
                # Handle legacy format without nsfw field
                url, user, pwd, name, cam_type, company = camera_data
                nsfw = False
                
            health = self.health_monitor.get_camera_health(i)
            camera_status[i] = {
                'name': name,
                'type': cam_type,
                'company': company,
                'nsfw': nsfw,
                'status': health['status'],
                'last_success': health['last_success'],
                'errors': health['total_errors'],
                'response_time': health['avg_response_time'],
                'recording': i in recording_status
            }
        
        return {
            'system': system_info,
            'cameras': camera_status,
            'recordings': recording_status,
            'cache_size': len(self.frame_cache.cache),
            'active_threads': len([t for t in self.camera_tasks.values() if not t.done()])
        }
    
    def get_display_frame(self):
        """Get the frame to display - either grid or single camera"""
        # Wait for at least one frame
        while not self.frames and self.running:
            time.sleep(0.05)  # Faster initial loading
        
        if self.selected_camera is not None:
            # Single camera view
            return self.get_single_camera_frame()
        else:
            # Grid view (paged or all cameras)
            if self.show_all_cameras:
                return self.get_all_cameras_frame()
            else:
                return self.get_grid_frame()
    
    def get_all_cameras_frame(self):
        """Get view of all cameras in screen-fitting tiles with company indicators"""
        # Calculate optimal tile size based on screen constraints
        # Target: fit all 277 cameras on screen
        max_width = 1800  # Leave margin for window borders
        max_height = 900  # Leave margin for title and controls
        
        num_cameras = len(self.cams)
        
        # Calculate grid layout for all cameras (277 cameras)
        if num_cameras <= 12:
            cols, rows = 4, 3
        elif num_cameras <= 20:
            cols, rows = 5, 4
        elif num_cameras <= 30:
            cols, rows = 6, 5
        elif num_cameras <= 42:
            cols, rows = 7, 6
        elif num_cameras <= 56:
            cols, rows = 8, 7
        elif num_cameras <= 72:
            cols, rows = 9, 8
        elif num_cameras <= 90:
            cols, rows = 10, 9
        elif num_cameras <= 110:
            cols, rows = 11, 10
        elif num_cameras <= 132:
            cols, rows = 12, 11
        elif num_cameras <= 156:
            cols, rows = 13, 12
        elif num_cameras <= 182:
            cols, rows = 14, 13
        elif num_cameras <= 210:
            cols, rows = 15, 14
        elif num_cameras <= 240:
            cols, rows = 16, 15
        elif num_cameras <= 272:
            cols, rows = 17, 16
        else:
            # For 277+ cameras: 18x16 grid (288 capacity)
            cols, rows = 18, 16
        
        tile_width = min(100, max_width // cols)  # Much smaller tiles to fit 277 cameras
        tile_height = min(56, max_height // rows)  # Maintain aspect ratio (16:9)
        
        # Define company colors for visual identification (only for specific companies)
        company_colors = {
            'Company A': (255, 191, 0),           # Deep Sky Blue (BGR)
            'Axis Communications': (180, 105, 255), # Hot Pink (BGR)
            'Private House': (128, 0, 128),       # Purple (BGR)
            'Korea Cams': (50, 205, 50),          # Lime Green (BGR)
            'Korea Multi-Cam': (0, 215, 255),     # Gold (BGR)
            'Netherlands Cams': (0, 69, 255),     # Orange Red (BGR)
            'Turkey Multi-Cam': (60, 20, 220)     # Crimson (BGR)
        }
        
        # Get unique companies for legend
        companies = set()
        for i in range(len(self.cams)):
            if i < len(self.cams):
                camera_data = self.cams[i]
                if len(camera_data) >= 6:
                    company = camera_data[5]
                else:
                    company = 'Unknown'
                companies.add(company)
        
        frame_list = []
        for i in range(len(self.cams)):
            if i in self.frames:
                # Resize to calculated tile size
                frame = cv2.resize(self.frames[i], (tile_width, tile_height), 
                                 interpolation=cv2.INTER_LINEAR)
                
                # Get company info
                camera_data = self.cams[i]
                if len(camera_data) >= 6:
                    company = camera_data[5]
                else:
                    company = 'Unknown'
                company_color = company_colors.get(company)
                
                # Add camera number with appropriate font size
                font_scale = 0.4 if tile_width < 200 else 0.6
                cv2.putText(frame, f"{i+1}", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2)
                cv2.putText(frame, f"{i+1}", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1)
                
                # Add company-colored border only for specific companies
                if company_color:
                    cv2.rectangle(frame, (0, 0), (tile_width-1, tile_height-1), company_color, 2)
                
                    # Add company indicator in bottom-right corner
                    company_short = company[:6] + "..." if len(company) > 6 else company
                    text_size = cv2.getTextSize(company_short, cv2.FONT_HERSHEY_SIMPLEX, 0.25, 1)[0]
                    text_x = tile_width - text_size[0] - 3
                    text_y = tile_height - 3
                    
                    # Add background for company text
                    cv2.rectangle(frame, (text_x - 1, text_y - text_size[1] - 1), 
                                 (text_x + text_size[0] + 1, text_y + 1), (0, 0, 0), -1)
                    cv2.putText(frame, company_short, (text_x, text_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.25, company_color, 1)
                
                frame_list.append(frame)
            else:
                # Placeholder frame
                placeholder = np.zeros((tile_height, tile_width, 3), dtype=np.uint8)
                font_scale = 0.4 if tile_width < 200 else 0.5
                cv2.putText(placeholder, f"CAM {i+1}", (5, tile_height//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 0), 1)
                cv2.putText(placeholder, "LOADING", (5, tile_height//2 + 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, (128, 128, 128), 1)
                
                # Add company border for loading cameras too (only for specific companies)
                if i < len(self.cams):
                    camera_data = self.cams[i]
                    if len(camera_data) >= 6:
                        company = camera_data[5]
                    else:
                        company = 'Unknown'
                    company_color = company_colors.get(company)
                    if company_color:
                        cv2.rectangle(placeholder, (0, 0), (tile_width-1, tile_height-1), company_color, 2)
                
                frame_list.append(placeholder)
        
        # Calculate optimal grid for cameras with screen fitting
        num_cameras = len(frame_list)
        
        # Use adaptive grid based on camera count and screen size - UPDATED FOR 277 CAMERAS
        if num_cameras <= 12:
            cols, rows = 4, 3
        elif num_cameras <= 20:
            cols, rows = 5, 4
        elif num_cameras <= 30:
            cols, rows = 6, 5
        elif num_cameras <= 42:
            cols, rows = 7, 6
        elif num_cameras <= 56:
            cols, rows = 8, 7
        elif num_cameras <= 72:
            cols, rows = 9, 8
        elif num_cameras <= 90:
            cols, rows = 10, 9
        elif num_cameras <= 110:
            cols, rows = 11, 10
        elif num_cameras <= 132:
            cols, rows = 12, 11
        elif num_cameras <= 156:
            cols, rows = 13, 12
        elif num_cameras <= 182:
            cols, rows = 14, 13
        elif num_cameras <= 210:
            cols, rows = 15, 14
        elif num_cameras <= 240:
            cols, rows = 16, 15
        elif num_cameras <= 272:
            cols, rows = 17, 16
        else:
            # For 277+ cameras: 18x16 grid (288 capacity)
            cols, rows = 18, 16
        
        # Recalculate tile size for final grid
        tile_width = min(100, max_width // cols)  # Much smaller tiles for 277 cameras
        tile_height = min(56, max_height // rows)  # Much smaller tiles for 277 cameras
        
        # Resize all frames to final tile size
        final_frame_list = []
        for i, frame in enumerate(frame_list):
            if frame.shape[0] != tile_height or frame.shape[1] != tile_width:
                frame = cv2.resize(frame, (tile_width, tile_height), interpolation=cv2.INTER_LINEAR)
            final_frame_list.append(frame)
        
        # Create grid
        grid_frames = []
        for row in range(rows):
            row_frames = []
            for col in range(cols):
                idx = row * cols + col
                if idx < len(frame_list):
                    row_frames.append(frame_list[idx])
                else:
                    # Empty placeholder
                    empty_frame = np.zeros((tile_height, tile_width, 3), dtype=np.uint8)
                    cv2.putText(empty_frame, "EMPTY", (tile_width//2-25, tile_height//2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (64, 64, 64), 1)
                    row_frames.append(empty_frame)
            grid_frames.append(np.hstack(row_frames))
        
        combined = np.vstack(grid_frames)
        
        # Add title with appropriate font size
        title_font_scale = 0.9 if combined.shape[1] < 1600 else 1.2
        cv2.putText(combined, f"ALL CAMERAS VIEW - {len(self.cams)} cameras", (20, 35), 
                   cv2.FONT_HERSHEY_SIMPLEX, title_font_scale, (0, 255, 255), 3)
        cv2.putText(combined, f"ALL CAMERAS VIEW - {len(self.cams)} cameras", (20, 35), 
                   cv2.FONT_HERSHEY_SIMPLEX, title_font_scale, (0, 0, 0), 1)
        
        # Add camera info
        video_count = 0
        image_count = 0
        
        for camera_data in self.cams:
            if len(camera_data) >= 5:
                cam_type = camera_data[4]  # type is at index 4
                if cam_type == "video":
                    video_count += 1
                else:
                    image_count += 1
        
        info_font_scale = 0.6 if combined.shape[1] < 1600 else 0.8
        cv2.putText(combined, f"{video_count} Video Streams | {image_count} Image Cameras", 
                   (20, 65), cv2.FONT_HERSHEY_SIMPLEX, info_font_scale, (255, 255, 0), 2)
        
        # Add basic info only
        cv2.putText(combined, f"Total Size: {combined.shape[1]}x{combined.shape[0]} | Press 'a' to return to paged view", 
                   (20, combined.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return combined
    
    def get_single_camera_frame(self):
        """Get fullscreen view of selected camera - CLEAN VERSION"""
        cam_id = self.selected_camera
        
        if cam_id in self.frames:
            # Use original high-res frame if available for any camera
            if cam_id in self.original_frames:
                base_frame = self.original_frames[cam_id].copy()
            else:
                # Use regular frame and resize to fullscreen
                base_frame = cv2.resize(self.frames[cam_id], 
                                      (self.settings['fullscreen_width'], self.settings['fullscreen_height']),
                                      interpolation=cv2.INTER_LINEAR)
            
            # Apply zoom if needed
            if self.zoom_level > 1.0:
                frame = self.apply_zoom(base_frame)
            else:
                # For high-res frames, resize to fit screen while maintaining aspect ratio
                if cam_id in self.original_frames:
                    frame = self.resize_to_fit_screen(base_frame)
                else:
                    frame = base_frame
            
            # Add back button (top-left corner)
            cv2.rectangle(frame, (10, 10), (90, 40), (0, 0, 0), -1)  # Black background
            cv2.rectangle(frame, (10, 10), (90, 40), (255, 255, 255), 2)  # White border
            cv2.putText(frame, "BACK", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # ONLY show camera number, company (if available), and city - NOTHING ELSE
            camera_config = self.config['cameras'][cam_id] if cam_id < len(self.config['cameras']) else {}
            camera_name = self.cams[cam_id][3]
            
            # Extract camera number and city from name
            camera_number = cam_id + 1
            
            # Extract city from name (format: "Camera X - City" or "Camera X (Type) - City")
            city = ""
            if " - " in camera_name:
                city = camera_name.split(" - ")[-1]  # Get everything after last " - "
            
            # Get company if available
            company = camera_config.get('company', '')
            
            # Build display text - only show what's available
            display_lines = []
            display_lines.append(f"Camera {camera_number}")
            
            # Company (only if available and not 'Unknown')
            if company and company != 'Unknown':
                display_lines.append(company)
            
            # City (only if available)
            if city:
                display_lines.append(city)
            
            # Calculate text area size for fullscreen
            max_width = 0
            line_height = 35  # Larger for fullscreen
            font_scale = 0.8  # Larger font for fullscreen
            for line in display_lines:
                text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
                max_width = max(max_width, text_size[0])
            
            # Create background for text (top-right corner)
            bg_height = len(display_lines) * line_height + 20
            x_pos = frame.shape[1] - max_width - 30
            overlay = frame.copy()
            cv2.rectangle(overlay, (x_pos - 10, 10), (frame.shape[1] - 10, bg_height), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            
            # Draw text lines (top-right corner)
            y_pos = 40
            for line in display_lines:
                cv2.putText(frame, line, (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2)
                y_pos += line_height
            
            return frame
        else:
            # Camera not available, show placeholder
            placeholder = np.zeros((self.settings['fullscreen_height'], self.settings['fullscreen_width'], 3), dtype=np.uint8)
            cv2.putText(placeholder, "LOADING CAMERA...", (self.settings['fullscreen_width']//2-150, self.settings['fullscreen_height']//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)
            
            # Add back button
            cv2.rectangle(placeholder, (10, 10), (90, 40), (0, 0, 0), -1)
            cv2.rectangle(placeholder, (10, 10), (90, 40), (255, 255, 255), 2)
            cv2.putText(placeholder, "BACK", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            return placeholder
            cv2.rectangle(placeholder, (10, 10), (90, 40), (255, 255, 255), 2)
            cv2.putText(placeholder, "BACK", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            return placeholder
    
    def resize_to_fit_screen(self, frame):
        """Resize high-res frame to fit screen while maintaining aspect ratio"""
        h, w = frame.shape[:2]
        screen_w = self.settings['fullscreen_width']
        screen_h = self.settings['fullscreen_height']
        
        # Calculate scaling factor to fit screen
        scale_w = screen_w / w
        scale_h = screen_h / h
        scale = min(scale_w, scale_h)
        
        # Calculate new dimensions
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Resize frame
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Create black background and center the image
        result = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)
        y_offset = (screen_h - new_h) // 2
        x_offset = (screen_w - new_w) // 2
        result[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        return result
    
    def apply_zoom(self, frame):
        """Apply zoom and pan to frame"""
        h, w = frame.shape[:2]
        
        # Calculate the size of the zoomed region
        zoom_w = int(w / self.zoom_level)
        zoom_h = int(h / self.zoom_level)
        
        # Calculate the center of the zoom region
        center_x = int(self.zoom_center_x * w)
        center_y = int(self.zoom_center_y * h)
        
        # Calculate crop boundaries
        x1 = max(0, center_x - zoom_w // 2)
        y1 = max(0, center_y - zoom_h // 2)
        x2 = min(w, x1 + zoom_w)
        y2 = min(h, y1 + zoom_h)
        
        # Adjust if we're at the edges
        if x2 - x1 < zoom_w:
            x1 = max(0, x2 - zoom_w)
        if y2 - y1 < zoom_h:
            y1 = max(0, y2 - zoom_h)
        
        # Crop and resize
        cropped = frame[y1:y2, x1:x2]
        zoomed = cv2.resize(cropped, (self.settings['fullscreen_width'], self.settings['fullscreen_height']))
        
        return zoomed
    
    def get_grid_frame(self):
        """Get the grid view of current page cameras with navigation"""
        current_cameras = self.get_current_page_cameras()
        
        # Create frames list for current page
        frame_list = []
        for global_idx, cam_data in current_cameras:
            if global_idx in self.frames:
                # Ensure frame is correct size for grid
                frame = cv2.resize(self.frames[global_idx], (self.settings['cam_width'], self.settings['cam_height']))
                
                # Add click indicator border
                cv2.rectangle(frame, (0, 0), (self.settings['cam_width']-1, self.settings['cam_height']-1), (0, 255, 0), 2)
                
                frame_list.append(frame)
            else:
                # Placeholder frame
                placeholder = np.zeros((self.settings['cam_height'], self.settings['cam_width'], 3), dtype=np.uint8)
                cv2.putText(placeholder, "LOADING...", (10, self.settings['cam_height']//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                cv2.putText(placeholder, cam_data[3], (10, self.settings['cam_height']//2 + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
                frame_list.append(placeholder)
        
        # Calculate grid layout for current page
        num_cameras = len(frame_list)
        if num_cameras == 0:
            # Empty page
            empty_frame = np.zeros((400, 600, 3), dtype=np.uint8)
            cv2.putText(empty_frame, "NO CAMERAS ON THIS PAGE", (100, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            return empty_frame
        
        cols, rows = self.calculate_grid_layout(num_cameras)
        
        # Create grid
        grid_frames = []
        for row in range(rows):
            row_frames = []
            for col in range(cols):
                idx = row * cols + col
                if idx < len(frame_list):
                    row_frames.append(frame_list[idx])
                else:
                    # Empty placeholder
                    empty_frame = np.zeros((self.settings['cam_height'], self.settings['cam_width'], 3), dtype=np.uint8)
                    cv2.putText(empty_frame, "EMPTY", (self.settings['cam_width']//2-30, self.settings['cam_height']//2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (64, 64, 64), 1)
                    row_frames.append(empty_frame)
            grid_frames.append(np.hstack(row_frames))
        
        combined = np.vstack(grid_frames)
        
        # Add page navigation info
        page_info = f"Page {self.current_page + 1}/{self.total_pages} | Cameras {self.current_page * self.cameras_per_page + 1}-{min((self.current_page + 1) * self.cameras_per_page, len(self.cams))} of {len(self.cams)}"
        cv2.putText(combined, page_info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Add navigation instructions
        nav_text = "Up/Down arrows: Change page | Click camera for fullscreen | 'a': All cameras view"
        cv2.putText(combined, nav_text, (10, combined.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add controls info
        controls_text = "'c': Config | 's': Screenshot | 'q': Quit"
        cv2.putText(combined, controls_text, (10, combined.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return combined

    def get_frame_as_jpeg(self, camera_id=None):
        """Get frame as high-quality JPEG bytes for web interface - OPTIMIZED"""
        if camera_id is not None:
            # For individual camera feeds
            if camera_id in self.frames:
                frame = self.frames[camera_id]
                
                # Resize for web to reduce bandwidth
                if frame.shape[0] > 480 or frame.shape[1] > 640:
                    frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_LINEAR)
                
                # Use lower quality for web streaming to reduce CPU load
                jpeg_quality = 70  # Reduced from 95
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
                ret, buffer = cv2.imencode('.jpg', frame, encode_param)
                if ret:
                    return buffer.tobytes()
            return None
        else:
            # For main display frame
            frame = self.get_display_frame()
            if frame is not None:
                # Resize for web display
                if frame.shape[0] > 720 or frame.shape[1] > 1280:
                    frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_LINEAR)
                
                jpeg_quality = 75
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
                ret, buffer = cv2.imencode('.jpg', frame, encode_param)
                if ret:
                    return buffer.tobytes()
        return None

    def run(self):
        """Main viewer loop with interactive features"""
        print("🚀 Starting ELI6 Professional Surveillance System")
        print("=" * 60)
        print(f"📹 Total Cameras: {len(self.cams)}")
        
        # Count video vs image cameras
        video_count = 0
        image_count = 0
        nsfw_count = 0
        
        for camera_data in self.cams:
            if len(camera_data) >= 7:
                url, user, pwd, name, cam_type, company, nsfw = camera_data
            else:
                # Handle legacy format without nsfw field
                url, user, pwd, name, cam_type, company = camera_data
                nsfw = False
            
            if cam_type == "video":
                video_count += 1
            else:
                image_count += 1
                
            if nsfw:
                nsfw_count += 1
        
        print(f"🎥 Video Streams: {video_count} cameras")
        print(f"📷 Image Cameras: {image_count} cameras")
        if nsfw_count > 0:
            print(f"🔒 Private Cameras: {nsfw_count} cameras")
        print(f"🌐 Web Interface: http://localhost:{self.settings['web_port']}")
        print("")
        print("🎮 CONTROLS:")
        print("  • Click camera: Fullscreen view")
        print("  • Up/Down arrows or 'p'/'n': Navigate pages")
        print("  • 'a': Toggle all cameras view")
        print("  • Mouse wheel: Zoom in fullscreen mode")
        print("  • 'r': Start/stop recording active camera")
        print("  • 'q': Quit, 's': Screenshot, 'c': Config")
        print("=" * 60)
        logger.info(f"Professional surveillance system initialized with {len(self.cams)} cameras")
        
        # Start camera threads using the new advanced system
        threads = self.start_threads()
        
        try:
            while self.running:
                # Get display frame (grid or single camera)
                combined = self.get_display_frame()
                
                # Show frame
                cv2.imshow("ELI6 Webcams - Surveillance System", combined)
                
                # Set mouse callback if not already set
                if not self.mouse_callback_set:
                    cv2.setMouseCallback("ELI6 Webcams - Surveillance System", self.mouse_callback)
                    self.mouse_callback_set = True
                
                # Handle keys
                key = cv2.waitKey(50) & 0xFF  # Faster display refresh (20 FPS)
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    timestamp = int(time.time())
                    if self.selected_camera is not None:
                        filename = f"camera_{self.selected_camera + 1}_capture_{timestamp}.jpg"
                    else:
                        filename = f"grid_capture_{timestamp}.jpg"
                    cv2.imwrite(filename, combined)
                    print(f"Screenshot saved: {filename}")
                elif key == ord('c'):
                    self.open_config_gui()
                elif key == ord('b') or key == 27:  # 'b' key or ESC key
                    if self.selected_camera is not None:
                        self.selected_camera = None
                        self.zoom_level = 1.0  # Reset zoom
                        # Resume all cameras when returning to grid
                        self.resume_all_cameras()
                        print("Returning to grid view")
                elif key == ord('r'):  # 'r' key for recording
                    if self.selected_camera is not None:
                        # Toggle recording for active camera
                        cam_id = self.selected_camera
                        camera_name = self.cams[cam_id][3]
                        
                        if cam_id in self.recording_manager.recording_sessions:
                            success, result = self.recording_manager.stop_recording(cam_id)
                            action = "stopped"
                        else:
                            success, result = self.recording_manager.start_recording(cam_id, camera_name, 10)  # 10 minutes
                            action = "started"
                        
                        if success:
                            logger.info(f"Recording {action} for {camera_name}")
                        else:
                            logger.error(f"Failed to {action.replace('ed', '')} recording: {result}")
                elif key == ord('a'):  # Toggle all cameras view
                    if self.selected_camera is None:
                        self.show_all_cameras = not self.show_all_cameras
                        mode = "all cameras" if self.show_all_cameras else "paged"
                        print(f"Switched to {mode} view")
                elif key == 82 or key == ord('p'):  # Up arrow key or 'p'
                    if not self.show_all_cameras and self.selected_camera is None:
                        self.current_page = max(0, self.current_page - 1)
                        print(f"Page {self.current_page + 1}/{self.total_pages}")
                elif key == 84 or key == ord('n'):  # Down arrow key or 'n'
                    if not self.show_all_cameras and self.selected_camera is None:
                        self.current_page = min(self.total_pages - 1, self.current_page + 1)
                        print(f"Page {self.current_page + 1}/{self.total_pages}")

        
        except KeyboardInterrupt:
            pass
        
        finally:
            logger.info("Shutting down surveillance system...")
            self.running = False
            
            # Shutdown thread pool
            self.thread_pool.shutdown(wait=True)
            
            # Clean up video captures
            for cam_id, cap in self.video_captures.items():
                cap.release()
            self.video_captures.clear()
            
            # Stop all recordings
            for cam_id in list(self.recording_manager.recording_sessions.keys()):
                self.recording_manager.stop_recording(cam_id)
            
            cv2.destroyAllWindows()
            logger.info("System shutdown complete")
    
    def open_config_gui(self):
        """Open configuration GUI in browser"""
        import webbrowser
        webbrowser.open(f"http://localhost:{self.settings['web_port']}/config")
        print("Configuration GUI opened in browser")

# Global viewer instance for web interface
viewer_instance = None

# Flask Web Interface
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/config')
def config():
    return render_template('config.html')

@app.route('/api/system/status')
def get_system_status():
    """Get comprehensive system status"""
    if viewer_instance:
        return jsonify(viewer_instance.get_system_status())
    return jsonify({'error': 'System not initialized'}), 500

@app.route('/api/system/performance')
def get_system_performance():
    """Get detailed system performance metrics"""
    if viewer_instance:
        system_info = viewer_instance.system_monitor.get_system_info()
        return jsonify({
            'cpu': {
                'current': system_info['cpu_current'],
                'average': system_info['cpu_avg'],
                'cores': system_info['cpu_count'],
                'history': system_info['performance_history']['cpu']
            },
            'memory': {
                'current': system_info['memory_current'],
                'average': system_info['memory_avg'],
                'total_gb': round(system_info['memory_total'] / (1024**3), 1),
                'available_gb': round(system_info['memory_available'] / (1024**3), 1),
                'history': system_info['performance_history']['memory']
            },
            'disk': {
                'current': system_info['disk_current'],
                'average': system_info['disk_avg'],
                'total_gb': round(system_info['disk_total'] / (1024**3), 1),
                'free_gb': round(system_info['disk_free'] / (1024**3), 1),
                'history': system_info['performance_history']['disk']
            },
            'network': {
                'current': system_info['network_current'],
                'average': system_info['network_avg'],
                'history': system_info['performance_history']['network']
            },
            'temperature': system_info['temperature'],
            'uptime': system_info['uptime']
        })
    return jsonify({'error': 'System not initialized'}), 500

@app.route('/api/cameras/analytics')
def get_camera_analytics():
    """Get camera performance analytics"""
    if viewer_instance:
        camera_stats = viewer_instance.system_monitor.camera_stats
        health_stats = viewer_instance.health_monitor.get_all_health()
        
        analytics = {
            'total_cameras': len(viewer_instance.cams),
            'online_cameras': 0,
            'offline_cameras': 0,
            'unstable_cameras': 0,
            'average_fps': 0,
            'average_response_time': 0,
            'total_errors': 0,
            'camera_details': []
        }
        
        fps_values = []
        response_times = []
        
        for cam_id, health in health_stats.items():
            if health['status'] == 'online':
                analytics['online_cameras'] += 1
            elif health['status'] == 'offline':
                analytics['offline_cameras'] += 1
            else:
                analytics['unstable_cameras'] += 1
            
            analytics['total_errors'] += health['total_errors']
            
            if health['avg_response_time'] > 0:
                response_times.append(health['avg_response_time'])
            
            if cam_id in camera_stats and camera_stats[cam_id]['fps'] > 0:
                fps_values.append(camera_stats[cam_id]['fps'])
            
            # Add camera details
            camera_name = viewer_instance.cams[cam_id][3] if cam_id < len(viewer_instance.cams) else f"Camera {cam_id + 1}"
            analytics['camera_details'].append({
                'id': cam_id,
                'name': camera_name,
                'status': health['status'],
                'fps': camera_stats[cam_id]['fps'] if cam_id in camera_stats else 0,
                'response_time': health['avg_response_time'],
                'errors': health['total_errors']
            })
        
        analytics['average_fps'] = sum(fps_values) / len(fps_values) if fps_values else 0
        analytics['average_response_time'] = sum(response_times) / len(response_times) if response_times else 0
        
        return jsonify(analytics)
    return jsonify({'error': 'System not initialized'}), 500

@app.route('/api/system/alerts')
def get_system_alerts():
    """Get system alerts and warnings"""
    if viewer_instance:
        alerts = []
        system_info = viewer_instance.system_monitor.get_system_info()
        
        # CPU alerts
        if system_info['cpu_current'] > 90:
            alerts.append({
                'type': 'critical',
                'category': 'performance',
                'message': f"High CPU usage: {system_info['cpu_current']:.1f}%",
                'timestamp': time.time()
            })
        elif system_info['cpu_current'] > 75:
            alerts.append({
                'type': 'warning',
                'category': 'performance',
                'message': f"Elevated CPU usage: {system_info['cpu_current']:.1f}%",
                'timestamp': time.time()
            })
        
        # Memory alerts
        if system_info['memory_current'] > 90:
            alerts.append({
                'type': 'critical',
                'category': 'performance',
                'message': f"High memory usage: {system_info['memory_current']:.1f}%",
                'timestamp': time.time()
            })
        elif system_info['memory_current'] > 80:
            alerts.append({
                'type': 'warning',
                'category': 'performance',
                'message': f"Elevated memory usage: {system_info['memory_current']:.1f}%",
                'timestamp': time.time()
            })
        
        # Disk alerts
        if system_info['disk_current'] > 95:
            alerts.append({
                'type': 'critical',
                'category': 'storage',
                'message': f"Disk space critically low: {system_info['disk_current']:.1f}%",
                'timestamp': time.time()
            })
        elif system_info['disk_current'] > 85:
            alerts.append({
                'type': 'warning',
                'category': 'storage',
                'message': f"Disk space running low: {system_info['disk_current']:.1f}%",
                'timestamp': time.time()
            })
        
        # Temperature alerts
        if system_info['temperature'] and system_info['temperature'] > 80:
            alerts.append({
                'type': 'critical',
                'category': 'hardware',
                'message': f"High system temperature: {system_info['temperature']:.1f}°C",
                'timestamp': time.time()
            })
        elif system_info['temperature'] and system_info['temperature'] > 70:
            alerts.append({
                'type': 'warning',
                'category': 'hardware',
                'message': f"Elevated system temperature: {system_info['temperature']:.1f}°C",
                'timestamp': time.time()
            })
        
        # Camera alerts
        offline_cameras = len(viewer_instance.cams) - system_info['active_cameras']
        if offline_cameras > len(viewer_instance.cams) * 0.5:  # More than 50% offline
            alerts.append({
                'type': 'critical',
                'category': 'cameras',
                'message': f"Many cameras offline: {offline_cameras}/{len(viewer_instance.cams)}",
                'timestamp': time.time()
            })
        elif offline_cameras > len(viewer_instance.cams) * 0.2:  # More than 20% offline
            alerts.append({
                'type': 'warning',
                'category': 'cameras',
                'message': f"Some cameras offline: {offline_cameras}/{len(viewer_instance.cams)}",
                'timestamp': time.time()
            })
        
        return jsonify({
            'alerts': alerts,
            'total_alerts': len(alerts),
            'critical_alerts': len([a for a in alerts if a['type'] == 'critical']),
            'warning_alerts': len([a for a in alerts if a['type'] == 'warning'])
        })
    return jsonify({'error': 'System not initialized'}), 500

@app.route('/api/cameras/health')
def get_cameras_health():
    """Get health status for all cameras"""
    if viewer_instance:
        return jsonify(viewer_instance.health_monitor.get_all_health())
    return jsonify({'error': 'System not initialized'}), 500

@app.route('/api/recording/start/<int:camera_id>')
def start_recording(camera_id):
    """Start recording for specific camera"""
    if viewer_instance and 0 <= camera_id < len(viewer_instance.cams):
        camera_name = viewer_instance.cams[camera_id][3]
        duration = request.args.get('duration', type=int)  # minutes
        
        success, result = viewer_instance.recording_manager.start_recording(
            camera_id, camera_name, duration
        )
        
        return jsonify({
            'success': success,
            'message': result,
            'camera_id': camera_id,
            'camera_name': camera_name
        })
    
    return jsonify({'error': 'Invalid camera ID'}), 400

@app.route('/api/recording/stop/<int:camera_id>')
def stop_recording(camera_id):
    """Stop recording for specific camera"""
    if viewer_instance:
        success, result = viewer_instance.recording_manager.stop_recording(camera_id)
        return jsonify({
            'success': success,
            'message': result,
            'camera_id': camera_id
        })
    
    return jsonify({'error': 'System not initialized'}), 500

@app.route('/api/recording/status')
def get_recording_status():
    """Get status of all active recordings"""
    if viewer_instance:
        return jsonify(viewer_instance.recording_manager.get_recording_status())
    return jsonify({'error': 'System not initialized'}), 500

@app.route('/api/backups')
def list_backups():
    """List available configuration backups"""
    if viewer_instance:
        backups = viewer_instance.backup_manager.list_backups()
        return jsonify(backups)
    return jsonify({'error': 'System not initialized'}), 500

@app.route('/api/backup/create')
def create_backup():
    """Create configuration backup"""
    if viewer_instance:
        success = viewer_instance.backup_manager.create_backup(viewer_instance.config)
        return jsonify({'success': success})
    return jsonify({'error': 'System not initialized'}), 500

@app.route('/api/settings')
def get_settings():
    config = ConfigManager.load_config()
    return jsonify(config['settings'])

@app.route('/api/cameras')
def get_cameras():
    """Get camera configuration"""
    config = ConfigManager.load_config()
    return jsonify(config['cameras'])

@app.route('/api/cameras', methods=['POST'])
def update_cameras():
    try:
        config = ConfigManager.load_config()
        config['cameras'] = request.json
        if ConfigManager.save_config(config):
            return jsonify({"success": True, "message": "Cameras updated successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to save configuration"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    try:
        config = ConfigManager.load_config()
        config['settings'] = request.json
        if ConfigManager.save_config(config):
            return jsonify({"success": True, "message": "Settings updated successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to save configuration"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/video_feed')
def video_feed():
    def generate():
        while viewer_instance and viewer_instance.running:
            frame_bytes = viewer_instance.get_frame_as_jpeg()
            if frame_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.05)  # Faster web streaming (20 FPS)
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera_feed/<int:camera_id>')
def camera_feed(camera_id):
    def generate():
        frame_count = 0
        while viewer_instance and viewer_instance.running:
            frame_bytes = viewer_instance.get_frame_as_jpeg(camera_id)
            if frame_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Adaptive frame rate based on camera type and load
            frame_count += 1
            if frame_count % 10 == 0:  # Every 10th frame, check system load
                active_streams = len([t for t in viewer_instance.camera_tasks.values() if not t.done()])
                if active_streams > 20:
                    time.sleep(0.2)  # 5 FPS for high load
                elif active_streams > 10:
                    time.sleep(0.1)  # 10 FPS for medium load
                else:
                    time.sleep(0.05)  # 20 FPS for low load
            else:
                time.sleep(0.1)  # Default 10 FPS for web interface
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera_thumbnail/<int:camera_id>')
def camera_thumbnail(camera_id):
    """Serve static thumbnail for camera grid - reduces CPU load"""
    if not viewer_instance:
        logger.warning(f"Viewer instance not available for camera {camera_id}")
        return Response(b'', mimetype='image/jpeg', status=503)
    
    # Check if camera_id is valid
    if camera_id >= len(viewer_instance.cams):
        logger.warning(f"Invalid camera_id {camera_id}, max is {len(viewer_instance.cams)-1}")
        return Response(b'', mimetype='image/jpeg', status=404)
    
    # Try to get frame
    if camera_id in viewer_instance.frames:
        frame_bytes = viewer_instance.get_frame_as_jpeg(camera_id)
        if frame_bytes:
            return Response(frame_bytes, mimetype='image/jpeg')
        else:
            logger.debug(f"No frame bytes for camera {camera_id}")
    else:
        logger.debug(f"Camera {camera_id} not in frames dict. Available: {len(viewer_instance.frames)} cameras")
    
    # Return placeholder image if camera not available
    placeholder = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\xf0\x01@\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
    return Response(placeholder, mimetype='image/jpeg')

def run_web_server(config):
    """Run the web server in a separate thread"""
    app.run(host=config['settings']['web_host'], 
            port=config['settings']['web_port'], 
            debug=False, 
            use_reloader=False)

def main():
    global viewer_instance
    
    # Load configuration
    config = ConfigManager.load_config()
    
    # Create viewer instance
    viewer_instance = InteractiveCameraViewer(config)
    
    # Start web server in background
    web_thread = threading.Thread(target=run_web_server, args=(config,))
    web_thread.daemon = True
    web_thread.start()
    
    # Run the main viewer
    viewer_instance.run()

if __name__ == "__main__":
    main()