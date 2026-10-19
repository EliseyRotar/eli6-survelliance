import json
import os
import re
import subprocess
import time

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
IDS = [15030, 15055, 15050, 15061, 15031, 15090, 15056, 15060, 15065, 15045,
       15040, 15024, 15100, 15083, 15010, 15114, 15115, 15111, 76100, 15080,
       15113, 15110, 15112]


def curl(args, timeout=35):
    try:
        p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', str(timeout)] + args,
                           capture_output=True, timeout=timeout + 10)
        return p.returncode, p.stdout
    except Exception as e:
        return -1, str(e).encode()


out = {}
for cid in IDS:
    rec = {}
    # webtv title + coords
    rc, body = curl(['https://webtv.feratel.com/webtv/?design=v5&cam=%d&c1=0' % cid])
    if rc == 0:
        w = body.decode('utf-8', 'replace')
        t = re.findall(r'<title>([^<]+)</title>', w)
        rec['webtv_title'] = t[0] if t else None
        rec['lat'] = (re.findall(r'infolat[^\d]*([\d.]+)', w) or [None])[0]
        rec['lon'] = (re.findall(r'infolong[^\d-]*(-?[\d.]+)', w) or [None])[0]
    # hotspot availability
    rc2, outb = curl(['-D', '-', '-o', os.devnull, '-w', '|%{http_code}|%{size_download}',
                      'https://webtvhotspot.feratel.com/hotspot/37/%d/0.jpeg?design=v3' % cid])
    meta = outb.decode('latin-1', 'replace').rsplit('|', 2)
    hdr = outb.decode('latin-1', 'replace')
    code = meta[-2] if len(meta) >= 2 else '?'
    size = meta[-1] if len(meta) >= 1 else '?'
    lm = re.search(r'[Ll]ast-[Mm]odified:\s*(.+)', hdr)
    rec['hotspot'] = {'code': code, 'size': size,
                      'last_modified': lm.group(1).strip() if lm else None}
    out[str(cid)] = rec
    print('%d | %s | %s,%s | hs=%s %sB' % (
        cid, (rec.get('webtv_title') or '?')[:78], rec.get('lat'), rec.get('lon'),
        code, size))
    time.sleep(0.7)

json.dump(out, open(os.path.join(TEMP, 'sn_feratel_all.json'), 'w'),
          ensure_ascii=False, indent=1)
print('saved', len(out))
