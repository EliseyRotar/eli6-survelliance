"""Grab TLS cert CN+SANs from every open-443 host in the sweep, plus
default Host probe on :80 - maps IPs to vhosts/services."""
import json
import os
import re
import socket
import ssl
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_SWEEP = os.path.join(_HERE, "sweep_up_hosts.txt")
HOSTS = []
if os.path.exists(_SWEEP):
    with open(_SWEEP, encoding="utf-8") as f:
        for l in f:
            if l.strip():
                HOSTS.append(l.split("\t")[0])
HOSTS = sorted(set(HOSTS))


def cert_names(ip):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((ip, 443), timeout=6) as s:
            with ctx.wrap_socket(s, server_hostname=ip) as ts:
                cert = ts.getpeercert(binary_form=False) or {}
                # binary_form=False with CERT_NONE yields {} -> use decoded dict
                der = ts.getpeercert(binary_form=True)
        # parse SANs from DER via ssl library
        import cryptography.x509 as cx
        import cryptography.hazmat.primitives.serialization as ser
        c = cx.load_der_x509_certificate(der)
        names = set()
        if c.subject:
            for r in c.subject:
                if r.oid.dotted_string == "2.5.4.3":
                    names.add(r.value)
        try:
            ext = c.extensions.get_extension_for_class(cx.SubjectAlternativeName)
            names.update(ext.value.get_values_for_type(cx.DNSName))
        except Exception:
            pass
        return {"names": sorted(names), "not_after": str(c.not_valid_after)}
    except Exception as e:
        return {"error": type(e).__name__ + ": " + str(e)[:80]}


def probe80(ip):
    req = urllib.request.Request(
        f"http://{ip}/",
        headers={"Host": "feratel.com", "User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            body = r.read(4000).decode("utf-8", "replace")
            title = ""
            m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
            if m:
                title = m.group(1).strip()[:120]
            return {
                "status": r.status,
                "server": r.headers.get("Server", ""),
                "loc": r.headers.get("Location", ""),
                "title": title,
            }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "server": e.headers.get("Server", ""), "loc": e.headers.get("Location", ""), "title": ""}
    except Exception as e:
        return {"error": type(e).__name__}


def main():
    ips = sorted(set(HOSTS))
    out = {}
    t0 = time.time()
    for i, ip in enumerate(ips, 1):
        rec = {}
        r80 = probe80(ip)
        if r80:
            rec["http80"] = r80
        rec["tls443"] = cert_names(ip)
        out[ip] = rec
        print(f"[{i}/{len(ips)}] {ip} {rec.get('tls443', {}).get('names') or rec.get('tls443', {}).get('error', '')} :: {r80.get('title') or r80.get('error', '')}", flush=True)
    fn = os.path.join(_HERE, "vhost_map.json")
    with open(fn, "w", encoding="utf-8") as f:
        json.dump({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "hosts": out}, f, indent=1)
    print(f"done {len(ips)} hosts in {round(time.time()-t0,1)}s -> {fn}")


if __name__ == "__main__":
    main()
