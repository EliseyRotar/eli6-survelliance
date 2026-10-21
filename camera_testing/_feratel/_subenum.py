"""DNS brute-force subdomain enum for feratel domains + sts host sweep."""
import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor

BASES = [
    "feratel.com", "feratel.co.at", "feratel.at", "feratel.de",
    "feratel.tv", "enzazi.com", "feratel.net",
]
WORDS = """
admin api app apps auth beta blog cdc cdn cms dcs dev docs extranet
feeds ftp git grafana hlsv2 id image img images ingest intranet jira
live login mail maps media mms mobile monitor ns1 ns2
old partners portal preview proxy push rtmp shop shop2
soa ssl sso static stats stats2 stream streams sts test tracking
video videos vod voip vpn web2 webtv weather wetter wiki www wtvthmb
backend b2b booking cam cams camera cameras cluster conf config
db demo download dyna dynimg ebus edge europe ext files front
go ice img2 internal kamera katalog lb legacy lists loc map
new noc oauth open origin out p2p perf phone photos pi play player
prod pub qa queue raw redis relay report rest robot rs sandbox
sec secure send server srv staging static2 storage swap sync
test tests time tmp tool trace track ts txt uni up update upload
v1 v2 v3 v4 v5 w3 webcams webshop wms ws wss
""".split()


def resolve(name):
    try:
        infos = socket.getaddrinfo(name, None)
        ips = sorted({i[4][0] for i in infos})
        return name, ips
    except OSError:
        return name, None


def main():
    targets = [f"{w}.{b}" for b in BASES for w in WORDS]
    found = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=64) as ex:
        for name, ips in ex.map(resolve, targets):
            if ips:
                found[name] = ips
    # sts001-250 (streaming LB pool on feratel.co.at)
    sts = [f"sts{i:03d}.feratel.co.at" for i in range(1, 251)]
    with ThreadPoolExecutor(max_workers=64) as ex:
        for name, ips in ex.map(resolve, sts):
            if ips:
                found[name] = ips
    out = {
        "found": found,
        "elapsed_s": round(time.time() - t0, 1),
        "tried": len(targets) + len(sts),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open("camera_testing/_feratel/subenum.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"tried {out['tried']} names, found {len(found)} in {out['elapsed_s']}s")
    for k in sorted(found):
        print(f"  {k}  {','.join(found[k])}")


if __name__ == "__main__":
    main()
