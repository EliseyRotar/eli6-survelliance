Port scan results for 75.119.202.195 (rojisan.com DreamHost shared server)

Aug 21 2026, ~340 common ports checked via Python concurrent connect_scan

## OPEN PORTS

| Port | Service | Banner | Notes |
|---|---|---|---|
| 21 | FTP | `220 DreamHost FTP Server` | Standard DreamHost FTP (anonymous not allowed; needs account) |
| 22 | SSH | `SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.18` | Ubuntu OpenSSH (server-wide, not specific to rojisan) |
| 80 | HTTP | Apache (DreamHost) | Apache/2.4.x (Ubuntu), redirects http → https |
| 443 | HTTPS | Apache (DreamHost) | SSL/TLS works, valid cert for rojisan.com |
| 587 | SMTP | (greeted but EHLO timed out from probe) | DreamHost mail submission port |

## CLOSED / NO RESPONSE
All other ports (21-30000) returned timeout — including 25, 3306, 5432, 8080, 8443, 8888, 27017, 50000, etc.

## SERVER INFO
- **Reverse DNS:** apache2-moon.pdx1-shared-a1-43.dreamhost.com
- **Datacenter:** DreamHost shared hosting (Portland PDX1, Oregon)
- **Type:** Multi-tenant shared — port 21/22/587 are server-wide services for all DreamHost customers on this box
- **NOT** dedicated to rojisan.com alone

## SIBLING SITES ON SAME IP
All confirmed hosted on same IP via Host header injection (HTTP 200):
- areyoumyhero.com
- stgroup6.net
- heroregistry.org
- brexton.org (301 redirect)
- cafeshops.com

All linked from `t_main.html` and `b_main.shtml` of rojisan.com (personal pages of the same owner).

## CONCLUSION
- **Only webcams/web services exposed:** port 80 (web) + 443 (web SSL)
- **Mail** port 587 (submission, server-wide)
- **No admin ports, no databases, no SSH/FTP/RDP specific to the cam or site** — these are server-wide services

## Files
- `rojisan_wayback_cdx.json` — full Wayback CDX for rojisan.com root
- `rojisan_wb_root.json` — Wayback for root + a few pages