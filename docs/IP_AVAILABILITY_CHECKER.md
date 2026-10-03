# IP Availability Checker

A self-contained Python CLI that quickly answers the question "is this IP / host /
URL actually reachable?" — without depending on any one probe technique.

> **Why another tool?** ICMP ping is often blocked or rate-limited on the public
> internet (and useless for camera endpoints that don't reply to ICMP). The script
> tries each probe in turn and stops at the first success, so you get an honest
> "yes / no" plus the evidence.

---

## Files

| Path | Purpose |
|------|---------|
| `src/check_ip_availability.py` | The checker script (stdlib-only, no `pip install`). |
| `camera_testing/ip_probe_targets.txt` | Sample target list used in the run below. |
| `camera_testing/ip_probe_results.json` | Machine-readable output from the run below. |

---

## How it works

For each target the script runs probes in this order and reports the first one
that responds:

1. **ICMP ping** (`ping -n 1 -w 2000` on Windows, `ping -c 1 -W 2` elsewhere).
2. **TCP handshake** against the target's port (if specified) plus a curated set
   of common camera/web ports: `80, 443, 554 (RTSP), 8000, 8080, 8443`.
3. **HTTP HEAD** (only when the input is a URL or `--http` is passed).

The TCP probes for a single target run in parallel, so the per-target worst
case is roughly `ping_timeout + tcp_timeout`, not their sum.

Input parsing accepts:

- bare IPs / hostnames: `8.8.8.8`, `example.com`
- `host:port` form: `192.168.1.10:8080`
- full URLs: `http://192.168.1.100/web/tmpfs/snap.jpg`

Sources: positional args, `-f <file>` (one target per line), and stdin (handy
when piping from another tool).

---

## Usage

```bash
# Single hosts / IPs
python src/check_ip_availability.py 8.8.8.8 1.1.1.1

# With explicit port
python src/check_ip_availability.py 192.168.1.10:8080

# URLs (HTTP probe is automatic when the input has a scheme)
python src/check_ip_availability.py https://github.com

# From a file
python src/check_ip_availability.py -f hosts.txt

# Force an HTTP probe for every entry (even bare IPs → http://<ip>)
python src/check_ip_availability.py --http -f hosts.txt

# Skip ICMP (useful when ping is blocked)
python src/check_ip_availability.py --no-ping 8.8.8.8

# JSON output (good for piping into jq / dashboards)
python src/check_ip_availability.py --json -f hosts.txt

# CI / cron mode — exit code 1 if any host is down
python src/check_ip_availability.py -q -f production_cameras.txt
```

### CLI reference

| Flag | Meaning |
|------|---------|
| `target ...` | One or more IPs / hosts / URLs. |
| `-f, --file FILE` | Read targets from a text file, one per line. |
| `--no-ping` | Skip the ICMP probe (skip ahead to TCP/HTTP). |
| `--http` | Also try an HTTP HEAD against every entry. |
| `-w, --workers N` | Concurrent workers (default `20`). |
| `-j, --json` | Emit JSON instead of a text table. |
| `-q, --quiet` | Only print failing targets. |

Exit codes: `0` if every target was reachable, `1` otherwise.

---

## Sample run

Targets list (`camera_testing/ip_probe_targets.txt`):

```
8.8.8.8
1.1.1.1
127.0.0.1
192.168.1.10
192.168.1.10:8080
http://192.168.1.100/web/tmpfs/snap.jpg
example.com
github.com
http://10.255.255.1
http://127.0.0.1:1
```

Command:

```bash
python src/check_ip_availability.py -f camera_testing/ip_probe_targets.txt --http
```

Console output:

```
[OK ] 8.8.8.8                                       probe=ping   141.0ms
[OK ] 1.1.1.1                                       probe=ping   156.0ms
[OK ] 127.0.0.1                                     probe=ping    15.0ms
[OK ] 192.168.1.10                                  probe=http   437.0ms [HTTP 404]
[OK ] 192.168.1.10:8080                             probe=http   437.0ms [HTTP 404]
[OK ] http://192.168.1.100/web/tmpfs/snap.jpg       probe=ping   187.0ms
[OK ] example.com                                   probe=http   297.0ms [HTTP 200]
[OK ] github.com                                    probe=http   782.0ms [HTTP 200]
[FAIL] http://10.255.255.1                           probe=-            - (no reply)
[OK ] http://127.0.0.1:1                            probe=ping    15.0ms

9/10 reachable
```

### Reading the result

| Column | Meaning |
|--------|---------|
| `OK / FAIL` | Final verdict for that target. |
| `target` | The original input (or `host:port` when the TCP probe won). |
| `probe` | Which probe produced the verdict: `ping`, `tcp`, `http`, or `-`. |
| `latency` | Round-trip time of the winning probe, in milliseconds. |
| `[HTTP nnn]` | HTTP status code when the HTTP probe was used. |
| `(no reply)` | Short error string from the last failed probe. |

### Key observations from this run

- **Public DNS / well-known IPs** (`8.8.8.8`, `1.1.1.1`) reply to ICMP — ping is
  the fastest signal here (~140 ms).
- **Local network devices** (`192.168.1.10`, `192.168.1.10:8080`) don't reply
  to ICMP but do respond to HTTP. The `[HTTP 404]` proves the host is up — the
  URL just doesn't point at anything; in a camera scenario this is typically
  the right path on a different port (e.g. `/axis-cgi/mjpg/video.cgi`).
- **10.255.255.1** is a non-routable RFC-1918 address, so every probe times out
  → `FAIL` as expected.
- **`127.0.0.1:1`** is parsed correctly: the script splits `host:port`, pings
  the loopback, and reports success at 0 ms.

---

## JSON output

The exact JSON for the run above is saved at
`camera_testing/ip_probe_results.json`. Each entry has:

```json
{
  "target": "192.168.1.10:8080",
  "host":   "192.168.1.10",
  "port":   8080,
  "available":   true,
  "probe":       "http",
  "latency_ms":  375.0,
  "error":       null,
  "http_status": 404
}
```

Useful `jq` recipes:

```bash
# Just the failing targets
jq '.[] | select(.available == false) | .target' camera_testing/ip_probe_results.json

# Top 5 slowest reachable hosts
jq '[.[] | select(.available)] | sort_by(-.latency_ms) | .[0:5]' \
    camera_testing/ip_probe_results.json

# Count by probe type
jq 'group_by(.probe) | map({probe: .[0].probe, count: length})' \
    camera_testing/ip_probe_results.json
```

---

## Notes & caveats

- The script **doesn't send credentials**. If you need to test a camera URL
  that requires HTTP Basic Auth, do it from `camera_testing/test_camera_urls.py`
  (which uses `requests` with auth) or extend `http_probe()` in this script.
- **Firewall caveat**: some networks block outbound ICMP, in which case
  `--no-ping` is your friend and TCP/HTTP probes will do all the work.
- The default common ports (`80, 443, 554, 8000, 8080, 8443`) cover most IP
  cameras and web dashboards; if you have a custom port, pass it explicitly:
  `python src/check_ip_availability.py 10.0.0.5:8888`.
- The script is **Windows-aware**: it uses `ping -n`/`-w` on Windows and
  `ping -c`/`-W` elsewhere, and `subprocess` with explicit timeouts so a
  missing `ping` binary won't hang the run.
