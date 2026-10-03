import re, html
files = [
    (r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_wb_2014.html', 'main 2014'),
    (r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_furiousd_wb_2014.html', 'furiousd 2014'),
    (r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_tank_wb_2014.html', 'tank 2014'),
    (r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_misc_wb_2014.html', 'misc 2014'),
]
for f, name in files:
    print('===', name)
    with open(f) as ff:
        h = ff.read()
    h = re.sub(r'<script.*?</script>', '', h, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r'<style.*?</style>', '', h, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r'<!--.*?-->', '', h, flags=re.DOTALL)
    srcs = re.findall(r'src="([^"]+)"', h)[:5]
    print('IMGS:', srcs)
    t = re.sub(r'<[^>]+>', ' ', h)
    t = html.unescape(t)
    t = re.sub(r'\s+', ' ', t).strip()
    print('TEXT:', t[:600])
    print()
