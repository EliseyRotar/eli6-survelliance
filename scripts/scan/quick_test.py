import urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HOST = "103.30.71.181"

for ch in ["1", "2", "3", "4"]:
    try:
        url = f"http://{HOST}/webcapture.jpg?command=snap&channel={ch}"
        resp = urllib.request.urlopen(url, timeout=3, context=ctx)
        data = resp.read()
        is_jpeg = data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'
        print(f"channel={ch}: {len(data)} bytes, JPEG={is_jpeg}")
    except Exception as e:
        print(f"channel={ch}: Error - {e}")