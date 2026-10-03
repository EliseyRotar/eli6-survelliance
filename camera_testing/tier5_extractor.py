"""Tier 5 extractor — for HTML pages that contain embedded cam URLs.

Scrapes:
- <iframe src=...>
- <embed src=...>
- <video src=...><source src=...>
- img src=... (full URL extraction)
- og:image, og:video
- JS strings (window.location = "..."; var x = 'http...')
- href=... with .jpg/.mjpg/.m3u8
- m3u8 playlists (recursive: parse .m3u8 for nested URLs)
"""
import re

HTML_EMBED_RE = re.compile(
    r'<(?:iframe|embed|frame|object|source)\s[^>]*?(?:src|data-src)\s*=\s*["\']([^"\']+)',
    re.I
)
VIDEO_TAG_RE = re.compile(
    r'<video[^>]*>.*?</video>', re.I | re.S
)
HREF_IMG_RE = re.compile(
    r'href\s*=\s*["\']([^"\']*\.(?:jpe?g|png|mjpg|mjpeg|m3u8|mp4)[^"\']*)',
    re.I
)
JS_URL_RE = re.compile(
    r'(?:var\s+\w+\s*=|window\.location(?:\.href)?\s*=|document\.location(?:\.href)?\s*=|["\'])((?:https?:|//)[^\s"\'<>]+)',
    re.I
)
OG_RE = re.compile(r'<meta\s+(?:name|property)\s*=\s*["\']og:(?:image|video|url)["\']\s+content\s*=\s*["\']([^"\']+)', re.I)


def extract_all(html, base_url):
    """Return list of candidate stream URLs from arbitrary HTML."""
    urls = []
    if not html:
        return urls
    # Direct embeds
    for m in HTML_EMBED_RE.finditer(html):
        urls.append(m.group(1))
    # og:image, og:video, og:url
    for m in OG_RE.finditer(html):
        urls.append(m.group(1))
    # JS string URLs (focus on stream-like)
    for m in JS_URL_RE.finditer(html):
        u = m.group(1)
        ul = u.lower()
        if any(t in ul for t in ['.m3u8', '.mjpg', '.mjpeg', 'live', 'stream', 'video', 'cam', 'image', '.mp4']):
            urls.append(u)
    # <a href="x.jpg">
    for m in HREF_IMG_RE.finditer(html):
        urls.append(m.group(1))
    # Resolve relative URLs
    resolved = []
    for u in urls:
        u = u.strip()
        if u.startswith('//'):
            u = 'https:' + u
        elif u.startswith('/'):
            try:
                from urllib.parse import urlparse, urljoin
                u = urljoin(base_url, u)
            except Exception:
                continue
        elif not u.startswith('http'):
            continue
        if 'javascript:' in u or 'data:' in u or len(u) > 1024:
            continue
        resolved.append(u)
    return list(set(resolved))[:10]


def is_stream_url(url):
    ul = url.lower()
    return (
        '.m3u8' in ul or '.m3u' in ul
        or '.mjpg' in ul or '.mjpeg' in ul
        or '.mp4' in ul
        or '/mjpeg' in ul or '/stream' in ul
        or '/video' in ul or '/cam' in ul
        or '/snapshot' in ul or '/image.jpg' in ul
        or '/videostream.cgi' in ul
        or '/axis-cgi/' in ul or '/Streaming/' in ul
        or '/ISAPI/' in ul
    )
