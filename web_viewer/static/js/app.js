// app.js — main dashboard controller
import { Api } from '/static/js/api.js';
import { buildStream, attachPlayback } from '/static/js/player.js';
import { VirtualGrid } from '/static/js/grid.js';

// ==================== STATE ====================
const STATE_KEY = 'eli6-state';
const SETTINGS_KEY = 'eli6-settings';
const DEFAULT_SETTINGS = {
  randomMode: 'random',       // random | stratified | off
  mapMode: 'random',          // random | stratified
  shuffleSec: 0,              // auto-shuffle (sec). 0=off
  pageSize: 60,               // visible tiles in grid
  mapPoints: 3000,            // max points on map / globe
  defaultType: '',            // default type filter
  showGlobe3D: true,
  heatmap: true,
  labels: true,
};
const state = {
  view: 'grid',
  filter: { q: '', type: '', vis: '', country: '', region: '', city: '', sort: 'idx' },  // type=''=all, 'hls','mjpeg','youtube','mp4'; vis=''=all,'public','private','unknown'
  cams: [],
  visible: [],
  countries: [],
  currentCam: null,
  modalDispose: null,
  modalPlayer: null,
  gridSize: 'compact',
  vgrid: null,
  settings: { ...DEFAULT_SETTINGS },
  seed: Math.floor(Math.random() * 1e9), // base seed for random
};

function loadSettings() {
  try {
    const s = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}');
    return { ...DEFAULT_SETTINGS, ...s };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

function saveSettings() {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(state.settings));
}

state.settings = loadSettings();

// ==================== PERSISTENCE ====================
function loadState() {
  try {
    const s = JSON.parse(localStorage.getItem(STATE_KEY) || '{}');
    return {
      view: s.view || 'grid',
      filter: { q: s.q || '', type: s.type || '', vis: s.vis || '', country: s.country || '', region: s.region || '', city: s.city || '', sort: s.sort || 'idx' },
      gridSize: s.gridSize || 'compact',
    };
  } catch {
    return { view: 'grid', filter: { q:'', type:'', vis:'', country:'', region:'', city:'', sort:'idx' }, gridSize: 'compact' };
  }
}

function saveState() {
  localStorage.setItem(STATE_KEY, JSON.stringify({
    view: state.view,
    q: state.filter.q,
    type: state.filter.type,
    vis: state.filter.vis,
    country: state.filter.country,
    region: state.filter.region,
    city: state.filter.city,
    sort: state.filter.sort,
    gridSize: state.gridSize,
  }));
}

window.addEventListener('storage', (e) => {
  if (e.key === STATE_KEY) {
    const s = loadState();
    Object.assign(state, s);
    Object.assign(state.filter, s.filter);
    document.getElementById('searchInput').value = state.filter.q;
    document.querySelectorAll('.chip[data-type]').forEach(c => c.classList.toggle('active', (c.dataset.type || '') === state.filter.type));
    document.querySelectorAll('.chip[data-vis]').forEach(c => c.classList.toggle('active', (c.dataset.vis || '') === state.filter.vis));
    document.getElementById('countryFilter').value = state.filter.country;
    document.getElementById('regionFilter').value = state.filter.region;
    document.getElementById('cityFilter').value = state.filter.city;
    document.getElementById('sortFilter').value = state.filter.sort;
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === state.view));
    applyGridSize(state.gridSize);
    if (state.view !== 'grid') switchView(state.view);
    applyFilter();
  }
});

// ==================== URL ROUTING ====================
const URL_KEYS = { view: 'view', q: 'q', type: 'type', vis: 'visibility', country: 'country', region: 'region', city: 'city', cam: 'cam', sort: 'sort' };

function readUrlParams() {
  const p = new URLSearchParams(location.search);
  return Object.fromEntries(Object.entries(URL_KEYS).map(([k, v]) => [k, p.get(v) || '']));
}

function writeUrlParams() {
  const p = new URLSearchParams();
  if (state.view !== 'grid') p.set(URL_KEYS.view, state.view);
  if (state.filter.q) p.set(URL_KEYS.q, state.filter.q);
  if (state.filter.type) p.set(URL_KEYS.type, state.filter.type);
  if (state.filter.vis) p.set(URL_KEYS.vis, state.filter.vis);
  if (state.filter.country) p.set(URL_KEYS.country, state.filter.country);
  if (state.filter.region) p.set(URL_KEYS.region, state.filter.region);
  if (state.filter.city) p.set(URL_KEYS.city, state.filter.city);
  if (state.filter.sort && state.filter.sort !== 'idx') p.set(URL_KEYS.sort, state.filter.sort);
  if (state.currentCam) p.set(URL_KEYS.cam, state.currentCam.idx);
  const qs = p.toString();
  history.replaceState(null, '', qs ? '?' + qs : location.pathname);
}

const _url = readUrlParams();
const _persisted = loadState();
state.view = _url.view || _persisted.view || 'grid';
state.filter = { ..._persisted.filter };
for (const k of ['q', 'type', 'vis', 'country', 'region', 'city', 'sort']) {
  if (_url[k]) state.filter[k] = _url[k];
}
state.gridSize = _persisted.gridSize;

// ==================== THEME ====================
const THEME_KEY = 'eli6-theme';
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  localStorage.setItem(THEME_KEY, t);
}
applyTheme(localStorage.getItem(THEME_KEY) || 'dark');
document.getElementById('themeToggle').addEventListener('click', () => {
  applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  if (state.view === 'map' && window.__map) setTimeout(() => window.__map.invalidateSize(), 100);
});

// ==================== GRID SIZE ====================
function applyGridSize(size) {
  state.gridSize = size;
  const tW = size === 'compact' ? 320 : 460;
  const tH = size === 'compact' ? 230 : 320;
  if (state.vgrid) {
    state.vgrid.tileWidth = tW;
    state.vgrid.tileHeight = tH;
    state.vgrid._onResize();
  }
  saveState();
}

// ==================== TOASTS ====================
function toast(msg, type = 'info', duration = 3000) {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.getElementById('toastStack').appendChild(el);
  setTimeout(() => el.remove(), duration + 500);
}

// ==================== RECENT + SHUFFLE + PAUSE ====================
const RECENT_KEY = 'eli6-recent';
function saveRecent(cam) {
  try {
    const recent = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
    const next = [{ idx: cam.idx, name: cam.name, country: cam.country, city: cam.city, type: cam.type, when: Date.now() }, ...recent.filter(r => r.idx !== cam.idx)];
    localStorage.setItem(RECENT_KEY, JSON.stringify(next.slice(0, 30)));
  } catch {}
}
function getRecent() {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch { return []; }
}
function shuffleCam() {
  if (!state.cams.length) {
    toast('No cams loaded', 'error');
    return;
  }
  // If random mode, use a fresh seed so we get DIFFERENT cams each click
  if (state.settings.randomMode === 'random' || state.settings.randomMode === 'stratified') {
    state.seed = Math.floor(Math.random() * 1e9);
    shuffleSeed();
  }
  const cam = state.cams[Math.floor(Math.random() * state.cams.length)];
  openDetail(cam);
}

function shuffleSeed() {
  state.seed = Math.floor(Math.random() * 1e9);
  // Re-fetch with new seed
  if (window.__maplibre) loadMapPoints();
  if (window.__globe) {
    // Rebuild globe points with new seed (cheap: just re-run ensure)
    window.__globe.pointsData([]);
    ensureGlobe();
  }
  // Grid: only re-fetch if in random mode
  if (state.settings.randomMode === 'random' || state.settings.randomMode === 'stratified') {
    reloadCams();
    toast(`New sample · seed ${state.seed}`, 'info');
  } else {
    toast(`New seed ${state.seed} (apply on grid)`, 'info');
  }
}

let shuffleTimer = null;
function setupShuffleTimer() {
  if (shuffleTimer) clearInterval(shuffleTimer);
  const sec = parseInt(state.settings.shuffleSec || 0, 10);
  if (sec > 0) {
    shuffleTimer = setInterval(() => {
      shuffleSeed();
    }, sec * 1000);
  }
}
function pauseAll() {
  for (const [idx, dispose] of activeDisposers.entries()) {
    try { dispose(); } catch {}
  }
  activeDisposers.clear();
  activePlayerCount = 0;
  toast('All streams paused', 'info');
  // Update tile UI to show paused
  document.querySelectorAll('.tile-status').forEach(el => {
    el.textContent = 'PAUSED';
    el.className = 'tile-status';
  });
}

