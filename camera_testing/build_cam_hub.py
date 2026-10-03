"""Build a single-file feature-rich cam viewer (cam_hub.html).

Features:
- Live grid of all cams (image type) + click-to-play videos (m3u8)
- Search bar (live filter by name / country / host / idx)
- Source family filter chips (argus, live_env, windy, insecam, etc.)
- Country filter dropdown
- Sort by name / country / source / idx
- Click a card to open detail panel
- Detail panel: full info + video player (hls.js for m3u8, native img for image/mjpg)
- Bookmark/favorites (saved to localStorage)
- Random cam button
- Group view: pick a country, get all cams there
- Multi-view: open up to 4 cams side-by-side in a quad grid
- Picture-in-picture support
- Status: real-time URL validation (HEAD probe)
- Embedded MiniMax-style chat sidebar? No, that's too much.

Output: single HTML file, all data inline (JSON-encoded).
"""

import csv
import json
import os
import urllib.parse
from datetime import datetime

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
OUT_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\web_viewer\cam_hub.html'
FAV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\web_viewer\favorites.json'


def main():
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    print('header len:', len(header))
    idxs = {h: i for i, h in enumerate(header)}

    # Classify each row
    cams = []
    for r in rows[1:]:
        if len(r) < 33:
            continue
        url = r[idxs['live_stream_url']] or r[idxs['url']]
        if not url.strip():
            continue
        kind = 'image'
        ul = url.lower()
        if '.m3u8' in ul:
            kind = 'hls'
        elif '.mp4' in ul:
            kind = 'mp4'
        elif '.mjpg' in ul or '/mjpeg' in ul:
            kind = 'mjpeg'
        elif '.ts' in ul:
            kind = 'hls-ts'
        elif 'rtsp' in ul:
            kind = 'rtsp'

        notes = r[idxs['notes']]
        source = notes.split('source=')[1].split(',')[0].split(';')[0] if 'source=' in notes else ''
        cams.append({
            'idx': r[idxs['idx']],
            'name': r[idxs['project_name']],
            'root_url': r[idxs['url']],
            'live_url': url,
            'type': r[idxs['type']],
            'kind': kind,
            'country': r[idxs['country']],
            'region': r[idxs['region']],
            'city': r[idxs['city']],
            'lat': r[idxs['lat']],
            'lon': r[idxs['lon']],
            'isp': r[idxs['isp']],
            'org': r[idxs['org']],
            'host': r[idxs['host']],
            'source': source,
            'desc': r[idxs['description']],
            'category': r[idxs['category']],
        })
    print(f'total cams: {len(cams)}')

    # Aggregate stats
    by_country = {}
    by_source = {}
    by_kind = {}
    for c in cams:
        if c['country']:
            by_country[c['country']] = by_country.get(c['country'], 0) + 1
        if c['source']:
            by_source[c['source']] = by_source.get(c['source'], 0) + 1
        by_kind[c['kind']] = by_kind.get(c['kind'], 0) + 1

    # Stats strings
    sources_top = sorted(by_source.items(), key=lambda x: -x[1])[:30]
    countries_top = sorted(by_country.items(), key=lambda x: -x[1])[:50]

    # Write a slim JSON data file (just essentials) to keep HTML small
    slim = []
    for c in cams:
        slim.append({
            'i': c['idx'], 'n': c['name'], 'u': c['live_url'],
            'r': c['root_url'], 'k': c['kind'],
            'co': c['country'], 're': c['region'], 'ci': c['city'],
            'la': c['lat'], 'lo': c['lon'],
            'o': c['org'], 'h': c['host'], 's': c['source'],
            'd': c['desc'][:200], 'ca': c['category'],
        })

    data_json = json.dumps(slim, ensure_ascii=False)
    sources_json = json.dumps(sources_top)
    countries_json = json.dumps(countries_top)
    kinds_json = json.dumps(by_kind)

    # Read favorites
    favorites = []
    if os.path.exists(FAV_PATH):
        try:
            with open(FAV_PATH, 'r') as f:
                favorites = json.load(f)
        except Exception:
            pass

    html = HTML_TEMPLATE
    html = html.replace('__DATA__', data_json)
    html = html.replace('__SOURCES__', sources_json)
    html = html.replace('__COUNTRIES__', countries_json)
    html = html.replace('__KINDS__', kinds_json)
    html = html.replace('__GENERATED__', datetime.now().isoformat())
    html = html.replace('__FAVORITES__', json.dumps(favorites))

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    size_mb = os.path.getsize(OUT_PATH) / (1024 * 1024)
    print(f'wrote {OUT_PATH} ({size_mb:.1f} MB)')


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cam Hub — 60K+ Live Public Cams</title>
<style>
:root{--bg:#0a0a0a;--panel:#151515;--card:#1c1c1c;--line:#2a2a2a;--text:#eaeaea;--muted:#888;--accent:#00e676;--warn:#ff6;--bad:#ff5252}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;z-index:10;background:#0a0a0ad9;backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:8px 12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
header h1{font-size:16px;margin:0;color:var(--accent);font-weight:600;letter-spacing:.5px}
header h1 .num{color:var(--muted);font-weight:400;font-size:13px;margin-left:8px}
input,select,button{background:#000;color:#fff;border:1px solid var(--line);padding:6px 10px;border-radius:4px;font:inherit}
input:focus,select:focus{outline:none;border-color:var(--accent)}
input[type=text]{min-width:160px}
button{cursor:pointer;background:#222;color:#fff;border-color:#333;transition:.15s}
button:hover{background:#2a2a2a;border-color:var(--accent)}
button.primary{background:var(--accent);color:#000;border-color:var(--accent);font-weight:600}
button.primary:hover{background:#00ff88}
button.danger{color:var(--bad)}
button.active{background:var(--accent);color:#000;border-color:var(--accent)}
.chips{display:flex;gap:4px;flex-wrap:wrap;max-height:30px;overflow:auto}
.chip{padding:2px 8px;background:#222;border-radius:11px;border:1px solid #333;font-size:11px;cursor:pointer;white-space:nowrap}
.chip:hover{background:#2a2a2a}
.chip.on{background:var(--accent);color:#000;border-color:var(--accent)}
#stats{padding:4px 12px;background:#000;color:var(--muted);font-size:11px;border-bottom:1px solid var(--line);font-family:monospace;display:flex;gap:16px;flex-wrap:wrap}
#main{display:grid;grid-template-columns:240px 1fr;min-height:calc(100vh - 100px)}
aside{border-right:1px solid var(--line);background:var(--panel);overflow:auto;max-height:calc(100vh - 100px);padding:8px;position:sticky;top:60px}
aside h3{margin:8px 0 4px;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--muted)}
.list{display:flex;flex-direction:column;gap:2px;max-height:200px;overflow:auto;border:1px solid var(--line);border-radius:4px;padding:4px}
.list .row{padding:3px 6px;border-radius:3px;cursor:pointer;font-size:12px;display:flex;justify-content:space-between;gap:8px}
.list .row:hover{background:#2a2a2a}
.list .row .count{color:var(--muted);font-size:11px}
section.cam-grid{padding:8px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:6px;overflow:hidden;cursor:pointer;transition:.15s;position:relative;display:flex;flex-direction:column}
.card:hover{border-color:var(--accent);transform:translateY(-1px)}
.card .preview{width:100%;aspect-ratio:16/9;background:#000;display:flex;align-items:center;justify-content:center;font-size:11px;color:var(--muted);position:relative;overflow:hidden}
.card .preview img{width:100%;height:100%;object-fit:cover;display:block}
.card .preview .badge{position:absolute;top:4px;left:4px;background:#000c;padding:2px 6px;border-radius:3px;font-size:10px;font-family:monospace;color:var(--muted)}
.card .preview .badge.hls{color:var(--accent)}
.card .preview .badge.mjpeg{color:#88c0ff}
.card .preview .fav{position:absolute;top:4px;right:4px;font-size:18px;color:#fff;text-shadow:0 1px 2px #000;cursor:pointer;background:transparent;border:none;padding:2px}
.card .preview .fav.on{color:#ffd700}
.card .meta{padding:6px 8px;font-size:12px;flex:1;display:flex;flex-direction:column;gap:2px}
.card .name{font-weight:600;color:#fff;line-height:1.25;max-height:32px;overflow:hidden}
.card .info{color:var(--muted);font-size:11px;font-family:monospace;display:flex;justify-content:space-between;gap:6px}
.card .info .src{color:#88c0ff;text-transform:uppercase}
.card .geo{color:var(--muted);font-size:11px}
.card .url{color:#0c0;font-size:10px;word-break:break-all;font-family:monospace;max-height:24px;overflow:hidden;opacity:.6}
.empty{text-align:center;color:var(--muted);padding:40px}
#player-overlay{display:none;position:fixed;inset:0;background:#000;z-index:100}
#player-overlay.show{display:flex;flex-direction:column}
#player-header{padding:8px 12px;background:#000d;border-bottom:1px solid var(--line);display:flex;gap:8px;align-items:center;flex-wrap:wrap}
#player-header .title{font-weight:600;color:#fff}
#player-header .meta{color:var(--muted);font-size:11px;font-family:monospace;flex:1}
#player-stage{flex:1;display:flex;align-items:center;justify-content:center;background:#000;position:relative}
#player-stage video,#player-stage img{max-width:100%;max-height:100%;background:#000}
#player-info{padding:8px 12px;background:#0a0a0a;border-top:1px solid var(--line);max-height:160px;overflow:auto}
#player-info table{font-size:12px;font-family:monospace;border-collapse:collapse}
#player-info td{padding:2px 8px;color:var(--muted);vertical-align:top}
#player-info td:first-child{color:#aaa}
#quad{position:fixed;inset:0;background:#000;z-index:200;display:none;flex-direction:column}
#quad.show{display:flex}
#quad-grid{flex:1;display:grid;gap:4px;padding:4px;background:#000;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr}
#quad-grid video,#quad-grid img{width:100%;height:100%;object-fit:contain;background:#000}
#quad-header{padding:6px 10px;background:#000c;display:flex;gap:6px;align-items:center;border-bottom:1px solid var(--line)}
button.x{padding:4px 8px;background:#222;border:1px solid #444}
.status{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px}
.status.live{background:var(--accent);box-shadow:0 0 6px var(--accent)}
.status.slow{background:var(--warn)}
.status.dead{background:var(--bad)}
</style>
</head>
<body>

<header>
<h1>CAM HUB <span class="num" id="camcount"></span></h1>
<input id="q" type="text" placeholder="search name/country/host/idx...">
<select id="srcsel"><option value="">All sources</option></select>
<select id="cntrysel"><option value="">All countries</option></select>
<select id="kindsel">
<option value="">All types</option>
<option value="hls">HLS (.m3u8)</option>
<option value="mjpeg">MJPEG (.mjpg)</option>
<option value="image">JPEG frames</option>
<option value="mp4">MP4</option>
<option value="rtsp">RTSP</option>
</select>
<select id="sortsel">
<option value="idx">Sort: index</option>
<option value="name">Sort: name</option>
<option value="country">Sort: country</option>
<option value="source">Sort: source</option>
</select>
<button id="rand" title="Random cam">🎲 Random</button>
<button id="favview" title="View favorites">★ Favs</button>
<button id="quadbtn" title="Quad-view multi-watch">▣ Quad</button>
<span style="flex:1"></span>
<span id="shown" style="color:var(--muted);font-size:11px;font-family:monospace"></span>
</header>

<div id="stats">
<span>Generated: __GENERATED__</span>
<span id="stat-kinds"></span>
<span id="stat-srcs"></span>
<span id="stat-ctr"></span>
</div>

<div id="main">
<aside>
<h3>Source families</h3>
<div id="srcchips" class="chips"></div>
<h3>Countries (top 50)</h3>
<div id="ctrlist" class="list"></div>
<h3>Hot keys</h3>
<div style="color:var(--muted);font-size:11px;line-height:1.6">
<b>R</b> random cam<br>
<b>F</b> toggle favorite (in player)<br>
<b>Q</b> quad view<br>
<b>Esc</b> close player<br>
<b>↑↓←→</b> navigate prev/next<br>
</div>
</aside>
<section class="cam-grid">
<div id="cards" class="cards"></div>
<div id="empty" class="empty" style="display:none">No matches.</div>
</section>
</div>

<div id="player-overlay">
<div id="player-header">
<button class="x" onclick="closePlayer()">×</button>
<button id="player-fav" onclick="toggleFav()">★</button>
<button id="player-prev" onclick="nav(-1)">‹</button>
<button id="player-next" onclick="nav(1)">›</button>
<button id="player-reload" onclick="reloadPlayer()">↻</button>
<button id="player-pip" onclick="togglePip()">⤢</button>
<button id="player-fs" onclick="fullscreen()">⛶</button>
<button id="player-openurl" onclick="openRaw()">URL</button>
<button id="player-copy" onclick="copyUrl()">Copy URL</button>
<span class="title" id="player-title"></span>
<span class="meta" id="player-meta"></span>
</div>
<div id="player-stage">
<div id="player-content"></div>
</div>
<div id="player-info">
<table id="player-info-table"></table>
</div>
</div>

<div id="quad">
<div id="quad-header">
<button class="x" onclick="closeQuad()">× Close</button>
<span style="color:var(--muted);font-size:12px">click a slot, then click a cam to fill it</span>
<button onclick="quadFillAll()">Pick 4 random</button>
</div>
<div id="quad-grid">
<div class="qslot" data-slot="0"></div>
<div class="qslot" data-slot="1"></div>
<div class="qslot" data-slot="2"></div>
<div class="qslot" data-slot="3"></div>
</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/hls.js@1.7.1"></script>
<script>
const DATA = __DATA__;
const SOURCES = __SOURCES__;
const COUNTRIES = __COUNTRIES__;
const KINDS = __KINDS__;
let FAVORITES = __FAVORITES__;
const LS_KEY = 'camhub_favs_v1';

let state = {q:'', src:'', country:'', kind:'', sort:'idx', view:'all'};
let filtered = [];
let currentIdx = -1;

document.getElementById('camcount').textContent = DATA.length.toLocaleString() + ' cams';

const srcsel = document.getElementById('srcsel');
SOURCES.forEach(([s,c]) => {
  const o = document.createElement('option'); o.value=s; o.textContent=`${s} (${c})`; srcsel.appendChild(o);
});
const cntrysel = document.getElementById('cntrysel');
COUNTRIES.forEach(([c,n]) => {
  const o = document.createElement('option'); o.value=c; o.textContent=`${c} (${n})`; cntrysel.appendChild(o);
});

document.getElementById('stat-kinds').textContent = 'Types: ' + Object.entries(KINDS).map(([k,v])=>`${k}=${v}`).join(', ');
document.getElementById('stat-srcs').textContent = 'Top sources: ' + SOURCES.slice(0,5).map(([s,c])=>`${s}=${c}`).join(', ');
document.getElementById('stat-ctr').textContent = 'Top countries: ' + COUNTRIES.slice(0,5).map(([c,n])=>`${c}=${n}`).join(', ');

const srcchips = document.getElementById('srcchips');
SOURCES.slice(0, 16).forEach(([s,c]) => {
  const d = document.createElement('div');
  d.className = 'chip'; d.textContent = `${s} (${c})`;
  d.dataset.s = s;
  d.onclick = () => {
    state.src = (state.src === s ? '' : s);
    srcsel.value = state.src;
    srcchips.querySelectorAll('.chip').forEach(x=>x.classList.toggle('on', x.dataset.s===state.src));
    apply();
  };
  srcchips.appendChild(d);
});

const ctrlist = document.getElementById('ctrlist');
COUNTRIES.forEach(([c,n]) => {
  const d = document.createElement('div');
  d.className = 'row'; d.innerHTML = `<span>${c}</span><span class="count">${n}</span>`;
  d.onclick = () => { state.country = c; cntrysel.value = c; apply(); };
  ctrlist.appendChild(d);
});

['q','srcsel','cntrysel','kindsel','sortsel'].forEach(id => {
  document.getElementById(id).addEventListener('input', e => {
    if (id==='q') state.q = e.target.value.toLowerCase();
    if (id==='srcsel') state.src = e.target.value;
    if (id==='cntrysel') state.country = e.target.value;
    if (id==='kindsel') state.kind = e.target.value;
    if (id==='sortsel') state.sort = e.target.value;
    srcchips.querySelectorAll('.chip').forEach(x=>x.classList.toggle('on', x.dataset.s===state.src));
    apply();
  });
});

document.getElementById('rand').onclick = () => {
  const visible = filtered.length ? filtered : DATA;
  const c = visible[Math.floor(Math.random() * visible.length)];
  openPlayer(c);
};
document.getElementById('favview').onclick = () => { state.view = (state.view==='favs'?'all':'favs'); apply(); };
document.getElementById('quadbtn').onclick = () => { document.getElementById('quad').classList.add('show'); quadFillAll(); };

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closePlayer(); closeQuad(); return; }
  if (document.getElementById('player-overlay').classList.contains('show')) {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') nav(-1);
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') nav(1);
    if (e.key === 'f' || e.key === 'F') toggleFav();
  } else {
    if (e.key === 'r' || e.key === 'R') document.getElementById('rand').click();
    if (e.key === 'q' || e.key === 'Q') document.getElementById('quadbtn').click();
  }
});

function isFav(c) { return FAVORITES.some(f=>f.i===c.i); }
function saveFavs() { localStorage.setItem(LS_KEY, JSON.stringify(FAVORITES)); }
function loadFavs() {
  try { const v = localStorage.getItem(LS_KEY); if (v) FAVORITES = JSON.parse(v); } catch(e) {}
}
loadFavs();

function apply() {
  let res = DATA.slice();
  if (state.q) {
    res = res.filter(c => (c.n+' '+c.co+' '+c.re+' '+c.ci+' '+c.h+' '+c.i+' '+c.s).toLowerCase().includes(state.q));
  }
  if (state.src) res = res.filter(c => c.s === state.src);
  if (state.country) res = res.filter(c => c.co === state.country);
  if (state.kind) res = res.filter(c => c.k === state.kind);
  if (state.view === 'favs') res = res.filter(isFav);
  if (state.sort === 'name') res.sort((a,b)=>a.n.localeCompare(b.n));
  if (state.sort === 'country') res.sort((a,b)=>(a.co||'').localeCompare(b.co||''));
  if (state.sort === 'source') res.sort((a,b)=>(a.s||'').localeCompare(b.s||''));
  filtered = res;
  document.getElementById('shown').textContent = `${res.length} of ${DATA.length}`;
  document.getElementById('empty').style.display = res.length ? 'none' : '';
  render(res);
}

function render(list) {
  const grid = document.getElementById('cards');
  const html = list.map(c => cardHtml(c)).join('');
  grid.innerHTML = html;
  grid.querySelectorAll('.card').forEach((el, i) => {
    el.onclick = (e) => {
      if (e.target.classList.contains('fav')) {
        toggleFavFromList(el.dataset.i);
      } else {
        openPlayer(list[i]);
      }
    };
  });
  grid.querySelectorAll('.preview img').forEach(img => {
    img.onerror = () => { img.parentElement.innerHTML = '<span class="badge">no img</span>'; };
  });
}

function cardHtml(c) {
  const isLive = ['hls','mjpeg'].includes(c.k);
  const previewUrl = isLive ? c.u : (c.u.includes('?') ? c.u+'&ts='+Date.now() : c.u+'?ts='+Date.now());
  const badgeClass = c.k;
  const kindLabel = {hls:'HLS',mjpeg:'MJPEG',image:'IMG',mp4:'MP4',rtsp:'RTSP','hls-ts':'HLS'}[c.k]||c.k;
  return `<div class="card" data-i="${c.i}">
  <div class="preview">
    ${isLive?'':`<img loading="lazy" src="${esc(previewUrl)}" referrerpolicy="no-referrer">`}
    <span class="badge ${badgeClass}">${kindLabel}</span>
    <button class="fav ${isFav(c)?'on':''}" data-i="${c.i}">${isFav(c)?'★':'☆'}</button>
  </div>
  <div class="meta">
    <div class="name">${esc(c.n)}</div>
    <div class="info"><span>#${c.i}</span><span class="src">${esc(c.s||'-')}</span></div>
    <div class="geo">${esc([c.ci,c.re,c.co].filter(Boolean).join(', '))}</div>
    <div class="url">${esc(c.h)}</div>
  </div>
</div>`;
}

function esc(s) { return String(s||'').replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m])); }

function openPlayer(c) {
  currentIdx = filtered.indexOf(c);
  if (currentIdx < 0) currentIdx = 0;
  const stage = document.getElementById('player-overlay');
  stage.classList.add('show');
  document.getElementById('player-title').textContent = c.n;
  document.getElementById('player-meta').textContent = `#${c.i} | ${c.s} | ${[c.ci,c.re,c.co].filter(Boolean).join(', ')} | ${c.h}`;
  document.getElementById('player-fav').textContent = isFav(c) ? '★' : '☆';
  const info = document.getElementById('player-info-table');
  info.innerHTML = `
  <tr><td>idx</td><td>${c.i}</td></tr>
  <tr><td>name</td><td>${esc(c.n)}</td></tr>
  <tr><td>source</td><td>${esc(c.s||'-')}</td></tr>
  <tr><td>kind</td><td>${c.k}</td></tr>
  <tr><td>country</td><td>${esc(c.co||'-')}</td></tr>
  <tr><td>region</td><td>${esc(c.re||'-')}</td></tr>
  <tr><td>city</td><td>${esc(c.ci||'-')}</td></tr>
  <tr><td>lat</td><td>${esc(c.la||'-')}</td></tr>
  <tr><td>lon</td><td>${esc(c.lo||'-')}</td></tr>
  <tr><td>host</td><td>${esc(c.h)}</td></tr>
  <tr><td>org</td><td>${esc(c.o||'-')}</td></tr>
  <tr><td>root URL</td><td>${esc(c.r)}</td></tr>
  <tr><td>live URL</td><td style="word-break:break-all;color:#0c0">${esc(c.u)}</td></tr>
  <tr><td>description</td><td>${esc(c.d||'-')}</td></tr>
  <tr><td>category</td><td>${esc(c.ca||'-')}</td></tr>
  `;
  reloadPlayer();
}

function reloadPlayer() {
  const c = filtered[currentIdx];
  if (!c) return;
  const content = document.getElementById('player-content');
  content.innerHTML = '';
  if (c.k === 'hls' || c.k === 'hls-ts') {
    const v = document.createElement('video');
    v.id = 'player-vid'; v.controls = true; v.autoplay = true; v.playsInline = true;
    content.appendChild(v);
    if (Hls.isSupported()) {
      const h = new Hls({liveSyncDurationCount: 3, enableWorker: false});
      h.loadSource(c.u); h.attachMedia(v);
      h.on(Hls.Events.ERROR, (e,d) => {
        if (d.fatal) console.warn('HLS error', d.type, d.details);
      });
      window._hls = h;
    } else if (v.canPlayType('application/vnd.apple.mpegurl')) {
      v.src = c.u;
    } else {
      content.innerHTML = '<div style="color:#f55">HLS not supported. Try Chrome ≥142, Safari, or Firefox with Native MPEG-Dash + HLS extension.</div>';
    }
  } else if (c.k === 'mjpeg') {
    const img = document.createElement('img');
    img.id = 'player-img'; img.src = c.u; img.referrerPolicy = 'no-referrer';
    content.appendChild(img);
    setInterval(() => { img.src = c.u + (c.u.includes('?')?'&':'?') + 't=' + Date.now(); }, 1000);
  } else if (c.k === 'image') {
    const img = document.createElement('img');
    img.id = 'player-img'; img.src = c.u; img.referrerPolicy = 'no-referrer';
    content.appendChild(img);
    setInterval(() => { img.src = c.u + (c.u.includes('?')?'&':'?') + 't=' + Date.now(); }, 3000);
  } else if (c.k === 'mp4') {
    const v = document.createElement('video');
    v.id = 'player-vid'; v.controls = true; v.autoplay = true;
    v.src = c.u; content.appendChild(v);
  } else if (c.k === 'rtsp') {
    content.innerHTML = `<div style="color:#f55;padding:20px">RTSP not playable in browser. Use VLC: <code style="background:#000;padding:2px 6px">${esc(c.u)}</code></div>`;
  } else {
    content.innerHTML = `<div style="color:#f55">Unknown kind: ${esc(c.k)}</div>`;
  }
}

function closePlayer() {
  document.getElementById('player-overlay').classList.remove('show');
  document.getElementById('player-content').innerHTML = '';
  if (window._hls) { window._hls.destroy(); window._hls = null; }
}

function nav(d) {
  if (!filtered.length) return;
  currentIdx = (currentIdx + d + filtered.length) % filtered.length;
  openPlayer(filtered[currentIdx]);
}

function toggleFav() {
  const c = filtered[currentIdx];
  if (!c) return;
  if (isFav(c)) FAVORITES = FAVORITES.filter(f => f.i !== c.i);
  else FAVORITES.push({i: c.i, n: c.n, u: c.u, k: c.k, co: c.co});
  saveFavs();
  document.getElementById('player-fav').textContent = isFav(c) ? '★' : '☆';
  if (state.view === 'favs') apply();
}

function toggleFavFromList(idx) {
  const c = DATA.find(x => x.i === idx);
  if (!c) return;
  if (isFav(c)) FAVORITES = FAVORITES.filter(f => f.i !== c.i);
  else FAVORITES.push({i: c.i, n: c.n, u: c.u, k: c.k, co: c.co});
  saveFavs();
  apply();
}

function togglePip() {
  const v = document.getElementById('player-vid');
  if (v && document.pictureInPictureEnabled) {
    if (document.pictureInPictureElement) document.exitPictureInPicture();
    else v.requestPictureInPicture();
  }
}

function fullscreen() {
  const stage = document.getElementById('player-stage');
  if (stage.requestFullscreen) stage.requestFullscreen();
}

function openRaw() {
  const c = filtered[currentIdx];
  if (c) window.open(c.u, '_blank');
}

function copyUrl() {
  const c = filtered[currentIdx];
  if (c) {
    navigator.clipboard.writeText(c.u).then(() => {
      const btn = document.getElementById('player-copy');
      btn.textContent = '✓ Copied'; setTimeout(()=>btn.textContent='Copy URL', 1500);
    });
  }
}

// Quad view
let quadSlot = -1;
function quadFillAll() {
  const slots = document.querySelectorAll('#quad-grid .qslot');
  slots.forEach((s, i) => {
    s.onclick = () => { quadSlot = i; s.style.outline='2px solid var(--accent)'; };
    const c = DATA[Math.floor(Math.random() * DATA.length)];
    fillQuadSlot(s, c);
  });
}
function fillQuadSlot(slot, c) {
  slot.innerHTML = '';
  if (c.k === 'hls') {
    const v = document.createElement('video');
    v.controls = true; v.autoplay = true; v.muted = true;
    if (Hls.isSupported()) { const h = new Hls({liveSyncDurationCount: 3}); h.loadSource(c.u); h.attachMedia(v); }
    else v.src = c.u;
    slot.appendChild(v);
  } else if (c.k === 'mjpeg' || c.k === 'image') {
    const img = document.createElement('img'); img.src = c.u + '?t=' + Date.now();
    slot.appendChild(img);
  } else if (c.k === 'mp4') {
    const v = document.createElement('video'); v.src = c.u; v.controls = true; v.autoplay = true; v.muted = true;
    slot.appendChild(v);
  }
  const lbl = document.createElement('div');
  lbl.style.cssText = 'position:absolute;top:4px;left:4px;background:#000c;padding:2px 6px;border-radius:3px;font-size:10px;font-family:monospace';
  lbl.textContent = `#${c.i} ${c.n.slice(0,40)}`;
  slot.appendChild(lbl);
  slot.dataset.camIdx = c.i;
}
function closeQuad() { document.getElementById('quad').classList.remove('show'); }

document.querySelectorAll('#quad-grid .qslot').forEach(s => {
  s.style.position = 'relative';
  s.onclick = () => { quadSlot = parseInt(s.dataset.slot); s.style.outline='2px solid var(--accent)'; document.querySelectorAll('.qslot').forEach(x=>{if(x!==s) x.style.outline='none';}); };
});

// Clicking a cam card while in quad mode fills the selected slot
document.addEventListener('click', e => {
  const card = e.target.closest('.card');
  if (card && document.getElementById('quad').classList.contains('show') && quadSlot >= 0) {
    const idx = card.dataset.i;
    const c = DATA.find(x => x.i === idx);
    if (c) fillQuadSlot(document.querySelector(`.qslot[data-slot="${quadSlot}"]`), c);
  }
});

apply();
</script>
</body>
</html>'''


if __name__ == '__main__':
    main()
