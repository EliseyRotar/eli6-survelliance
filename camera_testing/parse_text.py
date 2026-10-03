import re, html
files = [
    r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_links_2008.html',
    r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_tank_index_wb.html',
    r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_tank_wb_2010.html',
    r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_wb_2010_main.html',
    r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_furiousd_wb_2010.html',
]
for f in files:
    print('===', f.split('\\\\')[-1])
    with open(f) as ff:
        h = ff.read()
    # Strip script/style/comments
    h = re.sub(r'<script.*?</script>', '', h, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r'<style.*?</style>', '', h, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r'<!--.*?-->', '', h, flags=re.DOTALL)
    # Extract hrefs
    print('LINKS:')
    for m in re.findall(r'href=["\"]([^"\"]+)["\"]', h):
        if 'web.archive' not in m and 'web-static' not in m and 'bundle' not in m:
            print(' ', m)
    # Plain text
    t = re.sub(r'<[^>]+>', ' ', h)
    t = html.unescape(t)
    t = re.sub(r'\s+', ' ', t).strip()
    print('TEXT:', t[:600])
    print()