// ==================== FLAGS ====================
const FLAG = {
  'United States':'\u{1f1fa}\u{1f1f8}','Italy':'\u{1f1ee}\u{1f1f9}','France':'\u{1f1eb}\u{1f1f7}','UK':'\u{1f1ec}\u{1f1e7}','Germany':'\u{1f1e9}\u{1f1ea}','Japan':'\u{1f1ef}\u{1f1f5}','Canada':'\u{1f1e8}\u{1f1e6}','Australia':'\u{1f1e6}\u{1f1fa}','Spain':'\u{1f1ea}\u{1f1f8}','Netherlands':'\u{1f1f3}\u{1f1f1}','Switzerland':'\u{1f1e8}\u{1f1ed}','Brazil':'\u{1f1e7}\u{1f1f7}','China':'\u{1f1e8}\u{1f1f3}','Korea':'\u{1f1f0}\u{1f1f7}','Taiwan':'\u{1f1f9}\u{1f1fc}','India':'\u{1f1ee}\u{1f1f3}','Russia':'\u{1f1f7}\u{1f1fa}','Mexico':'\u{1f1f2}\u{1f1fd}','Sweden':'\u{1f1f8}\u{1f1ea}','Norway':'\u{1f1f3}\u{1f1f4}','Finland':'\u{1f1eb}\u{1f1ee}','Denmark':'\u{1f1e9}\u{1f1f0}','Poland':'\u{1f1f5}\u{1f1f1}','Turkey':'\u{1f1f9}\u{1f1f7}','Greece':'\u{1f1ec}\u{1f1f7}','Portugal':'\u{1f1f5}\u{1f1f9}','Czech Republic':'\u{1f1e8}\u{1f1ff}','Hungary':'\u{1f1ed}\u{1f1fa}','Austria':'\u{1f1e6}\u{1f1f9}','Belgium':'\u{1f1e7}\u{1f1ea}','Ireland':'\u{1f1ee}\u{1f1ea}','Romania':'\u{1f1f7}\u{1f1f4}','Slovakia':'\u{1f1f8}\u{1f1f0}','Slovenia':'\u{1f1f8}\u{1f1ee}','Croatia':'\u{1f1ed}\u{1f1f7}','South Africa':'\u{1f1ff}\u{1f1e6}','Thailand':'\u{1f1f9}\u{1f1ed}','Indonesia':'\u{1f1ee}\u{1f1e9}','Philippines':'\u{1f1f5}\u{1f1ed}','Malaysia':'\u{1f1f2}\u{1f1fe}','Israel':'\u{1f1ee}\u{1f1f1}','Argentina':'\u{1f1e6}\u{1f1f7}','Chile':'\u{1f1e8}\u{1f1f1}','Colombia':'\u{1f1e8}\u{1f1f4}','Hong Kong':'\u{1f1ed}\u{1f1f0}','Bulgaria':'\u{1f1e7}\u{1f1ec}','Estonia':'\u{1f1ea}\u{1f1ea}','Latvia':'\u{1f1f1}\u{1f1fb}','Lithuania':'\u{1f1f1}\u{1f1f9}','Luxembourg':'\u{1f1f1}\u{1f1fa}','Iceland':'\u{1f1ee}\u{1f1f8}','Cyprus':'\u{1f1e8}\u{1f1fe}','Malta':'\u{1f1f2}\u{1f1f9}','Andorra':'\u{1f1e6}\u{1f1e9}','Monaco':'\u{1f1f2}\u{1f1e8}','San Marino':'\u{1f1f8}\u{1f1f2}','Vatican City':'\u{1f1fb}\u{1f1e6}','Liechtenstein':'\u{1f1f1}\u{1f1ee}'

};
function flag(country) { return FLAG[country] || (country ? '🏳️' : '🌐'); }

// ==================== TILE RENDER ====================
// Per-viewport cap on simultaneous HLS streams. When more tiles are in
// the viewport than this number, we let newer ones win by FIFO evicting
// the oldest *paused* player (not one mid-load). With the VirtualGrid only
// rendering visible+overscan rows, the natural tile count is already capped
// to ~12-30 depending on screen; this is a hard ceiling for bandwidth.
const MAX_ACTIVE_PLAYERS = 30;
let activePlayerCount = 0;
// Maps cam.idx -> { disposeFn, obs, tile, cam, isIntersecting }
// disposed via VirtualGrid's dispose callback OR IntersectionObserver scrolling-out
const activeDisposers = new Map();
const activePausers = new Map();
const activeResumers = new Map();

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}

function fmt(n) {
  if (n == null) return '—';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(0) + 'k';
  return String(n);
}

function distanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const toRad = d => d * Math.PI / 180;
  const dLat = toRad(lat2 - lat1), dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function renderTile(cam, index) {
  const tile = document.createElement('div');
  tile.className = 'tile';
  tile.dataset.idx = cam.idx;

  const stream = buildStream(cam);
  const typeClass = cam.type === 'mjpeg' ? 'mjpeg' : cam.type === 'youtube' ? 'yt' : cam.type === 'mp4' ? 'mp4' : 'live';
  const typeLabel = (cam.type || 'live').toUpperCase();

  // Media
  const media = document.createElement('div');
  media.className = 'tile-media loading';

  const typeBadge = document.createElement('div');
  typeBadge.className = `tile-type ${typeClass}`;
  typeBadge.textContent = typeLabel;
  media.appendChild(typeBadge);

  if (cam.visibility === 'private') {
    const visBadge = document.createElement('div');
    visBadge.className = 'tile-vis';
    visBadge.textContent = 'private';
    visBadge.title = 'Visibility: private (not intended as a public camera)';
    media.appendChild(visBadge);
  }

  const flag = document.createElement('div');
  flag.className = 'tile-flag';
  flag.textContent = flagEmoji(cam.country);
  media.appendChild(flag);

  const status = document.createElement('div');
  status.className = 'tile-status loading';
  status.textContent = '...';
  media.appendChild(status);

  // Placeholder content (visible while HLS is loading or never loads)
  // Shows a nice gradient with the cam's name and location — much better UX than black
  const placeholder = document.createElement('div');
  placeholder.className = 'tile-placeholder';
  const phName = document.createElement('div');
  phName.className = 'tile-placeholder-name';
  phName.textContent = cam.name || '';
  placeholder.appendChild(phName);
  const phLoc = document.createElement('div');
  phLoc.className = 'tile-placeholder-loc';
  const phLocParts = [];
  if (cam.city) phLocParts.push(cam.city);
  if (cam.country) phLocParts.push(cam.country);
  phLoc.textContent = phLocParts.join(' · ');
  placeholder.appendChild(phLoc);
  media.appendChild(placeholder);

  const overlay = document.createElement('div');
  overlay.className = 'tile-overlay';
  media.appendChild(overlay);

  if (cam.lat != null && cam.lon != null && state.userLat != null) {
    const dist = distanceKm(state.userLat, state.userLon, cam.lat, cam.lon);
    const distEl = document.createElement('div');
    distEl.className = 'tile-dist';
    distEl.textContent = dist < 1000 ? `${Math.round(dist)} km` : `${Math.round(dist / 100) / 10}k km`;
    media.appendChild(distEl);
  }

  tile.appendChild(media);

  // Meta
  const meta = document.createElement('div');
  meta.className = 'tile-meta';
  const name = document.createElement('div');
  name.className = 'tile-name';
  const nm = cam.name || '(no name)';
  if (state.filter.q) {
    const q = state.filter.q.trim();
    if (q && q.length >= 2) {
      try {
        const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        name.innerHTML = nm.replace(re, '<mark>$1</mark>');
      } catch { name.textContent = nm; }
    } else {
      name.textContent = nm;
    }
  } else {
    name.textContent = nm;
  }
  name.title = nm;
  meta.appendChild(name);
  const loc = document.createElement('div');
  loc.className = 'tile-loc';
  const locParts = [];
  if (cam.city) locParts.push(cam.city);
  if (cam.region && cam.region !== cam.city) locParts.push(cam.region);
  if (cam.country && cam.country !== cam.region) locParts.push(cam.country);
  loc.textContent = locParts.join(' › ') || (cam.host || '');
  meta.appendChild(loc);
  tile.appendChild(meta);

  // Click → detail modal
  tile.addEventListener('click', () => openDetail(cam));

  // Lazy playback — single observer per tile. Crucially, this fires only
  // for tiles currently mounted in the DOM. When VirtualGrid removes a
  // tile (because it scrolled out of range), it calls our dispose() below
  // which disconnects this observer AND destroys the player.
  tile.dataset.idx = cam.idx;
  // Wrap player area in a sub-container so chrome stays
  const playerArea = document.createElement('div');
  playerArea.className = 'tile-player';
  playerArea.style.cssText = 'position:absolute;inset:0;z-index:1;';
  media.appendChild(playerArea);

  // Tile lifecycle:
  //   - on entry to viewport: activate player (or queue if at cap)
  //   - on leaving viewport but still in DOM: pause (keep buffer)
  //   - on VirtualGrid disposal (DOM removal): fully destroy player
  const obs = new IntersectionObserver((entries) => {
    for (const ent of entries) {
      const entry = activeDisposers.get(cam.idx);
      if (ent.isIntersecting) {
        if (!entry) {
          // Try to activate. If at cap, evict an inactive one first.
          if (activePlayerCount >= MAX_ACTIVE_PLAYERS) {
            evictOneInactive();
          }
          if (activePlayerCount < MAX_ACTIVE_PLAYERS) {
            activatePlayer(tile, playerArea, status, cam, stream);
          }
        } else {
          // Existing player scrolled back into view — resume
          entry.isIntersecting = true;
          if (controlsFor(cam.idx)) controlsFor(cam.idx).resume();
        }
      } else {
        if (entry) {
          // Scrolled out of viewport but still mounted. Pause to save bandwidth,
          // keep buffer so resume is instant.
          entry.isIntersecting = false;
          if (controlsFor(cam.idx)) controlsFor(cam.idx).pause();
        }
      }
    }
  }, { rootMargin: '200px' });
  obs.observe(tile);

  // Stash a dispose-tile callback on the tile DOM node itself, so
  // VirtualGrid can find it when it removes this tile from the DOM.
  // This handles the "scrolled out of virtual range AND out of viewport"
  // case — the IntersectionObserver alone never fires for detached nodes.
  tile._disposeTile = () => {
    const entry = activeDisposers.get(cam.idx);
    try { obs.disconnect(); } catch {}
    if (entry) {
      try { entry.disposeFn(); } catch {}
      activeDisposers.delete(cam.idx);
    }
    activePausers.delete(cam.idx);
    activeResumers.delete(cam.idx);
  };
  // Save the obs reference so VirtualGrid.disposer can disconnect it
  tile._observer = obs;
  tile._cam = cam;

  return tile;
}

function controlsFor(idx) {
  // Look up the player controls for the given cam idx, if any.
  // We attach them as a side-effect of activatePlayer. Stash via a Map.
  return _controlsByIdx.get(idx) || null;
}
const _controlsByIdx = new Map();

