import requests, time

key = 'jEvQy13lqyVqaTii6yC866hnlW9OFsPb'

# api-info first
r = requests.get('https://api.shodan.io/api-info', params={'key': key}, timeout=10)
print('api-info:', r.status_code, r.text[:500])
print()

if r.status_code == 200:
    j = r.json()
    print(f'plan={j.get("plan")} credits={j.get("query_credits")} / {j.get("usage_limits", {}).get("query_credits")}')
    qs = [
        'Hikvision country:"DE"',
        'product:"Hikvision IP Camera" port:80',
        'product:"webcam 7 httpd"',
        'product:yawcam',
        'Hipcam',
        'product:"webcamXP 5 httpd"',
        'product:"webcam 5 httpd"',
        '"Yawcam webcam viewer httpd"',
        'product:"Mobotix"',
        'product:"AXIS P"',
        'product:"Vivotek"',
        '"Sony Network Camera"',
        'rtsp has_screenshot:true',
        'Hipcam country:"US"',
        'webcam country:"BR"',
        'webcamxp country:"RU"',
        'webcam country:"RO"',
        'product:"webcam 7 httpd" country:"DE"',
    ]
    for q in qs:
        try:
            r2 = requests.get('https://api.shodan.io/shodan/host/search',
                               params={'key': key, 'query': q, 'limit': 5},
                               timeout=15)
            j2 = r2.json()
            n = j2.get('total', 0)
            err = j2.get('error', '')
            if err:
                print(f'  [{err[:50]}] {q}')
                break
            print(f'  total={n:>6}  {q}')
            time.sleep(1.2)
        except Exception as e:
            print(f'  err: {e}')
            break
