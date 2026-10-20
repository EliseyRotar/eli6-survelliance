# -*- coding: utf-8 -*-
"""Session 48n: generate web_viewer/static/loops/index.html gallery from
docs/loops_manifest.json — one-click verify of all loop videos."""
import json
import os

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
MANIFEST = os.path.join(ROOT, "docs", "loops_manifest.json")
OUT = os.path.join(ROOT, "web_viewer", "static", "loops", "index.html")

data = json.load(open(MANIFEST, encoding="utf-8"))
entries = []
label_map = {
    "official_mp4": ("official-20min", "Official 20-min loop"),
    "wayback_mp4": ("wayback", "Wayback multi-year"),
    "iem_7d_mp4": ("iem-7d", "IEM 7-day archive"),
}
gif_map = {
    "official_mp4": "official_gif",
    "wayback_mp4": "wayback_gif",
    "iem_7d_mp4": "iem_1d_gif",
}
for e in data["loops"]:
    vids = e["videos"]
    for kind, (fk, human) in label_map.items():
        if kind not in vids:
            continue
        item = {
            "id": "%s/%s" % (e["source"], e["camera"]),
            "src": e["source"],
            "cam": e["camera"],
            "filter": fk,
            "human": human,
            "url": "/static/loops/" + vids[kind]["path"],
            "mb": round(vids[kind]["bytes"] / 1e6, 1),
        }
        gk = gif_map[kind]
        if gk in vids:
            item["gif"] = "/static/loops/" + vids[gk]["path"]
        entries.append(item)