function evictOneInactive() {
  // Find an inactive player (paused or scrolled-out-of-viewport) and
  // dispose it so a new player can activate. Never evict one mid-stream
  // that's still being watched by the user.
  for (const [idx, entry] of activeDisposers.entries()) {
    if (!entry.isIntersecting) {
      try { entry.disposeFn(); } catch {}
      activeDisposers.delete(idx);
      activePausers.delete(idx);
      activeResumers.delete(idx);
      _controlsByIdx.delete(idx);
      return true;
    }
  }
  return false;
}

function activatePlayer(tile, playerArea, status, cam, stream) {
  if (activeDisposers.has(cam.idx)) {
    // Already active. Just refresh intersecting flag.
    const entry = activeDisposers.get(cam.idx);
    entry.isIntersecting = true;
    const ctrls = _controlsByIdx.get(cam.idx);
    if (ctrls && ctrls.resume) try { ctrls.resume(); } catch {}
    return;
  }
  activePlayerCount++;
  // attachPlayback returns { dispose, pause, resume, type }
  const controls = attachPlayback(playerArea, status, cam, stream, (s) => {
    if (s.cls === 'live') {
      const el = document.getElementById('statLoaded');
      const n = parseInt((el.textContent || '0').replace(/[^\d]/g, '') || '0', 10) + 1;
      el.textContent = n.toLocaleString();
    } else if (s.cls === 'error') {
      const el = document.getElementById('statErr');
      const n = parseInt((el.textContent || '0').replace(/[^\d]/g, '') || '0', 10) + 1;
      el.textContent = n.toLocaleString();
    }
  });
  _controlsByIdx.set(cam.idx, controls);

  const disposeFn = () => {
    activePlayerCount--;
    _controlsByIdx.delete(cam.idx);
    activePausers.delete(cam.idx);
    activeResumers.delete(cam.idx);
    try { controls.dispose(); } catch {}
  };
  if (controls && controls.pause && controls.resume) {
    activePausers.set(cam.idx, () => controls.pause());
    activeResumers.set(cam.idx, () => controls.resume());
  }
  const entry = { tile, isIntersecting: true, disposeFn };
  activeDisposers.set(cam.idx, entry);
}

const flagEmoji = flag;

// ==================== FILTER ====================
function applyFilter() {
  // Server-side already filtered. Just push to virtual grid.
  state.visible = state.cams;
  document.getElementById('statVisible').textContent = fmt(state.visible.length);
  document.getElementById('emptyState').style.display = state.visible.length === 0 ? 'flex' : 'none';
  if (state.vgrid) {
    state.vgrid.setData(state.visible);
  }
}

function setStats(types, total, byVis, byVisLive) {
  document.getElementById('countAll').textContent = fmt(total != null ? total : state.cams.length);
  document.getElementById('countHls').textContent = fmt(types.hls || 0);
  document.getElementById('countYt').textContent = fmt(types.youtube || 0);
  document.getElementById('countMjpeg').textContent = fmt(types.mjpeg || 0);
  document.getElementById('countMp4').textContent = fmt(types.mp4 || 0);
  if (byVis) {
    // Counts must match what each chip displays:
    //   all / public -> live-scoped (default dashboard view)
    //   private / unknown -> full bucket (no live filter on server)
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = fmt(v || 0); };
    const visLive = byVisLive || {};
    set('countVisAll', total != null ? total : 0);
    set('countVisPublic', visLive.public != null ? visLive.public : byVis.public);
    set('countVisPrivate', byVis.private);
    set('countVisUnknown', byVis.unknown);
  }
}

// ==================== VIEW SWITCHING ====================
const viewContainer = document.getElementById('viewContainer');
function switchView(v) {
  state.view = v;
  ['gridScroll', 'mapContainer', 'globeContainer', 'aiContainer', 'emptyState'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });

  if (v === 'grid') {
    document.getElementById('gridScroll').style.display = '';
    document.getElementById('emptyState').style.display = state.visible.length === 0 ? 'flex' : 'none';
  } else if (v === 'map') {
    document.getElementById('mapContainer').style.display = '';
    ensureMap();
  } else if (v === 'globe') {
    document.getElementById('globeContainer').style.display = '';
    ensureGlobe();
  } else if (v === 'ai') {
    document.getElementById('aiContainer').style.display = '';
    ensureAI();
  }
  writeUrlParams();
}

// ==================== MAP (MapLibre 2D, Osiris-style) ====================
let maplibreMap = null;
let maplibreLoaded = false;
let mapHudData = null;

async function ensureMap() {
  if (window.__maplibre) {
    if (document.getElementById('globeMapStatus')) document.getElementById('globeMapStatus').textContent = '> refreshing...';
    setTimeout(() => window.__maplibre.resize(), 100);
    if (mapHudData) updateMapHud();
    await loadMapPoints();
    return;
  }
  if (!maplibreLoaded) {
    maplibreLoaded = true;
    await loadScript('/static/vendor/maplibre-gl.js');
    document.getElementById('mapContainer').innerHTML = `
      <div id="maplibreMap" style="width:100%;height:100%"></div>
      <div class="map-status" id="globeMapStatus">> initializing...</div>
      <div class="map-hud" id="mapHud" style="display:none"></div>
      <div class="map-toolbar">
        <button id="mapRefresh" title="Resample">RESAMPLE</button>
        <button id="mapStyle" title="Basemap">DARK</button>
        <button id="mapHeat" title="Heatmap">HEAT</button>
        <button id="mapFit" title="Fit world">FIT</button>
      </div>
    `;
  }

  const style = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
  const map = new maplibregl.Map({
    container: 'maplibreMap',
    style,
    center: [0, 25],
    zoom: 1.5,
    minZoom: 1,
    maxZoom: 18,
    attributionControl: true,
  });

  map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'bottom-right');
  map.addControl(new maplibregl.ScaleControl({ maxWidth: 100, unit: 'metric' }), 'bottom-left');

  map.on('load', async () => {
    map.addSource('cams', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });

    map.addLayer({
      id: 'cam-glow',
      type: 'circle',
      source: 'cams',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, 4, 5, 8, 10, 14, 14, 22],
        'circle-color': ['match', ['get', 'type'], 'hls', '#ff2e3a', 'mp4', '#ff5a1f', 'youtube', '#a78bfa', 'mjpeg', '#ff6666', '#ff6666'],
        'circle-opacity': 0.18,
        'circle-blur': 0.6,
      },
    });
    map.addLayer({
      id: 'cam-dots',
      type: 'circle',
      source: 'cams',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, 2, 5, 4, 10, 7, 14, 11],
        'circle-color': ['match', ['get', 'type'], 'hls', '#ff2e3a', 'mp4', '#ff5a1f', 'youtube', '#a78bfa', 'mjpeg', '#ff6666', '#888'],
        'circle-opacity': 0.92,
        'circle-stroke-width': 1.2,
        'circle-stroke-color': '#000',
        'circle-stroke-opacity': 0.85,
      },
    });
    map.addSource('cam-heat', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    map.addLayer({
      id: 'cam-heatmap',
      type: 'heatmap',
      source: 'cam-heat',
      paint: {
        'heatmap-weight': ['interpolate', ['linear'], ['get', 'w'], 0, 0, 10, 1],
        'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 0.5, 9, 3],
        'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 6, 9, 24],
        'heatmap-opacity': 0.6,
        'heatmap-color': [
          'interpolate', ['linear'], ['heatmap-density'],
          0, 'rgba(0,0,0,0)',
          0.1, 'rgba(80,10,15,0.6)',
          0.3, 'rgba(160,20,30,0.7)',
          0.5, 'rgba(220,40,50,0.85)',
          0.7, 'rgba(255,80,40,0.9)',
          1, 'rgba(255,200,80,1)',
        ],
      },
    }, 'cam-glow');
    map.setLayoutProperty('cam-heatmap', 'visibility', state.settings.heatmap ? 'visible' : 'none');

    map.on('click', 'cam-dots', (e) => {
      const f = e.features && e.features[0];
      if (!f) return;
      const p = f.properties;
      e.preventDefault();
      const popupHtml = `
        <div style="font-family:var(--font-mono);min-width:200px">
          <div style="font-weight:700;color:#ff2e3a;font-size:13px;margin-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:6px">${escapeHtml(p.name || 'unnamed')}</div>
          <div style="font-size:10px;color:#888;line-height:1.6">
            <div><span style="color:#666">IDX</span> ${p.idx}</div>
            <div><span style="color:#666">TYPE</span> ${(p.type || '').toUpperCase()}</div>
            <div><span style="color:#666">LOC</span> ${escapeHtml([p.city, p.region, p.country].filter(Boolean).join(', ') || '\u2014')}</div>
            ${p.url ? `<div style="margin-top:4px"><span style="color:#666">URL</span> ${escapeHtml(p.url.substring(0, 60))}${p.url.length > 60 ? '...' : ''}</div>` : ''}
          </div>
          <button id="popupOpen" style="margin-top:10px;width:100%;background:#ff2e3a;color:#000;border:0;padding:6px 10px;font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:0.1em;cursor:pointer">OPEN CAM</button>
        </div>`;
      new maplibregl.Popup({ closeButton: true, offset: 14, maxWidth: '320px' })
        .setLngLat(f.geometry.coordinates)
        .setHTML(popupHtml)
        .addTo(map);
      setTimeout(() => {
        const b = document.getElementById('popupOpen');
        if (b) b.onclick = () => {
          const cam = state.cams.find(c => c.idx == p.idx);
          if (cam) openDetail(cam);
        };
      }, 50);
    });
    map.on('mouseenter', 'cam-dots', () => map.getCanvas().style.cursor = 'pointer');
    map.on('mouseleave', 'cam-dots', () => map.getCanvas().style.cursor = '');

    document.getElementById('mapRefresh').onclick = () => loadMapPoints();
    document.getElementById('mapFit').onclick = () => map.fitBounds([[-180, -60], [180, 75]], { padding: 40 });
    const hb = document.getElementById('mapHeat');
    if (hb) {
      hb.classList.toggle('active', state.settings.heatmap);
      hb.onclick = (e) => {
        state.settings.heatmap = !state.settings.heatmap;
        e.currentTarget.classList.toggle('active', state.settings.heatmap);
        map.setLayoutProperty('cam-heatmap', 'visibility', state.settings.heatmap ? 'visible' : 'none');
        saveSettings();
      };
    }

    window.__maplibre = map;
    await loadMapPoints();
  });
}

