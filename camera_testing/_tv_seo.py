import re
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\_blog_sample.html', encoding='utf-8', errors='replace') as f:
    html = f.read()
matches = re.findall(r'data-seo-([\w-]+)=["\']([^"\']+)', html)
print('data-seo attributes:', len(matches))
for k, v in matches[:20]:
    print(f'  {k}: {v[:200]}')
nd = re.search(r'__NEXT_DATA__[^>]*>([^<]+)<', html)
if nd:
    print('\nNEXT_DATA found:', len(nd.group(1)))
    print(nd.group(1)[:1000])
else:
    print('\nNo NEXT_DATA')
# Look for SEO content section
seo_section = re.search(r'<section[^>]*data-seo-content[^>]*>(.*?)</section>', html, re.DOTALL)
if seo_section:
    print('\nSEO section length:', len(seo_section.group(1)))
    # Find video sources
    srcs = re.findall(r'src=["\']([^"\']+)', seo_section.group(1))
    print('srcs in SEO:', len(srcs))
    for s in srcs[:10]:
        print(' ', s[:200])
    # Find any URLs
    urls = re.findall(r'https?://[^"\'<>\s]+', seo_section.group(1))
    print('\nAll URLs in SEO:', len(urls))
    for u in urls[:10]:
        print(' ', u[:200])
