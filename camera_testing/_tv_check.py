import urllib.request, socket, re
socket.setdefaulttimeout(15)
# Get all assets including lazy-loaded
req = urllib.request.Request('https://trafficvision.live/', headers={'User-Agent':'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
html = r.read().decode('utf-8', errors='replace')
# Look for manifest or sources endpoint
manifest_matches = re.findall(r'manifest[^"\s]*["\']([^"\']+)', html)
print('manifest matches:', manifest_matches[:10])
sources_matches = re.findall(r'sources[\.\[\]\s]*(?:url|endpoint|file)["\']([^"\']+)', html)
print('sources matches:', sources_matches[:10])
# Find api.trafficvision.live URLs
api_matches = re.findall(r'api\.trafficvision\.live[^"\']*', html)
print('api URLs:', api_matches[:10])
# Find any URL ending in .json
json_urls = re.findall(r'(https?://[^"\']+\.json)', html)
print('JSON URLs:', json_urls[:20])
# Look for any other CDN
cdn_matches = re.findall(r'([a-z0-9.-]+\.trafficvision\.live)', html)
print('TV subdomains:', list(set(cdn_matches)))