async function loadMapPoints() {
  const map = window.__maplibre;
  if (!map) return;
  const status = document.getElementById('globeMapStatus');
  if (status) status.textContent = '> sampling...';
  const limit = state.settings.mapPoints;
  try {
    const gj = await Api.geojson({
      mode: state.settings.mapMode || 'random',
      seed: state.seed,
      limit,
    });
    map.getSource('cams').setData(gj);
    const heatFC = {
      type: 'FeatureCollection',
      features: gj.features.map(f => ({
        type: 'Feature',
        geometry: f.geometry,
        properties: { w: 1 },
      })),
    };
    map.getSource('cam-heat').setData(heatFC);
    if (status) status.textContent = `> ${gj.features.length.toLocaleString()} cams - seed ${state.seed}`;
    buildMapHud(gj);
  } catch (e) {
    if (status) status.textContent = '> load failed: ' + (e.message || e);
  }
}

function buildMapHud(gj) {
  const hud = document.getElementById('mapHud');
  if (!hud) return;
  const counts = { total: gj.features.length, byType: {}, byCountry: {} };
  for (const f of gj.features) {
    const t = f.properties.type || 'other';
    counts.byType[t] = (counts.byType[t] || 0) + 1;
    const c = f.properties.country || 'Unknown';
    counts.byCountry[c] = (counts.byCountry[c] || 0) + 1;
  }
  const topCountries = Object.entries(counts.byCountry).sort((a,b) => b[1]-a[1]).slice(0, 6);
  const topTypes = Object.entries(counts.byType).sort((a,b) => b[1]-a[1]);
  const seed = state.seed;
  mapHudData = { counts, topCountries, topTypes, seed };
  hud.innerHTML = `
    <h4>LIVE SAMPLE</h4>
    <div class="map-hud-row"><span class="l">points</span><span class="v accent">${counts.total.toLocaleString()}</span></div>
    <div class="map-hud-row"><span class="l">seed</span><span class="v">${seed}</span></div>
    <div class="map-hud-row"><span class="l">mode</span><span class="v">${state.settings.mapMode}</span></div>
    <h4 style="margin-top:8px">TOP REGIONS</h4>
    ${topCountries.map(([c, n]) => `<div class="map-hud-row"><span class="l">${escapeHtml(c)}</span><span class="v">${n}</span></div>`).join('')}
    <h4 style="margin-top:8px">TYPES</h4>
    ${topTypes.map(([t, n]) => `<div class="map-hud-row"><span class="l">${escapeHtml(t)}</span><span class="v">${n.toLocaleString()}</span></div>`).join('')}
  `;
  hud.style.display = '';
}

function updateMapHud() {
  const map = window.__maplibre;
  if (!map) return;
  const status = document.getElementById('globeMapStatus');
  if (status) status.textContent = '> refreshing seed...';
}

// ==================== GLOBE (lighter, optional) ====================
let globeLoaded = false;
async function ensureGlobe() {
  if (!state.settings.showGlobe3D) {
    document.getElementById('globeContainer').innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-dim);font-family:var(--font-mono)"><div>3D globe disabled in settings</div></div>';
    return;
  }
  if (window.__globe) return;
  if (!globeLoaded) {
    globeLoaded = true;
    await loadScript('/static/vendor/three.min.js');
    await loadScript('/static/vendor/globe.gl.min.js');
    document.getElementById('globeContainer').innerHTML = `
      <div id="globe" style="width:100%;height:100%"></div>
      <div class="map-status" id="globeStatus">initializing</div>
    `;
  }
  document.getElementById('globe').innerHTML = '';

  try {
    document.getElementById('globeStatus').textContent = '> sampling cams...';
    const gj = await Api.geojson({
      mode: 'random',
      seed: state.seed,
      limit: Math.min(state.settings.mapPoints, 5000),
    });
    const allPoints = gj.features.map(f => {
      const [lon, lat] = f.geometry.coordinates;
      return {
        lat, lng: lon,
        idx: f.properties.idx,
        name: f.properties.name,
        type: f.properties.type,
        country: f.properties.country,
      };
    }).filter(p => Number.isFinite(p.lat) && Number.isFinite(p.lng));

    const buckets = {};
    for (const p of allPoints) {
      const key = (Math.round(p.lat * 50) / 50) + '|' + (Math.round(p.lng * 50) / 50);
      if (!buckets[key]) buckets[key] = { ...p, count: 0 };
      buckets[key].count += 1;
    }
    const points = Object.values(buckets);
    const typeColors = {
      hls: '#ff2e3a', mp4: '#ff5a1f', youtube: '#a78bfa', mjpeg: '#ff6666', other: '#888'
    };

    const Globe = window.ThreeGlobe || window.Globe;
    if (!Globe) throw new Error('globe.gl not loaded');
    const globeEl = document.getElementById('globe');
    const globe = new Globe(globeEl, { animateIn: true })
      .globeImageUrl('/static/vendor/earth-night.jpg')
      .bumpImageUrl('/static/vendor/earth-topology.png')
      .backgroundImageUrl('/static/vendor/night-sky.png')
      .pointLat(d => d.lat)
      .pointLng(d => d.lng)
      .pointColor(d => typeColors[d.type] || '#ff6666')
      .pointAltitude(d => d.type === 'hls' ? 0.04 : 0.02)
      .pointRadius(d => Math.max(0.15, Math.min(0.5, Math.log2((d.count || 1) + 1) * 0.18)))
      .pointsMerge(true)
      .onPointClick(p => {
        const cam = state.cams.find(c => c.idx == p.idx);
        if (cam) openDetail(cam);
      })
      .pointsData(points);

    if (state.settings.heatmap) {
      const heat = points.filter(p => p.count > 1).map(p => ({
        lat: p.lat, lng: p.lng, weight: Math.log2(p.count + 1),
      }));
      globe.heatmapsData([heat]).heatmapBandwidth(0.5).heatmapColorSaturation(3);
    }
    document.getElementById('globeStatus').textContent =
      `${allPoints.length.toLocaleString()} cams / ${points.length.toLocaleString()} points`;

    let idleT;
    const resetIdle = () => {
      clearTimeout(idleT);
      idleT = setTimeout(() => {
        globe.controls().autoRotate = true;
        globe.controls().autoRotateSpeed = 0.4;
      }, 4000);
    };
    globeEl.addEventListener('mousedown', () => { globe.controls().autoRotate = false; resetIdle(); });
    globeEl.addEventListener('wheel', () => resetIdle());
    resetIdle();
    window.__globe = globe;
  } catch (e) {
    console.error('globe init failed', e);
    document.getElementById('globeContainer').innerHTML = `
      <div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--err);font-family:var(--font-mono)">
        <div>
          <div style="font-size:14px;margin-bottom:8px">Globe failed to load</div>
          <div style="font-size:11px;color:var(--text-dim)">${escapeHtml(String(e))}</div>
        </div>
      </div>
    `;
  }
}

// ==================== AI VIEW ====================
let aiLoaded = false;
async function ensureAI() {
  const el = document.getElementById('aiContainer');
  if (aiLoaded) return;
  aiLoaded = true;
  el.innerHTML = `
    <div class="ai-header">
      <div style="font-family:var(--font-mono);font-size:13px;font-weight:700;color:var(--accent)">▸ AI INSIGHTS</div>
      <button class="btn" id="aiRefresh">↻ refresh</button>
    </div>
    <div class="ai-grid" id="aiGrid">
      <div class="ai-snapshot" id="aiSnapshot">loading snapshot…</div>
      <div class="ai-chat">
        <div class="ai-section-title">▸ ask the data</div>
        <div class="ai-chat-history" id="aiChatHistory">
          <div class="ai-chat-msg hint">Try: <code>top 5 cities in Japan</code> · <code>cams in NYC by type</code> · <code>countries with most traffic cams</code></div>
        </div>
        <div class="ai-chat-input-row">
          <input id="aiChatInput" type="text" placeholder="ask anything about the cam database…" autocomplete="off" spellcheck="false">
          <button class="btn primary" id="aiChatSend">▶</button>
        </div>
        <div id="aiChatResult" class="ai-chat-result"></div>
      </div>
      <div class="ai-section" id="aiInsightsSection">
        <div class="ai-section-title">▸ auto-generated insights</div>
        <div id="aiInsights">loading…</div>
      </div>
      <div class="ai-section" style="grid-column:1/3">
        <div class="ai-section-title">▸ cam hotspots (dbscan clustering)</div>
        <div class="hotspot-list" id="aiHotspots">loading…</div>
      </div>
    </div>`;

  document.getElementById('aiRefresh').addEventListener('click', () => { aiLoaded = false; ensureAI(); });
  await loadAIData();
}