t = data["totals"]
n_off = sum(1 for e in entries if e["filter"] == "official-20min")
n_wb = sum(1 for e in entries if e["filter"] == "wayback")
n_iem = sum(1 for e in entries if e["filter"] == "iem-7d")

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ELI6 &rsaquo; Loop Videos Gallery</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
 body{margin:0;background:#0d1117;color:#c9d1d9;font:14px/1.45 system-ui,Segoe UI,sans-serif}
 header{position:sticky;top:0;background:#161b22;border-bottom:1px solid #30363d;padding:10px 16px;z-index:5}
 h1{font-size:16px;margin:0 0 4px;color:#58a6ff}
 .stats{font-size:12px;color:#8b949e}
 .bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
 button{background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;
   padding:4px 10px;font-size:13px;cursor:pointer}
 button.on{background:#1f6feb;border-color:#1f6feb;color:#fff}
 input{background:#0d1117;border:1px solid #30363d;color:#c9d1d9;border-radius:6px;
   padding:5px 9px;font-size:13px;width:220px}
 #wrap{display:flex;gap:14px;padding:14px;align-items:flex-start}
 #playerbox{position:sticky;top:96px;width:min(680px,52vw);flex-shrink:0}
 video{width:100%;background:#000;border:1px solid #30363d;border-radius:8px;aspect-ratio:16/10}
 #now{margin-top:8px;font-size:13px;color:#8b949e;word-break:break-all}
 #now a{color:#58a6ff}
 #list{flex:1;min-width:0}
 .grp{font-size:12px;color:#8b949e;margin:14px 0 6px;text-transform:uppercase;letter-spacing:.5px}
 .it{display:flex;gap:8px;align-items:center;padding:5px 8px;border-radius:6px;cursor:pointer}
 .it:hover{background:#1c2128}
 .it.cur{background:#1f6feb33;outline:1px solid #1f6feb}
 .it .nm{font-weight:600;color:#e6edf3;min-width:150px}
 .it .d{color:#8b949e;font-size:12px}
 .it .m{margin-left:auto;color:#8b949e;font-size:12px}
 .empty{color:#8b949e;padding:20px}
 a.g{color:#58a6ff;font-size:12px}
</style>
</head>
<body>
<header>
 <h1>ELI6 &rsaquo; Loop Videos Gallery</h1>
 <div class="stats">@@T_CAMS@@ cameras with loops &middot; @@T_MB@@ GB &middot;
  official 20-min: @@T_OFF@@ &middot; wayback multi-year: @@T_WB@@ &middot; IEM 7-day: @@T_IEM@@
  &middot; source: docs/loops_manifest.json</div>
 <div class="bar">
  <button class="on" data-f="all">All (@@N_ALL@@)</button>
  <button data-f="official-20min">Official 20-min (@@N_OFF@@)</button>
  <button data-f="wayback">Wayback history (@@N_WB@@)</button>
  <button data-f="iem-7d">IEM 7-day (@@N_IEM@@)</button>
  <input id="q" placeholder="filter: yyc/86, KCCI, wayback...">
 </div>
</header>
<div id="wrap">
 <div id="playerbox">
  <video id="player" controls loop muted playsinline></video>
  <div id="now">Click an item on the right to play. Deep-link works too, e.g.
   <a href="?v=/static/loops/yyc/86/official.mp4">?v=...</a></div>
 </div>
 <div id="list"><div class="empty">Loading...</div></div>
</div>
<script>
const DATA = @@JSON@@;
const player = document.getElementById('player');
const now = document.getElementById('now');
const list = document.getElementById('list');
let filter = 'all', cur = '';
const params = new URLSearchParams(location.search);

function groups(){
  const g = {};
  const q = document.getElementById('q').value.trim().toLowerCase();
  for(const e of DATA){
    if(filter !== 'all' && e.filter !== filter) continue;
    if(q && !(e.id.toLowerCase().includes(q) || e.human.toLowerCase().includes(q))) continue;
    (g[e.id] = g[e.id] || []).push(e);
  }
  return g;
}
function render(){
  const g = groups();
  const keys = Object.keys(g);
  if(!keys.length){ list.innerHTML = '<div class="empty">No matches</div>'; return; }
  let h = '';
  for(const k of keys){
    h += '<div class="grp">' + k + '</div>';
    for(const e of g[k]){
      h += '<div class="it' + (cur === e.url ? ' cur' : '') + '" data-u="' + e.url +
           '" data-h="' + (e.human + ' - ' + e.id + ' (' + e.mb + ' MB)') + '">' +
           '<span class="nm">' + e.cam + '</span>' +
           '<span class="d">' + e.human + '</span>' +
           (e.gif ? '<a class="g" target="_blank" href="' + e.gif + '" onclick="event.stopPropagation()">gif</a>' : '') +
           '<span class="m">' + e.mb + ' MB</span></div>';
    }
  }
  list.innerHTML = h;
}
function play(url, label){
  cur = url;
  player.src = url;
  player.play().catch(()=>{});
  now.innerHTML = '<b>' + label + '</b> - ' + url +
    ' | <a target="_blank" href="' + url + '">open raw</a>';
  render();
}
list.addEventListener('click', ev => {
  const it = ev.target.closest('.it');
  if(!it || ev.target.tagName === 'A') return;
  play(it.dataset.u, it.dataset.h);
});
document.querySelectorAll('header button').forEach(b => b.onclick = () => {
  document.querySelectorAll('header button').forEach(x => x.classList.remove('on'));
  b.classList.add('on'); filter = b.dataset.f; render();
});
document.getElementById('q').oninput = render;
render();
const v = params.get('v');
if(v && DATA.some(e => e.url === v)){
  const hit = DATA.find(e => e.url === v);
  play(v, hit.human + ' - ' + hit.id);
} else {
  const first = groups();
  const k = Object.keys(first)[0];
  if(k) play(first[k][0].url, first[k][0].human + ' - ' + first[k][0].id);
}
</script>
</body>
</html>
"""

for key, val in {
    "@@T_CAMS@@" : t["cameras_with_loops"],
    "@@T_MB@@"   : "%.1f" % (t["total_bytes"] / 1e6),
    "@@T_OFF@@"  : t["yyc_official"],
    "@@T_WB@@"   : t["yyc_wayback"],
    "@@T_IEM@@"  : t["iem"],
    "@@N_ALL@@"  : len(entries),
    "@@N_OFF@@"  : n_off,
    "@@N_WB@@"   : n_wb,
    "@@N_IEM@@"  : n_iem,
    "@@JSON@@"   : json.dumps(entries),
}.items():
    HTML = HTML.replace(key, str(val))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(HTML)
print("written:", OUT)
print("entries: all=%d off=%d wb=%d iem=%d" % (len(entries), n_off, n_wb, n_iem))
