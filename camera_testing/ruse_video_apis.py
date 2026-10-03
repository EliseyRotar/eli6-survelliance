"""Find Ruse cam video streams via API endpoints.

Most cam aggregators convert source streams to HLS. Common patterns:
- worldcam: https://www.worldcam.eu/webcams/[id] returns iframe with HLS
- webcam24: video URLs in JSON
- windy: returns HLS URL in JSON
- yandex: returns HLS URL in some endpoint

Strategy: query aggregator HTML pages for embedded video URLs.
"""

import os
import re
import urllib.request
import urllib.error
import ssl
import json

OUT_DIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_ruse\video_streams"
os.makedirs(OUT_DIR, exist_ok=True)


def fetch(url, timeout=15):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None


def find_in_text(text, pattern):
    matches = re.findall(pattern, text, re.I)
    return [m for m in matches if 'm3u8' in str(m) or 'mp4' in str(m) or 'rtsp' in str(m) or 'webm' in str(m) or 'stream' in str(m).lower() or 'video' in str(m).lower()]


def analyze_worldcam():
    """Worldcam returns cam metadata + HLS URL."""
    print('\n=== Worldcam Ruse Traffic Page ===')
    url = 'https://worldcam.eu/webcams/europe/bulgaria/33129-ruse-traffic'
    text = fetch(url)
    if text:
        # Save
        with open(os.path.join(OUT_DIR, 'worldcam_ruse_33129.html'), 'w', encoding='utf-8') as f:
            f.write(text)
        # Find video URLs
        patterns = [
            r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8|webm))',
            r'(rtsp://[^\s"\'<>]+)',
            r'(?:file|videoUrl|sourceUrl|streamUrl)["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'"(https?://[^"]+stream[^"]+)"',
            r'iframe[^>]+src=["\']([^"\']+)["\']',
        ]
        found = []
        for p in patterns:
            try:
                m = re.findall(p, text, re.I)
                for url in m:
                    found.append(url)
            except: pass
        # Also find cam references
        cam_ids = re.findall(r'/webcams/[^/]+/(\d+)-[^"\'<>]+', text)
        print(f'  Found {len(found)} URLs, {len(set(cam_ids))} cam IDs')
        # Look for player/embed config
        player_data = re.findall(r'playerData\s*=\s*({[^}]+})', text)
        if player_data:
            print(f'  Player data found:')
            for pd in player_data[:3]:
                print(f'    {pd[:200]}')
        # Sample URLs
        unique = sorted(set(found))
        for u in unique[:15]:
            if u not in ['', 'self']:
                print(f'    URL: {u[:120]}')
        return list(set(found))


def analyze_windy():
    """Windy embed returns metadata."""
    print('\n=== Windy embed ===')
    for wid in [1597690315, 1793898215, 1793902097]:
        url = f'https://webcams.windy.com/webcams/public/embed/player/{wid}'
        text = fetch(url, timeout=8)
        if text and len(text) > 100:
            # Look for video URL
            for pattern in [
                r'(?:src|file|videoUrl)["\']?\s*[=:]\s*["\']([^"\']+)["\']',
                r'(https?://[^"\']+\.m3u8[^"\']*)',
                r'(https?://[^"\']+\.mp4[^"\']*)',
                r'iframe[^>]+src=["\']([^"\']+)["\']',
            ]:
                urls = re.findall(pattern, text, re.I)
                if urls:
                    print(f'  Windy wid={wid}: {urls[:5]}')


def analyze_webcamsbg():
    """WebcamsBG aggregator."""
    print('\n=== WebcamsBG aggregator ===')
    urls_to_check = [
        'https://webcamsbg.com/ruse-live-webcam-camera-kamera-na-jivo-vremeto.html',
        'https://webcamsbg.com/cams/',
    ]
    for url in urls_to_check:
        text = fetch(url)
        if text:
            # Find video URLs
            found = re.findall(r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8|webm|webm3))', text, re.I)
            # Find img URLs with video context
            videos = re.findall(r'<video[^>]+src=["\']([^"\']+)["\']', text)
            rtsp = re.findall(r'(rtsp://[^\s"\'<>]+)', text, re.I)
            print(f'  {url}:')
            print(f'    URLs: {len(found)}, Videos: {len(videos)}, RTSP: {len(rtsp)}')
            for f in set(found)[:5]:
                print(f'      URL: {f[:120]}')