async function loadAIData() {
  try {
    const [snap, insights, hotspots] = await Promise.all([
      Api.aiSnapshot(),
      Api.aiInsights(),
      Api.aiHotspots(),
    ]);
    document.getElementById('aiSnapshot').textContent = '◉ ' + snap.summary;

    // Build chart for top countries
    const maxCount = Math.max(...(insights.top_countries || []).map(c => c.count), 1);
    const chartHtml = (insights.top_countries || []).map(c => {
      const w = Math.max(8, Math.round(c.count / maxCount * 100));
      return `<div class="bar-row" data-country="${escapeHtml(c.country)}">
        <div class="bar-label">${flagEmoji(c.country)} ${escapeHtml(c.country)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${w}%"></div>
          <div class="bar-count">${c.count.toLocaleString()}</div>
        </div>
      </div>`;
    }).join('');
    // Type breakdown as chips
    const typeHtml = (insights.type_breakdown || []).map(t => {
      const color = t.type === 'hls' ? 'var(--accent)' : t.type === 'mjpeg' ? 'var(--warn)' : t.type === 'youtube' ? 'var(--purple)' : 'var(--text-dim)';
      return `<div class="type-chip" style="--c:${color}">
        <span class="type-pct">${t.pct}%</span>
        <span class="type-name">${(t.type || 'other').toUpperCase()}</span>
      </div>`;
    }).join('');
    document.getElementById('aiInsights').innerHTML = `
      <div class="ai-section-title" style="margin-top:0">▸ top countries (live cams)</div>
      <div class="bar-chart">${chartHtml}</div>
      <div class="ai-section-title">▸ stream type mix</div>
      <div class="type-chips">${typeHtml}</div>
      <div class="ai-section-title">▸ text insights</div>
      ${insights.insights.map(i => `<div class="ai-insight">${escapeHtml(i)}</div>`).join('')}
    `;
    // Wire bar chart clicks to filter
    document.querySelectorAll('.bar-row').forEach(el => {
      el.addEventListener('click', () => {
        const co = el.dataset.country;
        if (co) {
          document.querySelector('.tab[data-view="grid"]').click();
          state.filter.country = co;
          saveState();
          applyFilter();
        }
      });
    });

    document.getElementById('aiHotspots').innerHTML = hotspots.clusters.slice(0, 30).map(c => `
      <div class="hotspot" data-idx="${c.samples[0]?.idx || ''}">
        <div>
          <div style="font-weight:600">${c.count} cams nearby</div>
          <div class="hotspot-meta">${c.cities.slice(0, 3).join(', ') || c.countries.slice(0, 2).join(', ')}</div>
        </div>
        <div class="hotspot-count">${c.count}</div>
      </div>
    `).join('') || '<div style="padding:20px;color:var(--text-dim)">No hotspots found</div>';
    document.querySelectorAll('.hotspot').forEach(el => {
      el.addEventListener('click', () => {
        const idx = el.dataset.idx;
        if (!idx) return;
        const cam = state.cams.find(c => c.idx == idx);
        if (cam) openDetail(cam);
      });
    });

    // Wire AI chat
    const chatInput = document.getElementById('aiChatInput');
    const chatSend = document.getElementById('aiChatSend');
    const chatHistory = document.getElementById('aiChatHistory');
    const chatResult = document.getElementById('aiChatResult');
    async function sendChat() {
      const q = chatInput.value.trim();
      if (!q) return;
      const userMsg = document.createElement('div');
      userMsg.className = 'ai-chat-msg user';
      userMsg.textContent = '▸ ' + q;
      chatHistory.appendChild(userMsg);
      chatHistory.scrollTop = chatHistory.scrollHeight;
      chatInput.value = '';
      chatSend.disabled = true;
      chatSend.textContent = '...';
      try {
        const r = await fetch('/api/ai/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ q }),
        });
        const data = await r.json();
        const botMsg = document.createElement('div');
        botMsg.className = 'ai-chat-msg bot';
        botMsg.style.whiteSpace = 'pre-wrap';
        botMsg.textContent = data.answer || 'no answer';
        chatHistory.appendChild(botMsg);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        // Show result buttons if any
        if (data.results && data.results.length) {
          const btns = document.createElement('div');
          btns.className = 'ai-chat-actions';
          if (data.type === 'top' || data.type === 'category') {
            btns.innerHTML = `<button class="btn" id="aiFilterBtn">▸ show on grid</button>`;
            btns.querySelector('#aiFilterBtn').addEventListener('click', () => {
              // For "top X" results, take the top 1 result and filter by that
              const top = data.results[0];
              if (top) {
                if (data.type === 'category' && top.name) {
                  document.querySelector('.tab[data-view="grid"]').click();
                  state.filter.type = top.name === 'hls' ? 'hls' : top.name === 'mjpeg' ? 'mjpeg' : top.name === 'youtube' ? 'youtube' : '';
                  applyFilter();
                } else if (top.name) {
                  // For top N countries/cities/etc, filter by that value
                  const filterKey = data.type === 'top' ? 'country' : null; // best guess
                  if (filterKey) {
                    document.querySelector('.tab[data-view="grid"]').click();
                    state.filter[filterKey] = top.name;
                    saveState();
                    document.getElementById(filterKey + 'Filter').value = top.name;
                    applyFilter();
                  }
                }
              }
            });
          } else if (data.type === 'place_lookup' && data.results[0]?.idx) {
            btns.innerHTML = `<button class="btn primary" id="aiOpenFirst">▸ open first</button> <button class="btn" id="aiShowGrid">▸ show on grid</button> <button class="btn" id="aiShowMap">▸ show on map</button>`;
            btns.querySelector('#aiOpenFirst').addEventListener('click', () => {
              const c = state.cams.find(x => x.idx == data.results[0].idx);
              if (c) openDetail(c);
              else Api.cam(data.results[0].idx).then(openDetail);
            });
            btns.querySelector('#aiShowGrid').addEventListener('click', () => {
              document.querySelector('.tab[data-view="grid"]').click();
            });
            btns.querySelector('#aiShowMap').addEventListener('click', () => {
              document.querySelector('.tab[data-view="map"]').click();
              if (data.results[0]?.lat && window.__flyTo) {
                setTimeout(() => window.__flyTo(data.results[0].lat, data.results[0].lon), 500);
              }
            });
          } else if (data.results[0]?.idx) {
            btns.innerHTML = `<button class="btn primary" id="aiOpenFirst">▸ open first match</button>`;
            btns.querySelector('#aiOpenFirst').addEventListener('click', () => {
              const c = state.cams.find(x => x.idx == data.results[0].idx);
              if (c) openDetail(c);
              else Api.cam(data.results[0].idx).then(openDetail);
            });
          }
          if (btns.innerHTML) chatHistory.appendChild(btns);
        }
      } catch (e) {
        const errMsg = document.createElement('div');
        errMsg.className = 'ai-chat-msg bot error';
        errMsg.textContent = '✗ query failed: ' + e.message;
        chatHistory.appendChild(errMsg);
      } finally {
        chatSend.disabled = false;
        chatSend.textContent = '▶';
      }
    }
    chatSend.addEventListener('click', sendChat);
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); sendChat(); }
    });
  } catch (e) {
    console.error('AI data failed', e);
  }
}

