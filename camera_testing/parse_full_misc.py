import re, html
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\amhilton_misc_html_200210.html') as f:
    h = f.read()
h = re.sub(r'<script.*?</script>', '', h, flags=re.DOTALL | re.IGNORECASE)
h = re.sub(r'<style.*?</style>', '', h, flags=re.DOTALL | re.IGNORECASE)
h = re.sub(r'<!--.*?-->', '', h, flags=re.DOTALL)
t = re.sub(r'<[^>]+>', ' ', h)
t = html.unescape(t)
t = re.sub(r'\s+', ' ', t).strip()
print(t)
