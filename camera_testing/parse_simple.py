import re, html
files = [
    (r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_wb_200310.html', '200310 main'),
    (r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_furious_2004_v2.html', 'furious 2004'),
]
for f, name in files:
    print('===', name)
    with open(f) as ff:
        h = ff.read()
    h = re.sub(r'<script.*?</script>', '', h, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r'<style.*?</style>', '', h, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r'<!--.*?-->', '', h, flags=re.DOTALL)
    hrefs = re.findall(r'href="([^"]+)"', h)
    hrefs = [u for u in hrefs if 'web.archive' not in u and 'web-static' not in u][:10]
    print('hrefs:', hrefs)
    t = re.sub(r'<[^>]+>', ' ', h)
    t = html.unescape(t)
    t = re.sub(r'\s+', ' ', t).strip()
    print('TEXT:', t)
    print()