// ==================== DETAIL MODAL ====================
async function openDetail(cam) {
  state.currentCam = cam;
  saveRecent(cam);
  const m = document.getElementById('detailModal');
  const titleEl = document.getElementById('modalTitle');
  const subEl = document.getElementById('modalSubtitle');
  const side = document.getElementById('modalSide');
  const videoEl = document.getElementById('modalVideo');

  titleEl.textContent = cam.name || `cam #${cam.idx}`;
  const subParts = [];
  if (cam.idx) subParts.push(`#${cam.idx}`);
  if (cam.host) subParts.push(cam.host);
  if (cam.isp) subParts.push(cam.isp);
  subEl.textContent = subParts.join(' · ');

  // Fetch full details
  try {
    const full = await Api.cam(cam.idx);
    cam._full = full;
  } catch {}

  // Render side panel
  const f = cam._full || cam;
  side.innerHTML = `
    <div class="ai-section">
      <div class="ai-section-title">location</div>
      <div class="drawer-row"><span class="k">city</span><span class="v">${escapeHtml(f.city || '—')}</span></div>
      <div class="drawer-row"><span class="k">region</span><span class="v">${escapeHtml(f.region || '—')}</span></div>
      <div class="drawer-row"><span class="k">country</span><span class="v">${escapeHtml(f.country || '—')}</span></div>
      <div class="drawer-row"><span class="k">lat / lon</span><span class="v">${f.lat != null ? f.lat.toFixed(4) + ', ' + f.lon.toFixed(4) : '—'}</span></div>
      <div class="drawer-row"><span class="k">host</span><span class="v">${escapeHtml(f.host || '—')}</span></div>
    </div>
    <div class="ai-section">
      <div class="ai-section-title">stream</div>
      <div class="drawer-row"><span class="k">type</span><span class="v">${escapeHtml(f.type || '—')}</span></div>
      <div class="drawer-row"><span class="k">category</span><span class="v">${escapeHtml(f.category || '—')}</span></div>
      <div class="drawer-row"><span class="k">visibility</span><span class="v ${f.visibility === 'private' ? 'bad' : ''}">${escapeHtml(f.visibility || 'unknown')}</span></div>
      <div class="drawer-row"><span class="k">brand</span><span class="v">${escapeHtml(f.brand || '—')}</span></div>
      <div class="drawer-row"><span class="k">model</span><span class="v">${escapeHtml(f.model || '—')}</span></div>
      <div class="drawer-row"><span class="k">live url</span><span class="v mono" style="word-break:break-all;font-size:10px">${escapeHtml((f.live || '').slice(0, 200))}</span></div>
      <div class="drawer-row"><span class="k">source</span><span class="v mono" style="word-break:break-all;font-size:10px">${escapeHtml((f.url || '').slice(0, 200))}</span></div>
    </div>
    <div class="ai-section">
      <div class="ai-section-title">status</div>
      <div class="drawer-row"><span class="k">live_status</span><span class="v ${f.live_status === 'live' ? 'live' : f.live_status === 'auth_required' ? '' : 'bad'}">${escapeHtml(f.live_status || '—')}</span></div>
      <div class="drawer-row"><span class="k">http</span><span class="v">${escapeHtml(f.content_type || '—')}</span></div>
      <div class="drawer-row"><span class="k">auth</span><span class="v">${f.auth ? 'yes' : 'no'}</span></div>
      <div class="drawer-row"><span class="k">isp</span><span class="v">${escapeHtml(f.isp || '—')}</span></div>
      <div class="drawer-row"><span class="k">confidence</span><span class="v">${f.confidence || 0}</span></div>
    </div>
    <div class="ai-section" id="similarSection" style="display:none">
      <div class="ai-section-title">similar cams</div>
      <div id="similarList">searching…</div>
    </div>`;

  // Player
  if (state.modalDispose) { state.modalDispose(); state.modalDispose = null; }
  videoEl.innerHTML = '';
  const statusEl = document.createElement('div');
  statusEl.className = 'tile-status loading';
  statusEl.textContent = '...';
  statusEl.style.cssText = 'position:absolute;bottom:14px;left:14px;padding:4px 10px;background:rgba(0,0,0,0.7);border:1px solid currentColor;color:var(--text-dim);font-family:JetBrains Mono;font-size:11px;font-weight:700;letter-spacing:0.1em;z-index:5';
  videoEl.appendChild(statusEl);
  const overlay = document.createElement('div');
  overlay.className = 'modal-video-overlay';
  overlay.style.cssText = 'z-index:4';
  overlay.textContent = `${(cam.type || '').toUpperCase()} · ${(f.content_type || '').slice(0, 30) || 'live'}`;
  videoEl.appendChild(overlay);
  const stream = buildStream(cam);
  const p = attachPlayback(videoEl, statusEl, cam, stream);
  state.modalDispose = p.dispose;
  state.modalPlayer = p;

  m.classList.add('show');
  writeUrlParams();

  // Wire actions
  document.getElementById('btnCopyUrl').onclick = () => {
    navigator.clipboard.writeText(cam.live || cam.url || '');
    toast('URL copied', 'success', 1500);
  };
  document.getElementById('btnOpenRaw').onclick = () => {
    window.open(cam.live || cam.url || '', '_blank', 'noopener');
  };
  document.getElementById('btnShare').onclick = () => {
    const url = `${location.origin}/?cam=${cam.idx}`;
    navigator.clipboard.writeText(url);
    toast('link copied to clipboard', 'success', 2000);
  };
  document.getElementById('btnFindSimilar').onclick = async () => {
    const sec = document.getElementById('similarSection');
    const list = document.getElementById('similarList');
    sec.style.display = '';
    list.textContent = 'searching…';
    try {
      const r = await Api.aiSimilar(cam.idx);
      list.innerHTML = r.similar.slice(0, 12).map(c => `
        <div class="hotspot" data-idx="${c.idx}">
          <div>
            <div style="font-weight:600;font-size:12px">${escapeHtml(c.name || '')}</div>
            <div class="hotspot-meta">${escapeHtml([c.city, c.country].filter(Boolean).join(', '))}</div>
          </div>
          <div class="hotspot-count">${c.score}</div>
        </div>
      `).join('') || '<div style="color:var(--text-dim);padding:8px">No similar cams</div>';
      list.querySelectorAll('.hotspot').forEach(el => {
        el.addEventListener('click', () => {
          const newCam = state.cams.find(c => c.idx == el.dataset.idx);
          if (newCam) openDetail(newCam);
        });
      });
    } catch (e) {
      list.textContent = 'error: ' + e.message;
    }
  };
  document.getElementById('btnShowOnMap').onclick = () => {
    closeDetail();
    document.querySelector('[data-view="map"]').click();
    setTimeout(() => {
      if (window.__flyTo && cam.lat != null) window.__flyTo(cam.lat, cam.lon);
    }, 500);
  };
}

function closeDetail() {
  document.getElementById('detailModal').classList.remove('show');
  if (state.modalDispose) { state.modalDispose(); state.modalDispose = null; }
  state.modalPlayer = null;
  state.currentCam = null;
  writeUrlParams();
}
document.getElementById('modalClose').addEventListener('click', closeDetail);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeDetail();
});

// ==================== STATS DRAWER ====================
document.getElementById('statsToggle').addEventListener('click', () => {
  document.getElementById('statsDrawer').classList.add('open');
  refreshStats();
});
document.getElementById('statsClose').addEventListener('click', () => {
  document.getElementById('statsDrawer').classList.remove('open');
});

// Auto-refresh stats drawer every 30s while open
setInterval(() => {
  if (document.getElementById('statsDrawer').classList.contains('open')) {
    refreshStats();
  }
}, 30000);

async function refreshStats() {
  try {
    const [stats, health] = await Promise.all([Api.stats(), Api.health()]);
    const body = document.getElementById('statsBody');
    body.innerHTML = `
      <div class="drawer-section">
        <div class="drawer-section-title">overview</div>
        <div class="stat-grid-2">
          <div class="stat-card"><div class="v">${fmt(stats.total)}</div><div class="l">total cams</div></div>
          <div class="stat-card"><div class="v" style="color:var(--live)">${fmt(stats.live)}</div><div class="l">live</div></div>
          <div class="stat-card"><div class="v" style="color:var(--err)">${fmt(stats.dead)}</div><div class="l">dead</div></div>
          <div class="stat-card"><div class="v" style="color:var(--yellow)">${fmt(stats.auth_required)}</div><div class="l">auth required</div></div>
        </div>
        <div class="stat-grid-2" style="margin-top:8px">
          <div class="stat-card"><div class="v">${fmt(stats.with_geo)}</div><div class="l">with geo</div></div>
          <div class="stat-card"><div class="v">${fmt(stats.distinct_countries)}</div><div class="l">countries</div></div>
          <div class="stat-card"><div class="v">${fmt(stats.distinct_cities)}</div><div class="l">cities</div></div>
          <div class="stat-card"><div class="v">${fmt(stats.distinct_hosts)}</div><div class="l">hosts</div></div>
        </div>
      </div>

      <div class="drawer-section">
        <div class="drawer-section-title">by type</div>
        ${Object.entries(stats.by_type).sort((a,b) => b[1] - a[1]).map(([k,v]) =>
          `<div class="drawer-row"><span class="k">${k.toUpperCase()}</span><span class="v">${fmt(v)}</span></div>`
        ).join('')}
      </div>

      <div class="drawer-section">
        <div class="drawer-section-title">visibility</div>
        ${Object.entries(stats.by_visibility || {}).sort((a,b) => b[1] - a[1]).map(([k,v]) =>
          `<div class="drawer-row"><span class="k">${escapeHtml(k)}</span><span class="v ${k === 'private' ? 'bad' : ''}">${fmt(v)}</span></div>`
        ).join('')}
      </div>

      <div class="drawer-section">
        <div class="drawer-section-title">top countries</div>
        ${Object.entries(stats.by_country).slice(0, 15).map(([k,v]) =>
          `<div class="drawer-row"><span class="k">${escapeHtml(k)}</span><span class="v">${fmt(v)}</span></div>`
        ).join('')}
      </div>

      <div class="drawer-section">
        <div class="drawer-section-title">proxies</div>
        ${Object.entries(health.proxies).map(([n, p]) =>
          `<div class="drawer-row"><span class="k"><span class="health-dot ${p.online ? 'online' : 'offline'}"></span>${n}</span><span class="v ${p.online ? 'ok' : 'bad'}">${p.online ? '● online' : '○ offline'}${p.data?.count ? ' (' + fmt(p.data.count) + ')' : ''}</span></div>`
        ).join('')}
      </div>

      <div class="drawer-section">
        <div class="drawer-section-title">services</div>
        <div class="drawer-row"><span class="k"><span class="health-dot ${health.reaper?.exists ? 'online' : 'offline'}"></span>reaper</span><span class="v ${health.reaper?.exists ? 'ok' : 'bad'}">${health.reaper?.exists ? '● pid file' : '○ stopped'}</span></div>
        <div class="drawer-row"><span class="k"><span class="health-dot ${health.token_daemon?.exists ? 'online' : 'offline'}"></span>token daemon</span><span class="v ${health.token_daemon?.exists ? 'ok' : 'bad'}">${health.token_daemon?.exists ? '● pid file' : '○ stopped'}</span></div>
        <div class="drawer-row"><span class="k">csv mtime</span><span class="v">${new Date(stats.csv_mtime * 1000).toLocaleString()}</span></div>
      </div>`;
  } catch (e) {
    document.getElementById('statsBody').innerHTML = `<div style="color:var(--err);padding:20px">${e.message}</div>`;
  }
}

