"""Query Windy + worldcam for Ruse BG cams via API.

Windy API: https://node.windy.com/webcams/v2.0/list
Worldcam API: https://www.worldcam.pl/api (or via image URL substitution)
"""

import json
import os
import re
import urllib.request
import time

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT = os.path.join(WORKDIR, "dossier_ruse", "webcams")
os.makedirs(OUT, exist_ok=True)

# Ruse coordinates: 43.82306°N, 25.95389°E
LAT = 43.82306
LON = 25.95389


def get(url, timeout=20):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  err {url}: {e}")
        return None


# 1. Windy cams
print("[Windy] Querying Ruse cams...")
windy_urls = []
for radius_km in [10, 25, 50, 100]:
    url = f'https://node.windy.com/webcams/v2.0/list?nearby={LAT},{LON}&radius={radius_km}&limit=50'
    print(f"  radius={radius_km}km...", end="", flush=True)
    data = get(url)
    if data:
        try:
            d = json.loads(data)
            cams = d.get("cams", d.get("result", {}).get("webcams", []))
            if isinstance(cams, list) and cams:
                windy_urls.extend(cams)
                print(f"  {len(cams)} cams")
                break
            else:
                print(f"  0 cams")
        except Exception as e:
            print(f"  parse err: {e}")
    else:
        print(f"  no data")

with open(os.path.join(OUT, "windy_ruse.json"), 'w') as f:
    json.dump(windy_urls, f, indent=2)
print(f"[Windy] Saved {len(windy_urls)} cams")

# 2. worldcam - try API
print("\n[Worldcam] Querying...")
wc_urls = []
for radius_km in [10, 25, 50, 100]:
    url = f'https://www.worldcam.eu/api/webcams/nearby?lat={LAT}&lon={LON}&radius={radius_km}'
    data = get(url)
    if data:
        try:
            d = json.loads(data)
            cams = d if isinstance(d, list) else d.get("cams", [])
            wc_urls.extend(cams)
            print(f"  radius={radius_km}km: {len(cams)} cams")
            break
        except Exception:
            print(f"  no json")

# Save
with open(os.path.join(OUT, "worldcam_ruse.json"), 'w') as f:
    json.dump(wc_urls, f, indent=2)

# 3. Try specifc worldcam IDs we found in parse (14906, 24496, 2706, 37360, 40580)
print("\n[Worldcam] Trying specific cam IDs...")
worldcam_ids = [14906, 24496, 2706, 37360, 40580]
wc_results = {}
for wc_id in worldcam_ids:
    print(f"  WC #{wc_id}...", end="", flush=True)
    url = f'https://www.worldcam.eu/webcams/europe/bulgaria/{wc_id}-*'
    data = get(url)
    if data:
        # Save
        with open(os.path.join(OUT, f"worldcam_{wc_id}.html"), 'w', encoding='utf-8') as f:
            f.write(data)
        wc_results[wc_id] = data[:500]
    else:
        wc_results[wc_id] = "no data"
    print(f"  saved")
    time.sleep(0.5)

# 4. Windy cams for IDs we already found
print("\n[Windy] Probing specific cam IDs (1597690315, 1793898215, 1793902097)...")
windy_ids = [1597690315, 1793898215, 1793902097]
for w_id in windy_ids:
    url = f'https://node.windy.com/webcams/v2.0/webcam/{w_id}'
    data = get(url)
    if data:
        with open(os.path.join(OUT, f"windy_{w_id}.json"), 'w') as f:
            f.write(data)

# 5. Yandex cams (yandex_cam_id=20758 from URL pattern)
print("\n[Yandex] Trying cam ID 20758...")
yandex_data = get('https://info.weather.yandex.net/20758/3.png')  # direct image
if yandex_data:
    print(f"  Got {len(yandex_data)} bytes image data")

# 6. Webcam-Travel.com (Aggregator)
print("\n[Webcam-Travel] Ruse cams...")
wct_data = get('https://www.webcamgalore.com/webcam/webcam/Rousse.html')
if wct_data:
    with open(os.path.join(OUT, "webcamgalore_ruse.html"), 'w', encoding='utf-8') as f:
        f.write(wct_data)

# 7. Skyline webcams
print("\n[Skyline] Ruse cams...")
sk_data = get('https://www.skylinewebcams.com/en/webcam/bulgaria/rousse.html')
if sk_data:
    with open(os.path.join(OUT, "skyline_ruse.html"), 'w', encoding='utf-8') as f:
        f.write(sk_data)
    cam_urls = re.findall(r'(https?://[^\s"\'<>]+\.(?:jpg|jpeg|mjpg|mjpeg|mp4|hls|m3u8))', sk_data)
    print(f"  Found {len(cam_urls)} cam URLs")

# 8. screambain/windy embed cams
print("\n[Windy embeds] Finding all in scrollwheel places...")

print("\nDone!")
