#!/usr/bin/env python3
"""
Camera URL Testing Tool
Tests connectivity and response for a list of camera URLs
"""

import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import json
from datetime import datetime
import os

class CameraTester:
    def __init__(self, timeout=10, max_workers=20):
        self.timeout = timeout
        self.max_workers = max_workers
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def test_single_camera(self, url):
        """Test a single camera URL"""
        result = {
            'url': url,
            'status': 'unknown',
            'response_code': None,
            'response_time': None,
            'content_type': None,
            'content_length': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            start_time = time.time()
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response_time = time.time() - start_time
            
            result['response_code'] = response.status_code
            result['response_time'] = round(response_time, 3)
            result['content_type'] = response.headers.get('content-type', 'unknown')
            result['content_length'] = response.headers.get('content-length', 'unknown')
            
            if response.status_code == 200:
                result['status'] = 'online'
            elif response.status_code == 401:
                result['status'] = 'auth_required'
            elif response.status_code == 404:
                result['status'] = 'not_found'
            else:
                result['status'] = 'error'
                
        except requests.exceptions.Timeout:
            result['status'] = 'timeout'
            result['error'] = 'Connection timeout'
        except requests.exceptions.ConnectionError:
            result['status'] = 'connection_error'
            result['error'] = 'Connection failed'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def test_cameras(self, urls, progress_callback=None):
        """Test multiple camera URLs concurrently"""
        print(f"Testing {len(urls)} camera URLs with {self.max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.test_single_camera, url): url for url in urls}
            
            completed = 0
            for future in as_completed(future_to_url):
                result = future.result()
                self.results.append(result)
                completed += 1
                
                if progress_callback:
                    progress_callback(completed, len(urls), result)
                else:
                    print(f"Progress: {completed}/{len(urls)} - {result['url'][:50]}... - {result['status']}")
        
        return self.results
    
    def save_results(self, filename=None):
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"camera_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"Results saved to: {filename}")
        return filename
    
    def print_summary(self):
        """Print test summary"""
        if not self.results:
            print("No results to summarize")
            return
        
        status_counts = {}
        total_tests = len(self.results)
        
        for result in self.results:
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\n" + "="*60)
        print("CAMERA TEST SUMMARY")
        print("="*60)
        print(f"Total cameras tested: {total_tests}")
        print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nStatus breakdown:")
        
        for status, count in sorted(status_counts.items()):
            percentage = (count / total_tests) * 100
            print(f"  {status.upper()}: {count} ({percentage:.1f}%)")
        
        # Show online cameras
        online_cameras = [r for r in self.results if r['status'] == 'online']
        if online_cameras:
            print(f"\nONLINE CAMERAS ({len(online_cameras)}):")
            for cam in online_cameras:
                print(f"  ✓ {cam['url']} (Response: {cam['response_time']}s)")
        
        # Show cameras requiring auth
        auth_cameras = [r for r in self.results if r['status'] == 'auth_required']
        if auth_cameras:
            print(f"\nCAMERAS REQUIRING AUTHENTICATION ({len(auth_cameras)}):")
            for cam in auth_cameras:
                print(f"  🔒 {cam['url']}")


def main():
    # List of camera URLs to test
    camera_urls = [
        "http://24.134.3.9/axis-cgi/mjpg/video.cgi",
        "http://213.3.30.80:6001/axis-cgi/mjpg/video.cgi",
        "http://118.21.111.254:65000/nphMotionJpeg?Resolution=640x480",
        "http://85.196.146.82:3337/axis-cgi/mjpg/video.cgi",
        "http://80.254.191.189:8008/axis-cgi/mjpg/video.cgi",
        "http://80.28.111.68:82/axis-cgi/mjpg/video.cgi",
        "http://82.127.206.236/axis-cgi/mjpg/video.cgi",
        "http://185.108.19.197:10800/axis-cgi/mjpg/video.cgi",
        "http://213.123.122.163:1087/axis-cgi/mjpg/video.cgi",
        "http://61.115.78.205/control/userimage.html",
        "http://173.165.152.129:8011/axis-cgi/mjpg/video.cgi",
        "http://77.60.226.189:8012/control/userimage.html",
        "http://185.74.192.88:85/axis-cgi/mjpg/video.cgi",
        "http://31.193.25.62:10002/control/userimage.html",
        "http://77.110.245.165/axis-cgi/mjpg/video.cgi",
        "http://63.42.216.178:8088/axis-cgi/mjpg/video.cgi",
        "http://128.255.86.21/axis-cgi/mjpg/video.cgi",
        "http://80.245.224.153/control/userimage.html",
        "http://142.0.109.159/axis-cgi/mjpg/video.cgi",
        "http://194.94.76.134/control/userimage.html",
        "http://213.5.145.4/control/userimage.html",
        "http://80.75.114.18/axis-cgi/mjpg/video.cgi",
        "http://91.214.62.226/control/userimage.html",
        "http://82.77.203.219:8080/control/userimage.html",
        "http://208.77.125.240:81/control/userimage.html",
        "http://155.133.206.74:8080/axis-cgi/mjpg/video.cgi",
        "http://74.95.172.65:8100/axis-cgi/mjpg/video.cgi",
        "http://79.161.6.126:9092/axis-cgi/mjpg/video.cgi",
        "http://89.97.231.70:8083/control/userimage.html",
        "http://187.141.142.149:8010/axis-cgi/mjpg/video.cgi",
        "http://63.41.124.38/control/userimage.html",
        "http://212.26.235.210/axis-cgi/mjpg/video.cgi",
        "http://208.124.240.178/axis-cgi/mjpg/video.cgi",
        "http://74.113.182.246:9600/axis-cgi/mjpg/video.cgi",
        "http://185.226.233.55:8001/axis-cgi/mjpg/video.cgi",
        "http://109.247.15.178:6001/mjpg/video.mjpg",
        "http://85.8.92.1/control/userimage.html",
        "http://194.106.254.98:1080/control/userimage.html",
        "http://115.179.100.76:8080/CgiStart?page=Single&Language=0",
        "http://58.94.98.44/CgiStart?page=Single&Language=0",
        "http://72.253.153.216:81/view/index.shtml",
        "http://14.160.87.118:82/live/index.html?Language=0",
        "http://210.248.127.20/CgiStart?page=Single&Language=0",
        "http://218.45.173.232:8000/live/index.html?Language=1&ViewMode=pull",
        "http://153.156.235.87/cgi-bin/faststream.jpg?stream=full&fps=25",
        "http://194.44.38.196:8083/view/viewer_index.shtml?id=493",
        "http://109.205.108.132/cgi-bin/faststream.jpg?stream=full&fps=25",
        "http://77.89.48.20:8003/cgi-bin/faststream.jpg?stream=full&fps=25",
        "http://166.151.98.221:7001/cgi-bin/faststream.jpg?stream=full&fps=25",
        "http://221.189.0.181/cgi-bin/guestimage.html",
        "http://195.32.24.180:1024/mjpg/video.mjpg"
    ]
    
    # Add the rest of the URLs
    extended_urls = [
        "http://185.133.99.214:8010/mjpg/video.mjpg",
        "http://213.98.123.127:8050/cgi-bin/faststream.jpg?stream=full&fps=25",
        "http://77.106.164.66/#view",
        "http://91.133.105.85:50050/cgi-bin/faststream.jpg?stream=full&fps=25",
        "http://94.139.68.110/mjpg/video.mjpg",
        "http://212.67.236.61/mjpg/video.mjpg",
        "http://185.80.208.125/#view",
        "http://37.182.240.202:82/cgi-bin/faststream.jpg",
        "http://77.242.135.139:8082/cgi-bin/faststream.jpg?stream=full&fps=25",
        "http://195.196.36.242/#view",
        "http://193.214.75.118/mjpg/video.mjpg",
        "http://178.174.58.91/mjpg/video.mjpg",
        "http://220.233.144.165:8888/mjpg/video.mjpg",
        "http://193.90.139.222:33445/mjpg/video.mjpg",
        "http://87.224.70.147:1884/mjpg/video.mjpg",
        "http://166.149.155.73:7001/cgi-bin/faststream.jpg?stream=full&fps=25",
        "http://213.128.169.233:1112/mjpg/video.mjpg",
        "http://77.222.181.11:8080/mjpg/video.mjpg",
        "http://77.110.203.114:82/mjpg/video.mjpg",
        "http://50.197.223.169/#view",
        "http://97.68.104.34/aca/index.html#view",
        "http://109.236.111.203/mjpg/video.mjpg",
        "http://80.14.201.251:8010/mjpg/video.mjpg",
        "http://87.139.9.247/#view",
        "http://166.247.77.253:81/#view",
        "http://50.197.223.170/#view",
        "http://114.179.205.142/live/index.html?Language=1",
        "http://79.8.83.39/en/index.html",
        "http://204.106.237.68:88/mjpg/1/video.mjpg",
        "http://153.156.82.99/nphMotionJpeg",
        "http://72.17.65.138/mjpg/video.mjpg",
        "http://213.236.250.78/mjpg/video.mjpg",
        "http://185.97.122.128/cgi-bin/guestimage.html",
        "http://63.142.190.238:6120/mjpg/video.mjpg",
        "http://91.192.168.58:8080/mjpg/video.mjpg",
        "http://96.91.10.219/mjpg/1/video.mjpg",
        "http://67.53.46.161:65123/mjpg/video.mjpg",
        "http://212.67.231.233/mjpg/video.mjpg",
        "http://83.136.176.101:10013/mjpg/video.mjpg",
        "http://159.130.70.206/mjpg/video.mjpg",
        "http://89.106.109.144:12060/mjpg/video.mjpg",
        "http://87.138.157.245/cgi-bin/guestimage.html",
        "http://109.109.87.147/mjpg/video.mjpg",
        "http://104.243.223.162:8082/mjpg/video.mjpg",
        "http://78.31.82.246/mjpg/video.mjpg",
        "http://77.110.219.78/mjpg/video.mjpg",
        "http://85.220.149.7/cgi-bin/guestimage.html",
        "http://50.231.121.221/axis-cgi/mjpg/video.cgi",
        "http://213.3.30.80:6001/mjpg/video.mjpg",
        "http://61.211.241.239/nphMotionJpeg?Resolution=640x480",
        "https://129.2.146.15/#view",
        "http://70.63.123.20/mjpg/1/video.mjpg",
        "http://212.170.100.189/mjpg/video.mjpg",
        "http://207.194.15.97/mjpg/video.mjpg",
        "https://82.198.200.23/mjpg/video.mjpg",
        "http://199.104.253.4/mjpg/video.mjpg",
        "http://62.214.4.38/mjpg/video.mjpg",
        "https://129.2.146.15/jpg/image.jpg",
        "http://37.128.212.84/mjpg/video.mjpg",
        "http://78.186.26.188/mjpg/1/video.mjpg",
        "http://212.41.248.38/cgi-bin/hugesize.jpg?camera=4&motion=0",
        "http://31.132.43.196:81/cgi-bin/fullsize.jpg?camera=2&motion=0",
        "http://202.174.60.121/-wvhttp-01-/image.cgi",
        "http://82.134.72.194/mjpg/video.mjpg",
        "http://195.196.36.242/mjpg/video.mjpg",
        "http://31.132.43.196:81/cgi-bin/fullsize.jpg?camera=3&motion=0",
        "http://81.167.114.67:84/mjpg/video.mjpg",
        "http://46.14.58.189/mjpg/video.mjpg",
        "http://212.41.248.38/cgi-bin/hugesize.jpg?camera=1&motion=0",
        "http://212.41.248.38/cgi-bin/hugesize.jpg?camera=3&motion=0",
        "http://185.49.169.66:1024/control/faststream.jpg?stream=full&fps=16",
        "http://live1.tusten.no:8080/axis-cgi/mjpg/video.cgi",
        "http://cam-mckeldin-eastview.umd.edu/axis-cgi/mjpg/video.cgi",
        "http://webcam.anklam.de/axis-cgi/mjpg/video.cgi",
        "http://barbadillodeherreros.dyndns.org:9001/axis-cgi/mjpg/video.cgi",
        "http://museumhallevik2.ddns.net:9501/axis-cgi/mjpg/video.cgi",
        "http://shimamaki-camera.aa0.netvolante.jp:8001/nphMotionJpeg?Resolution=320x240",
        "http://webcam.fairharbormarina.com/nphMotionJpeg?Resolution=640x480",
        "http://yakumo-fishing-circle.aa0.netvolante.jp/nphMotionJpeg?Resolution=640x480",
        "http://minigolf-paderborn.spdns.de:86/axis-cgi/mjpg/video.cgi",
        "http://x3hgy587adhfql.selfhost.eu:8080/axis-cgi/mjpg/video.cgi?resolution=4CIF&camera=3",
        "http://cam0819917993.ddns.komatsuelec.co.jp/nphMotionJpeg?Resolution=640x480&Quality=Clarity",
        "http://x3hgy587adhfql.selfhost.eu:8080/axis-cgi/mjpg/video.cgi?resolution=4CIF&camera=1",
        "http://montfarlagne.tacticddns.com:8081/axis-cgi/mjpg/video.cgi",
        "http://x3hgy587adhfql.selfhost.eu:8080/axis-cgi/mjpg/video.cgi?resolution=4CIF&camera=2",
        "http://chalet-chuenis.internet-box.ch/axis-cgi/mjpg/video.cgi",
        "http://oceanmist.ddns.net:8084/axis-cgi/mjpg/video.cgi",
        "http://cam2.aub.edu.lb/axis-cgi/mjpg/video.cgi",
        "http://webcam3.vilhelmina.se/axis-cgi/mjpg/video.cgi",
        "https://erma-stedi-cam.gmd-tg.ch/axis-cgi/mjpg/video.cgi",
        "http://webcam2.vilhelmina.se/axis-cgi/mjpg/video.cgi",
        "http://nasukashi.aa0.netvolante.jp:8192/axis-cgi/mjpg/video.cgi",
        "http://piercam.cofairhope.com/mjpg/video.mjpg",
        "http://renzo.dyndns.tv/mjpg/video.mjpg",
        "http://webcam2.minden-wlan.de:10000/axis-cgi/mjpg/video.cgi",
        "http://webcam1.vilhelmina.se/axis-cgi/mjpg/video.cgi",
        "http://webcam4.vilhelmina.se/axis-cgi/mjpg/video.cgi",
        "http://mittaghorn.mine.nu/mjpg/video.mjpg",
        "http://captainsbounty.dnsalias.com/mjpg/video.mjpg",
        "http://eyc.synology.me:10001/mjpg/video.mjpg",
        "https://webcam.vliegveldzeeland.nl:7171/axis-cgi/mjpg/video.cgi",
        "http://camera.sissiboo.com:86/mjpg/video.mjpg",
        "http://lafarge.sarl2e.fr:3100/mjpg/video.mjpg",
        "http://x3hgy587adhfql.selfhost.eu:8080/axis-cgi/mjpg/video.cgi?resolution=4CIF&camera=4",
        "http://holmen.tplinkdns.com/mjpg/video.mjpg",
        "http://htadmcam01.larimer.org/mjpg/video.mjpg",
        "http://webcam.zvnoordwijk.nl:82/mjpg/video.mjpg",
        "https://meishan.ysnp.gov.tw/axis-cgi/mjpg/video.cgi",
        "https://pavwebcam.warrnambool.vic.gov.au/axis-cgi/mjpg/video.cgi",
        "https://webcamrm.loodswezen.nl/cgi-bin/faststream.jpg?stream=full&fps=25",
        "http://camera6.city.satsumasendai.lg.jp/-wvhttp-01-/image.cgi",
        "https://webcam.duntondestinations.com/axis-cgi/mjpg/video.cgi",
        "https://csea-me-webcam.cse.umn.edu/mjpg/video.mjpg",
        "http://yukijinjya.st.wakwak.ne.jp/control/userimage.html",
        "http://webcam.agf-bw.info:8092/mjpg/video.mjpg",
        "http://kamera.mikulov.cz:8888/mjpg/video.mjpg",
        "https://ysp.ysnp.gov.tw/axis-cgi/mjpg/video.cgi",
        "http://koupaliste.velkeopatovice.cz/mjpg/video.mjpg",
        "http://cam6284208.miemasu.net/nphMotionJpeg",
        "http://honjin1.miemasu.net/nphMotionJpeg",
        "http://takemotopiano.aa1.netvolante.jp:8104/nphMotionJpeg",
        "http://takemotopiano.aa1.netvolante.jp:8102/nphMotionJpeg",
        "http://casamellow.dyndns.org/mjpg/video.mjpg",
        "http://hoybakken.dyndns.org:9876/mjpg/video.mjpg",
        "http://iyashi-webcam.st.wakwak.ne.jp/nphMotionJpeg?Resolution=320x240&Quality=Standard",
        "http://abcmaingate.dyndns.info:8081/mjpg/video.mjpg",
        "https://ipcam-1.byrd.osu.edu/mjpg/video.mjpg",
        "http://velospeer.spdns.org/mjpg/video.mjpg",
        "http://plassenburg-blick.iyxdveyshavdrmjx.myfritz.net/cgi-bin/faststream.jpg?stream=full&fps=25",
        "http://seegler.homeip.net:8888/mjpg/video.mjpg",
        "http://skycam.sebewainggigvillage.com/mjpg/video.mjpg",
        "http://mbr-cam.dyndns.org:8088/mjpg/video.mjpg",
        "http://alatsaeroclub.ddns.net:85/mjpg/video.mjpg",
        "http://ferienpenthouse34.spdns.de:4601/control/userimage.html",
        "http://mmb.aa1.netvolante.jp:1025/mjpg/video.mjpg?resolution=640x360&compression=50",
        "http://mmb.aa1.netvolante.jp:1025/mjpg/video.mjpg?resolution=640x360",
        "http://myrafjell.sodvin.no/mjpg/video.mjpg",
        "http://adlerschanze.selfhost.eu/control/userimage.html",
        "http://amrescam1.homeip.net:88/control/userimage.html",
        "https://webcam.sparkassenplatz.info/cgi-bin/faststream.jpg?stream=full&fps=25",
        "http://pendelcam.kip.uni-heidelberg.de/mjpg/video.mjpg",
        "http://www.groto.dy.fi/mjpg/video.mjpg",
        "https://camera.strandafjellet.no:8441/axis-cgi/mjpg/video.cgi",
        "http://view.dikemes.edu.gr/mjpg/video.mjpg",
        "https://romecam.mvcc.edu/mjpg/video.mjpg?timestamp=1687505435116",
        "http://e1480d3b88f7.sn.mynetname.net:91/mjpg/video.mjpg",
        "https://webcam1.lpl.org/mjpg/video.mjpg",
        "https://webcam.privcom.ch/mjpg/video.mjpg",
        "http://flightcam3.pr.erau.edu/view/view.shtml",
        "https://iihrwc03.iowa.uiowa.edu/axis-cgi/mjpg/video.cgi",
        "https://webcam.schwaebischhall.de/mjpg/video.mjpg"
    ]
    
    # Combine all URLs
    all_urls = camera_urls + extended_urls
    
    print(f"Starting camera connectivity test for {len(all_urls)} URLs...")
    print("This may take several minutes depending on network conditions.\n")
    
    # Create tester instance
    tester = CameraTester(timeout=15, max_workers=25)
    
    # Run tests
    results = tester.test_cameras(all_urls)
    
    # Print summary
    tester.print_summary()
    
    # Save results
    results_file = tester.save_results()
    
    print(f"\nDetailed results saved to: {results_file}")
    print("Test completed!")


if __name__ == "__main__":
    main()