// ==================== SEARCH RESULTS POPUP ====================
function showSearchResults(r) {
  let popup = document.getElementById('searchPopup');
  if (popup) popup.remove();
  popup = document.createElement('div');
  popup.id = 'searchPopup';
  popup.className = 'search-suggestions';
  popup.style.cssText = 'position:fixed;top:56px;left:50%;transform:translateX(-50%);width:600px;max-width:90vw;z-index:200;background:var(--bg-1);border:1px solid var(--accent);max-height:50vh;overflow-y:auto;';
  popup.innerHTML = `
    <div style="padding:12px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;">
      <div>
        <div style="font-family:var(--font-mono);font-size:10px;letter-spacing:0.15em;color:var(--accent);text-transform:uppercase;">${r.intent} · ${r.count} results</div>
        <div style="font-size:13px;color:var(--text);margin-top:4px;">${escapeHtml(r.explanation || '')}</div>
      </div>
      <button class="icon-btn" id="closePopup">×</button>
    </div>
    ${(r.results || []).slice(0, 30).map(c => `
      <div class="search-suggestion" data-idx="${c.idx}" style="padding:10px 12px;border-bottom:1px solid var(--border-faint);cursor:pointer;display:flex;align-items:center;gap:8px;">
        <span class="search-suggestion-flag">${flagEmoji(c.country)}</span>
        <span style="flex:1">
          <div style="font-weight:600;">${escapeHtml(c.name || '')}</div>
          <div style="font-size:11px;color:var(--text-dim);">${escapeHtml([c.city, c.region, c.country].filter(Boolean).join(' › '))} · ${(c.type || '').toUpperCase()}</div>
        </span>
      </div>
    `).join('')}`;
  document.body.appendChild(popup);
  document.getElementById('closePopup').addEventListener('click', () => popup.remove());
  popup.querySelectorAll('.search-suggestion').forEach(el => {
    el.addEventListener('click', () => {
      const cam = state.cams.find(c => c.idx == el.dataset.idx);
      if (cam) { openDetail(cam); popup.remove(); }
      else {
        // AI result not in current loaded set — fetch it
        Api.cam(el.dataset.idx).then(c => openDetail(c));
        popup.remove();
      }
    });
  });
  setTimeout(() => {
    function closePopup(e) {
      if (!popup.contains(e.target) && e.target !== search) {
        popup.remove();
        document.removeEventListener('click', closePopup, true);
        document.removeEventListener('keydown', onEsc, true);
      }
    }
    function onEsc(e) {
      if (e.key === 'Escape') {
        popup.remove();
        document.removeEventListener('click', closePopup, true);
        document.removeEventListener('keydown', onEsc, true);
      }
    }
    document.addEventListener('click', closePopup, true);
    document.addEventListener('keydown', onEsc, true);
  }, 100);
}

// ==================== FILTERS UI ====================
function setupFilters() {
  // Search (AI smart intent OR FTS5 server-side)
  const search = document.getElementById('searchInput');
  let searchT;
  search.addEventListener('input', () => {
    clearTimeout(searchT);
    searchT = setTimeout(async () => {
      const q = search.value.trim();
      state.filter.q = q;
      if (q.length >= 3) {
        // First, check AI smart intent (coords, IPs, near X)
        try {
          const r = await Api.aiSearch(q);
          if (r.intent && r.intent !== 'empty' && r.intent !== 'keyword') {
            showSearchResults(r);
            saveState();
            writeUrlParams();
            return;
          }
        } catch {}
      }
      // Otherwise, server-side FTS5 search
      await reloadCams();
      saveState();
      writeUrlParams();
    }, 400);
  });

  // Type chips
  document.querySelectorAll('.chip[data-type]').forEach(c => {
    c.addEventListener('click', async () => {
      document.querySelectorAll('.chip[data-type]').forEach(x => x.classList.remove('active'));
      c.classList.add('active');
      state.filter.type = c.dataset.type;
      await reloadCams();
      saveState();
      writeUrlParams();
    });
  });

  // Visibility chips (public / private / unknown — exact match server-side)
  document.querySelectorAll('.chip[data-vis]').forEach(c => {
    c.addEventListener('click', async () => {
      document.querySelectorAll('.chip[data-vis]').forEach(x => x.classList.remove('active'));
      c.classList.add('active');
      state.filter.vis = c.dataset.vis;
      await reloadCams();
      saveState();
      writeUrlParams();
    });
  });

  // Country dropdown
  document.getElementById('countryFilter').addEventListener('change', async (e) => {
    state.filter.country = e.target.value;
    state.filter.region = ''; state.filter.city = '';
    document.getElementById('regionFilter').innerHTML = '<option value="">all regions</option>';
    document.getElementById('cityFilter').innerHTML = '<option value="">all cities</option>';
    document.getElementById('regionFilter').disabled = !e.target.value;
    document.getElementById('cityFilter').disabled = true;
    if (e.target.value) {
      try {
        const regions = await Api.regions(e.target.value);
        const sel = document.getElementById('regionFilter');
        regions.slice(0, 500).forEach(r => {
          const o = document.createElement('option'); o.value = r; o.textContent = r;
          sel.appendChild(o);
        });
      } catch {}
    }
    await reloadCams();
    saveState();
    writeUrlParams();
  });

  document.getElementById('regionFilter').addEventListener('change', async (e) => {
    state.filter.region = e.target.value;
    state.filter.city = '';
    document.getElementById('cityFilter').innerHTML = '<option value="">all cities</option>';
    document.getElementById('cityFilter').disabled = !e.target.value;
    if (e.target.value) {
      try {
        const cities = await Api.cities(state.filter.country, e.target.value);
        const sel = document.getElementById('cityFilter');
        cities.slice(0, 500).forEach(c => {
          const o = document.createElement('option'); o.value = c; o.textContent = c;
          sel.appendChild(o);
        });
      } catch {}
    }
    await reloadCams();
    saveState();
    writeUrlParams();
  });

  document.getElementById('cityFilter').addEventListener('change', async (e) => {
    state.filter.city = e.target.value;
    await reloadCams();
    saveState();
    writeUrlParams();
  });

  // Sort
  document.getElementById('sortFilter').addEventListener('change', async (e) => {
    state.filter.sort = e.target.value;
    saveState();
    writeUrlParams();
    // Reload cams with new sort
    await reloadCams();
  });

  // Tabs
  document.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
      t.classList.add('active');
      state.view = t.dataset.view;
      switchView(state.view);
      saveState();
      writeUrlParams();
    });
  });

  // Grid size button
  document.getElementById('gridSizeBtn').addEventListener('click', () => {
    applyGridSize(state.gridSize === 'compact' ? 'wide' : 'compact');
  });

  // Shuffle button — re-samples with new seed
  document.getElementById('shuffleBtn').addEventListener('click', () => {
    if (state.view === 'map' || state.view === 'globe') {
      shuffleSeed();
    } else {
      shuffleCam();
    }
  });

  // Pause all
  document.getElementById('pauseBtn').addEventListener('click', pauseAll);

  // Settings drawer
  const settingsDrawer = document.getElementById('settingsDrawer');
  document.getElementById('settingsBtn').addEventListener('click', () => {
    // Populate inputs from current settings
    document.getElementById('setRandomMode').value = state.settings.randomMode;
    document.getElementById('setMapMode').value = state.settings.mapMode;
    document.getElementById('setShuffleSec').value = state.settings.shuffleSec;
    document.getElementById('setPageSize').value = state.settings.pageSize;
    document.getElementById('setMapPoints').value = state.settings.mapPoints;
    document.getElementById('setDefaultType').value = state.settings.defaultType;
    document.getElementById('setGlobe3D').checked = state.settings.showGlobe3D;
    document.getElementById('setHeatmap').checked = state.settings.heatmap;
    document.getElementById('setLabels').checked = state.settings.labels;
    settingsDrawer.classList.add('open');
  });
  document.getElementById('settingsClose').addEventListener('click', () => {
    settingsDrawer.classList.remove('open');
  });
  document.getElementById('setSave').addEventListener('click', () => {
    state.settings.randomMode = document.getElementById('setRandomMode').value;
    state.settings.mapMode = document.getElementById('setMapMode').value;
    state.settings.shuffleSec = parseInt(document.getElementById('setShuffleSec').value || 0, 10);
    state.settings.pageSize = parseInt(document.getElementById('setPageSize').value || 60, 10);
    state.settings.mapPoints = parseInt(document.getElementById('setMapPoints').value || 3000, 10);
    state.settings.defaultType = document.getElementById('setDefaultType').value;
    state.settings.showGlobe3D = document.getElementById('setGlobe3D').checked;
    state.settings.heatmap = document.getElementById('setHeatmap').checked;
    state.settings.labels = document.getElementById('setLabels').checked;
    saveSettings();
    setupShuffleTimer();
    // Apply default type if changed
    const newType = state.settings.defaultType;
    if (newType !== state.filter.type) {
      const chip = document.querySelector(`.chip[data-type="${newType}"]`);
      if (chip) chip.click();
    }
    // Show/hide 3D globe tab
    const tab = document.querySelector('.tab[data-view="globe"]');
    if (tab) tab.style.display = state.settings.showGlobe3D ? '' : 'none';
    settingsDrawer.classList.remove('open');
    toast('Settings saved', 'success');
    // Re-sample current views if modes changed
    state.seed = Math.floor(Math.random() * 1e9);
    if (window.__maplibre) loadMapPoints();
    if (state.view === 'grid') reloadCams();
  });
  document.getElementById('setReset').addEventListener('click', () => {
    localStorage.removeItem(SETTINGS_KEY);
    state.settings = { ...DEFAULT_SETTINGS };
    saveSettings();
    document.getElementById('settingsBtn').click();
    toast('Settings reset', 'info');
  });

  setupShuffleTimer();

  // Keyboard shortcuts (consolidated)
  document.addEventListener('keydown', (e) => {
    const tag = document.activeElement?.tagName;
    const inForm = ['INPUT','TEXTAREA','SELECT'].includes(tag);
    if (e.key === 'Escape') {
      closeDetail();
      const drawer = document.getElementById('statsDrawer');
      if (drawer.classList.contains('open')) drawer.classList.remove('open');
      const popup = document.getElementById('searchPopup');
      if (popup) popup.remove();
      return;
    }
    if (!inForm && e.key === '/') {
      e.preventDefault();
      search.focus();
      search.select();
      return;
    }
    if (!inForm && e.key === 's') {
      shuffleCam();
      return;
    }
    if (!inForm && e.key === 'p') {
      pauseAll();
      return;
    }
    if (e.key === 'g' && e.ctrlKey) {
      e.preventDefault();
      applyGridSize(state.gridSize === 'compact' ? 'wide' : 'compact');
      return;
    }
  });
}