def analyze_skyline():
    """Skyline webcams - no longer exists."""
    print('\n=== Skyline Webcams ===')
    urls = [
        'https://www.skylinewebcams.com/en/webcam/bulgaria/rousse.html',
        'https://www.skylinewebcams.com/en/webcam/bulgaria/ruse.html',
    ]
    for url in urls:
        text = fetch(url, timeout=5)
        if text:
            print(f'  {url}: {len(text)} bytes')
            # Look for video
            for pattern in [
                r'playbackUrl\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
                r'src:\s*[\'"]([^\'"]+\.m3u8[^\'"]*)[\'"]',
                r'"(https?[^"]+\.(?:mp4|m3u8|webm)[^"]*)"',
                r'<source[^>]+src=[\'"]([^\'"]*\.(?:mp4|m3u8|webm)[^\'"]*)[\'"]',
            ]:
                urls = re.findall(pattern, text, re.I)
                if urls:
                    print(f'    Pattern match ({len(urls)}):')
                    for u in urls[:5]:
                        print(f'      {u[:120]}')


def analyze_easeweather():
    """Easeweather cam page."""
    print('\n=== EaseWeather ===')
    url = 'https://www.easeweather.com/europe/bulgaria/ruse/webcam'
    text = fetch(url)
    if text:
        # Search for video URLs
        for pattern in [
            r'"(https?://[^"]+\.(?:mp4|m3u8|webm)[^"]*)"',
            r'src=[\'"]([^\'"]+)[\'"].*\.mp4',
            r'<source[^>]+src=[\'"]([^\'"]*)[\'"]',
            r'youtube\.com/embed/([^"\']+)',
        ]:
            urls = re.findall(pattern, text, re.I)
            if urls:
                print(f'  Pattern matches ({len(urls)}):')
                for u in urls[:5]:
                    print(f'    {u[:120]}')


def analyze_ruselive():
    """Ruse live cams."""
    print('\n=== Ruselive ===')
    for url in ['http://ruselive.com/main_en.htm', 'http://ruselive.com']:
        text = fetch(url, timeout=10)
        if text:
            # Find all video URLs
            urls = re.findall(r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8|webm|mjpg|mjpeg))', text, re.I)
            rtsp = re.findall(r'(rtsp://[^\s"\'<>]+)', text, re.I)
            iframes = re.findall(r'iframe[^>]+src=["\']([^"\']+)["\']', text)
            videos = re.findall(r'<video[^>]+src=["\']([^"\']+)["\']', text)
            sources = re.findall(r'<source[^>]+src=["\']([^"\']+)["\']', text)
            print(f'  {url}:')
            print(f'    URLs: {len(urls)}, RTSP: {len(rtsp)}, iframes: {len(iframes)}, videos: {len(videos)}, sources: {len(sources)}')
            for u in (set(urls) | set(rtsp))[:10]:
                if len(u) > 10:
                    print(f'      {u[:140]}')


# Run all
if __name__ == '__main__':
    print('=== Ruse Cam Video Stream Finder ===')
    all_videos = {}
    try:
        u = analyze_worldcam()
        if u: all_videos['worldcam'] = u
    except Exception as e:
        print(f'Worldcam err: {e}')
    try:
        analyze_windy()
    except Exception as e:
        print(f'Windy err: {e}')
    try:
        analyze_webcamsbg()
    except Exception as e:
        print(f'WebcamsBG err: {e}')
    try:
        analyze_skyline()
    except Exception as e:
        print(f'Skyline err: {e}')
    try:
        analyze_easeweather()
    except Exception as e:
        print(f'Easeweather err: {e}')
    try:
        analyze_ruselive()
    except Exception as e:
        print(f'Ruselive err: {e}')

    # Save what we found
    with open(os.path.join(OUT_DIR, 'video_urls.json'), 'w') as f:
        json.dump(all_videos, f, indent=2)
    print(f'\nDone. Saved to {OUT_DIR}')
