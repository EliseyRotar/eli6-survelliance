import re, html
files = [
    (r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_misc_html_200210.html', 'misc.html 200210'),
    (r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_new_200210.html', 'new 200210'),
    (r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_biography_2004.html', 'biography 2004'),
    (r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_tankguide_2004.html', 'tankguide 2004'),
    (r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_misc_wb_2012.html', 'misc 2012'),
]
for f, name in files:
    print('===', name)
    with open(f) as ff:
        h = ff.read()
    h = re.sub(r'<script.*?</script>', '', h, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r'<style.*?</style>', '', h, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r'<!--.*?-->', '', h, flags=re.DOTALL)
    t = re.sub(r'<[^>]+>', ' ', h)
    t = html.unescape(t)
    t = re.sub(r'\s+', ' ', t).strip()
    print(t[:1200])
    print()