// ==================== HELPERS ====================
function loadScript(src) {
  return new Promise((res, rej) => {
    if ([...document.scripts].some(s => s.src === src)) return res();
    const s = document.createElement('script');
    s.src = src;
    s.onload = res;
    s.onerror = rej;
    document.head.appendChild(s);
  });
}

// ==================== DATA LOADING ====================
async function reloadCams() {
  setIntro('loading cams');
  try {
    // First, fetch authoritative counts from /api/stats
    try {
      const stats = await Api.stats();
      setStats(stats.by_type || {}, stats.live, stats.by_visibility || {}, stats.by_visibility_live || {});
    } catch {}

    // Load cams matching current filters (server-side)
    const params = {
      type: state.filter.type,
      visibility: state.filter.vis,
      country: state.filter.country,
      region: state.filter.region,
      city: state.filter.city,
      q: state.filter.q,
      sort: state.filter.sort,
    };
    const all = [];
    let totalMatches = null;

    // Random / stratified: single shot (no offset needed)
    if (state.settings.randomMode === 'random' || state.settings.randomMode === 'stratified') {
      // Single shot — request 1500 random cams (plenty for the visible window).
      // 1500 = ~50 visible tiles worth of margin when scrolling, much faster than 5000.
      // The pool size is shown via r.count.
      const LIM = 1500;
      const r = await Api.cams({ ...params, mode: state.settings.randomMode, seed: state.seed, limit: LIM });
      totalMatches = r.count;
      all.push(...(r.cams || []));
      setIntro(`loaded ${all.length.toLocaleString()} random cams of ${totalMatches.toLocaleString()} matching filters (seed ${state.seed})`);
    } else {
      // Default paginated load
      let offset = 0;
      const PAGE = 10000;
      const INITIAL_CAP = 20000;  // cap at 20k for faster initial load
      while (true) {
        const r = await Api.cams({ ...params, limit: PAGE, offset });
        if (!r.cams || r.cams.length === 0) break;
        if (totalMatches == null) totalMatches = r.count;
        all.push(...r.cams);
        if (r.cams.length < PAGE) break;
        offset += PAGE;
        if (all.length >= INITIAL_CAP) break;
        setIntro(`loading cams · ${all.length.toLocaleString()}${totalMatches ? ` of ${totalMatches.toLocaleString()}` : ''}`);
      }
    }
    state.cams = all;
    state.totalMatches = totalMatches;
    applyFilter();
  } catch (e) {
    toast('Failed to load cams: ' + e.message, 'error');
  }
}

function setIntro(msg) {
  const el = document.getElementById('introDetail');
  if (el) el.textContent = msg;
}

// ==================== GEOLOCATION (for distance) ====================
function getUserLocation() {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(
    pos => { state.userLat = pos.coords.latitude; state.userLon = pos.coords.longitude; },
    () => { /* ignore */ },
    { timeout: 5000, maximumAge: 60_000 }
  );
}

// ==================== DISCLAIMER ====================
function setupDisclaimer() {
  const root = document.getElementById('disclaimer');
  const checks = ['cbResearch', 'cbLegal', 'cbNoHarm'].map(id => document.getElementById(id));
  const acceptBtn = document.getElementById('btnAccept');
  const declineBtn = document.getElementById('btnDecline');
  const updateState = () => {
    const allChecked = checks.every(c => c.checked);
    acceptBtn.classList.toggle('ready', allChecked);
    acceptBtn.disabled = !allChecked;
  };
  checks.forEach(c => c.addEventListener('change', updateState));
  acceptBtn.addEventListener('click', () => {
    localStorage.setItem('eli6-disclaimer-accepted', '1');
    root.classList.add('hide');
    setTimeout(() => root.remove(), 500);
  });
  declineBtn.addEventListener('click', () => {
    document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;text-align:center;font-family:monospace;color:#888;padding:40px">You declined. Reload to reconsider.</div>';
  });
  if (localStorage.getItem('eli6-disclaimer-accepted') === '1') {
    root.classList.add('hide');
    setTimeout(() => root.remove(), 100);
  }
}

// ==================== BOOT ====================
async function boot() {
  const intro = document.getElementById('intro');
  setupDisclaimer();
  getUserLocation();

  // Apply persisted state to UI
  document.getElementById('searchInput').value = state.filter.q;
  document.querySelectorAll('.chip[data-type]').forEach(c => c.classList.toggle('active', (c.dataset.type || '') === state.filter.type));
  document.querySelectorAll('.chip[data-vis]').forEach(c => c.classList.toggle('active', (c.dataset.vis || '') === state.filter.vis));
  document.getElementById('sortFilter').value = state.filter.sort || 'idx';

  // Init virtual grid
  const tW = state.gridSize === 'compact' ? 320 : 460;
  const tH = state.gridSize === 'compact' ? 230 : 320;
  state.vgrid = new VirtualGrid(
    document.getElementById('gridCanvas'),
    document.getElementById('gridScroll'),
    {
      tileWidth: tW,
      tileHeight: tH,
      gap: 8,
      render: renderTile,
      // CRITICAL: VirtualGrid calls this when a tile falls out of its
      // visible range. We forward to the tile's own _disposeTile (set
      // up in renderTile) which fully destroys the player and
      // disconnects the IntersectionObserver.
      dispose: (node, cam, idx) => {
        if (node && node._disposeTile) {
          try { node._disposeTile(); } catch {}
        }
      },
      onNearEnd: () => lazyLoadMore(),
    }
  );

  // Lazy-load more when scrolling near end
  let lazyLoading = false;
  async function lazyLoadMore() {
    if (lazyLoading) return;
    if (state.cams.length >= state.totalMatches) return;
    lazyLoading = true;
    try {
      const offset = state.cams.length;
      const r = await Api.cams({
        type: state.filter.type,
        country: state.filter.country,
        region: state.filter.region,
        city: state.filter.city,
        q: state.filter.q,
        sort: state.filter.sort,
        limit: 10000,
        offset,
      });
      if (r.cams && r.cams.length) {
        state.cams.push(...r.cams);
        applyFilter();
        toast(`+${r.cams.length.toLocaleString()} more cams (${state.cams.length.toLocaleString()} of ${state.totalMatches?.toLocaleString() || '?'})`, 'info', 2000);
      }
    } catch {}
    lazyLoading = false;
  }

  // Expose loadAll for "load all 200k" button
  window.__loadAllCams = async function() {
    if (state.cams.length >= state.totalMatches) {
      toast('All cams already loaded', 'info', 2000);
      return;
    }
    const start = state.cams.length;
    const total = state.totalMatches;
    const toLoad = total - start;
    toast(`Loading ${toLoad.toLocaleString()} more cams...`, 'info', 2000);
    let offset = start;
    let loaded = 0;
    const CHUNK = 25000;
    while (offset < total) {
      const remaining = total - offset;
      const lim = Math.min(CHUNK, remaining);
      try {
        const r = await Api.cams({
          type: state.filter.type,
          country: state.filter.country,
          region: state.filter.region,
          city: state.filter.city,
          q: state.filter.q,
          sort: state.filter.sort,
          limit: lim,
          offset,
        });
        if (!r.cams || !r.cams.length) break;
        state.cams.push(...r.cams);
        loaded += r.cams.length;
        applyFilter();
        toast(`loaded ${loaded.toLocaleString()} / ${toLoad.toLocaleString()}`, 'info', 1000);
        offset += lim;
      } catch (e) {
        toast('load failed: ' + e.message, 'error');
        break;
      }
    }
    toast(`✓ all ${state.cams.length.toLocaleString()} cams loaded`, 'success', 2000);
  };

  setupFilters();

  // Load countries dropdown
  try {
    setIntro('loading countries');
    const countries = await Api.countries();
    const sel = document.getElementById('countryFilter');
    countries.slice(0, 500).forEach(c => {
      const o = document.createElement('option');
      o.value = c; o.textContent = c;
      sel.appendChild(o);
    });
  } catch (e) {
    console.warn('countries load failed', e);
  }

  // Apply URL filters
  if (state.filter.country) document.getElementById('countryFilter').value = state.filter.country;
  if (state.filter.region) {
    document.getElementById('regionFilter').disabled = false;
    document.getElementById('regionFilter').value = state.filter.region;
  }
  if (state.filter.city) {
    document.getElementById('cityFilter').disabled = false;
    document.getElementById('cityFilter').value = state.filter.city;
  }

  // Load cams
  setIntro('loading cams');
  await reloadCams();

  // Init header stats
  try {
    const stats = await Api.stats();
    document.getElementById('statTotal').textContent = fmt(stats.total);
    document.getElementById('statLive').textContent = fmt(stats.live);
  } catch {}

  // Restore view
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === state.view));
  if (state.view !== 'grid') switchView(state.view);

  // Restore cam detail
  if (_url.cam) {
    setTimeout(async () => {
      let cam = state.cams.find(c => c.idx == _url.cam);
      if (!cam) {
        try { cam = await Api.cam(_url.cam); } catch {}
      }
      if (cam) openDetail(cam);
    }, 200);
  }

  // Hide intro
  setIntro('ready');
  intro.classList.add('hide');
  setTimeout(() => intro.remove(), 600);
}

boot().catch(e => {
  console.error('boot error', e);
  document.getElementById('intro').textContent = 'BOOT ERROR · ' + e.message;
});