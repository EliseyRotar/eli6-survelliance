// player.js - HLS / YouTube / MJPEG / MP4 dispatcher with offline overlay
const PROXY_FL511   = 'http://localhost:8770';
const PROXY_SKYLINE = 'http://localhost:8771';

// Live URL map: cam_idx -> { live_url, image_url, source }
// Loaded async at module init from /api/live_mappings
const LIVE_MAP = new Map();
let _liveMapLoaded = false;
let _liveMapLoading = null;
async function ensureLiveMap() {
  if (_liveMapLoaded) return LIVE_MAP;
  if (_liveMapLoading) return _liveMapLoading;
  _liveMapLoading = (async () => {
    try {
      const r = await fetch('/api/live_mappings');
      const j = await r.json();
      const mappings = j.mappings || {};
      for (const [k, v] of Object.entries(mappings)) {
        LIVE_MAP.set(Number(k), v);
      }
      _liveMapLoaded = true;
      console.log(`[player] Loaded ${LIVE_MAP.size} live URL mappings`);
    } catch (e) {
      console.warn('[player] Failed to load live mappings:', e.message);
      _liveMapLoaded = true; // don't retry forever
    }
    return LIVE_MAP;
  })();
  return _liveMapLoading;
}
// Kick off loading on module init
ensureLiveMap();

function autostradeToMp4(jpegUrl) {
  // /video-frames/dt{N}/{uuid}-{viewnum}-{frameidx}.jpg  ->  /video-mp4_hq/dt{N}/{uuid}-{viewnum}.mp4
  // /video-frames/dt{N}/{uuid}-{viewnum}-thumb.jpg        ->  /video-mp4_hq/dt{N}/{uuid}-{viewnum}.mp4
  if (!jpegUrl || !jpegUrl.includes('video.autostrade.it/video-frames/')) return null;
  const m = jpegUrl.match(/^(https?:\/\/video\.autostrade\.it)\/video-frames\/(dt[0-9]+|[a-z]+)\/(.+?)(-thumb)?(-\d+)?\.jpg$/i);
  if (!m) return null;
  const [, base, hw, uuid] = m;
  return `${base}/video-mp4_hq/${hw}/${uuid}.mp4`;
}

// kcscout RTSP -> HLS streamlock.net path.
// rtsp://5fca316e7c40f.streamlock.net:1935/live-secure/customInstance/{ID}-LQ.stream
// -> file path = live-secure/customInstance/{ID}-LQ.stream (token fetched via API)
function kcscoutToHls(rtspUrl, kcscoutId) {
  if (!rtspUrl) return null;
  // Match the RTSP URL pattern
  let m = rtspUrl.match(/^rtsp:\/\/[^/]+\/(live-(?:secure|interleave)\/customInstance\/[^\s]+\.stream)/i);
  if (m) return m[1];
  // Also support already-built streamlock URLs
  m = rtspUrl.match(/^https?:\/\/[^/]+\/(live-(?:secure|interleave)\/customInstance\/[^\s]+\.stream)/i);
  if (m) return m[1];
  // Or if kcscout_id present, build it manually
  if (kcscoutId) {
    return `live-secure/customInstance/${kcscoutId}-LQ.stream`;
  }
  return null;
}

function guessStreamType(url) {
  if (!url) return 'other';
  if (/\.m3u8/i.test(url)) return 'hls';
  if (/\.mp4/i.test(url)) return 'mp4';
  if (/\.mpd/i.test(url)) return 'dash';
  if (/\.jpe?g/i.test(url)) return 'mjpeg';
  return 'other';
}

// Route external HLS/MP4 streams through /api/proxy to bypass CORS.
// Same-origin (dashboard itself) and already-proxied URLs go through directly.
function maybeProxy(url, type) {
  if (!url) return url;
  // Already proxied? Same-origin? No CORS issue?
  if (url.startsWith('/api/') || url.startsWith('http://localhost:') || url.startsWith('http://127.0.0.1:')) {
    return url;
  }
  if (type === 'hls' || type === 'mp4' || type === 'dash') {
    return `/api/proxy/hls?u=${encodeURIComponent(url)}`;
  }
  return url;
}

export function buildStream(cam) {
  const u = cam.live || cam.url || '';
  const t = (cam.type || '').toLowerCase();
  if (!u) return { type: 'other', url: '' };

  // kcscout.net streams: RTSP URL, but actual stream is HLS at streamlock.net
  // Requires token from kcscout's DataProvider.asmx endpoint (IP-restricted).
  if (u.includes('streamlock.net') || (cam.host && cam.host.includes('streamlock')) || u.startsWith('rtsp://')) {
    const file = kcscoutToHls(u, cam.kcscout_id);
    if (file) {
      // We'll fetch token at click time; player handles kcscout_file specially
      return { type: 'hls', url: u, kcscout_file: file };
    }
  }

  // Skyline: always use proxy (static jpg -> hls via proxy)
  if (u.includes('skylinewebcams.com/live') && /\.jpg/i.test(u)) {
    return { type: 'hls', url: `${PROXY_SKYLINE}/skyline/${cam.idx}/stream.m3u8` };
  }

  // Digitraffic weathercam: static JPEG every 10min. Use slideshow mode (5 recent history frames).
  if (u.includes('weathercam.digitraffic.fi/') && /\.jpe?g/i.test(u)) {
    const m = u.match(/\/(C[0-9]+)\.jpe?g/i);
    if (m) {
      return { type: 'slideshow', presetId: m[1], url: `/api/digitraffic/slideshow/${m[1]}.json` };
    }
  }

  // Houston TranStar cams: server-side slideshow. Two patterns:
  //   - Local: houstontx cams via snapshots/cctv/{id}.jpg
  //   - Regional: houstontx regional cams via /cctv_construction/txdot/..._live_image.jpg
  // Both cycle through 1-6 historical frames at 1fps to simulate a live video feed.
  // Single-frame cams are just a refreshing still (3-5s).
  if (u.includes('houstontranstar.org/snapshots/cctv/') || u.includes('cctv_construction/txdot/')) {
    let queryUrl;
    if (u.includes('snapshots/cctv/')) {
      // Local cam: extract ID from path
      const m = u.match(/snapshots\/cctv\/(\d+)\.jpg/);
      if (m) {
        queryUrl = `/api/transtar/frames?cam_id=${m[1]}`;
      }
    } else if (u.includes('cctv_construction/txdot/')) {
      // Regional cam: pass full path
      const m = u.match(/(cctv_construction\/txdot\/[^?]+)/);
      if (m) {
        queryUrl = `/api/transtar/frames?path=${encodeURIComponent('/' + m[1])}`;
      }
    }
    if (queryUrl) {
      return { type: 'slideshow', url: queryUrl };
    }
  }

  // fl511 (divas.cloud) HLS via proxy using full URL (token in URL)
  if (u.includes('dis-se') && u.includes('divas.cloud')) {
    const params = new URLSearchParams({ u });
    // If we have a fl511 imageId, pass it so proxy can refresh on 401/404
    if (cam.fl511_id) params.set('cam_id', cam.fl511_id);
    return { type: 'hls', url: `${PROXY_FL511}/stream_url?${params.toString()}` };
  }

  // Autostrade.it: transform static JPEG URL to live MP4 (verified pattern)
  // Autostrade.it allows CORS for video, so no proxy needed
  const mp4 = autostradeToMp4(u);
  if (mp4) {
    return { type: 'mp4', url: mp4 };
  }

  // SATAP A4 Italian tollway webcams: short looping MP4 files overwritten
  // every ~30s on the origin server. Origin supports byte-range, but we
  // still proxy to avoid CORS preflight + to add Cache-Control.
  if (u.includes('satapweb.it') && /\.mp4/i.test(u)) {
    return { type: 'mp4', url: `/api/satap/proxy?u=${encodeURIComponent(u)}&t=${Date.now()}` };
  }

  // TV-catalog verified live URLs (loaded from /api/live_mappings)
  const live = LIVE_MAP.get(Number(cam.idx));
  if (live && live.live_url && live.live_url !== u) {
    const stype = guessStreamType(live.live_url);
    return { type: stype, url: maybeProxy(live.live_url, stype) };
  }

  // YouTube
  if (/youtube\.com|youtu\.be/.test(u)) {
    let vid = null;
    let m = u.match(/youtube\.com\/embed\/([\w-]+)/);
    if (m) vid = m[1];
    if (!vid) { m = u.match(/[?&]v=([\w-]+)/); if (m) vid = m[1]; }
    if (!vid) { m = u.match(/youtu\.be\/([\w-]+)/); if (m) vid = m[1]; }
    if (vid) return { type: 'youtube', vid };
    return { type: 'other', url: u };
  }

  // Standard fallbacks
  if (t === 'hls' || /\.m3u8/i.test(u)) return { type: 'hls', url: maybeProxy(u, 'hls') };
  if (t === 'mp4' || /\.mp4/i.test(u)) return { type: 'mp4', url: maybeProxy(u, 'mp4') };
  if (t === 'mjpeg' || /\.jpe?g/i.test(u)) return { type: 'mjpeg', url: u };
  return { type: 'other', url: u };
}

// Try to find a poster image for the cam. We have three strategies:
// 1. Pre-extracted ffmpeg poster via /api/poster/<idx> (instant load, 24h cache, 60s negative cache)
// 2. Direct file at /static/posters/<idx>.jpg (legacy path, used in case /api/poster isn't reachable)
// 3. Fallback: /api/proxy/img with .jpg variant of the HLS path
function guessPosterUrl(cam, stream) {
  if (!stream || !stream.url) return null;
  // Don't try for mjpeg/youtube (they have their own rendering)
  if (stream.type === 'mjpeg' || stream.type === 'youtube') return null;
  // 1. Server endpoint: returns 404 with negative cache if file missing
  if (cam.idx) {
    return `/api/poster/${cam.idx}?t=${Date.now()}`;
  }
  // 2. Fallback: try .jpg variant of the HLS path
  const url = stream.url;
  let origUrl = url;
  if (url.startsWith('/api/proxy/hls?u=')) {
    try {
      const u = new URL(url, window.location.origin);
      origUrl = decodeURIComponent(u.searchParams.get('u') || '');
    } catch { return null; }
  }
  if (!origUrl || !origUrl.startsWith('http')) return null;
  if (/\.m3u8(\?|$)/i.test(origUrl)) {
    const baseUrl = origUrl.replace(/\.m3u8(\?.*)?$/, '');
    return `/api/proxy/img?u=${encodeURIComponent(baseUrl + '.jpg')}&t=${Date.now()}`;
  }
  if (/\.jpe?g/i.test(origUrl) || /mjpeg/i.test(origUrl)) {
    return null;
  }
  return null;
}

export function attachPlayback(wrap, statusEl, cam, stream, onStateChange) {
  const idx = cam.idx;

  // Set a static image as poster (background) while video loads
  // Many HLS sources have a thumbnail at /path/index.jpg or similar
  const posterUrl = guessPosterUrl(cam, stream);
  let posterImg = null;
  if (posterUrl) {
    posterImg = new Image();
    posterImg.alt = '';
    posterImg.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#000;z-index:0;';
    posterImg.loading = 'lazy';
    wrap.appendChild(posterImg);
    // The poster sits behind the video. As soon as the video's first
    // frame is displayed, the video covers the poster visually.
    posterImg.onload = () => {
      // poster is in DOM; if the player never gets to LIVE, the poster
      // remains as the visible image.
    };
    posterImg.onerror = () => {
      try { posterImg.remove(); } catch {}
      posterImg = null;
    };
    posterImg.src = posterUrl;
  }

  function setState(state) {
    statusEl.textContent = state.label;
    statusEl.className = `tile-status ${state.cls}`;
    if (onStateChange) onStateChange(state);
    // Toggle shimmer: remove loading class on any non-loading state
    // so the user sees the shimmer only while truly connecting.
    const media = wrap.closest('.tile-media');
    if (media) {
      if (state.cls === 'loading') {
        media.classList.add('loading');
        media.classList.remove('has-video');
      } else {
        media.classList.remove('loading');
        if (state.cls === 'live') {
          // Live video is playing — hide the placeholder
          media.classList.add('has-video');
        } else {
          media.classList.remove('has-video');
        }
      }
    }
    if (state.cls === 'error' || state.cls === 'offline') {
      // Keep poster visible on error so user still sees something
      if (posterImg) {
        try { posterImg.style.opacity = '1'; } catch {}
      }
      showOfflineOverlay(wrap, state.label, () => {
        hideOfflineOverlay(wrap);
        // Re-trigger by reloading iframe/img
        if (state.retry) state.retry();
      });
    } else if (state.cls === 'live' || state.cls === 'loading') {
      // Once LIVE, hide the poster (video will cover it)
      if (state.cls === 'live' && posterImg) {
        setTimeout(() => {
          if (posterImg && posterImg.parentNode) {
            try { posterImg.style.opacity = '0'; posterImg.style.transition = 'opacity 0.4s'; } catch {}
            setTimeout(() => { try { posterImg?.remove(); } catch {} }, 500);
          }
        }, 1500);  // wait until video has been playing for 1.5s
      }
      hideOfflineOverlay(wrap);
    }
  }

  setState({ label: '...', cls: 'loading' });
  const HARD_TIMEOUT_MS = 8000;
  let disposed = false;

  if (stream.type === 'youtube') {
    const iframe = document.createElement('iframe');
    iframe.src = `https://www.youtube.com/embed/${stream.vid}?autoplay=1&mute=1&playsinline=1&rel=0&modestbranding=1`;
    iframe.allow = 'autoplay; encrypted-media; fullscreen';
    iframe.allowFullscreen = true;
    iframe.style.cssText = 'width:100%;height:100%;border:0;background:#000;';
    iframe.addEventListener('load', () => {
      if (!disposed) setState({ label: 'YT', cls: 'live' });
    }, { once: true });
    iframe.addEventListener('error', () => {
      if (!disposed) setState({ label: 'OFF', cls: 'offline', retry: () => { iframe.src = iframe.src; } });
    }, { once: true });
    wrap.appendChild(iframe);
    // Hard timeout: YT iframes don't fire error for dead streams - assume live after 12s
    const tm = setTimeout(() => {
      if (!disposed && statusEl.classList.contains('loading')) {
        setState({ label: 'YT', cls: 'live' });
      }
    }, 12000);
    return {
      type: 'youtube',
      dispose: () => {
        clearTimeout(tm);
        disposed = true;
        hideOfflineOverlay(wrap);
        if (iframe.parentNode) iframe.remove();
      }
    };
  }

  if (stream.type === 'slideshow') {
    // Slideshow mode: cycle through 1-6 historical frames at 1 fps.
    // - Multi-frame (e.g. PTZ cams with frame buffer): real visible motion
    // - Single-frame (e.g. stills): just refreshes the same image; we still
    //   add visual interest via the refresh tick + indicator so user knows
    //   the stream is live (just updated slowly)
    const img = document.createElement('img');
    img.alt = cam.name || `cam ${idx}`;
    img.loading = 'lazy';
    img.style.cssText = 'width:100%;height:100%;object-fit:contain;background:#000;';
    let alive = true;
    let frames = [];
    let frameIdx = 0;
    let tick = null;
    let refreshTick = null;
    let errStreak = 0;
    let lastFetchUrl = '';
    const FRAME_MS = 800;  // 1.25 fps through frames (slightly faster)
    const REFRESH_MS = 30_000;  // re-fetch slideshow JSON every 30s (catches server updates faster)
    function showFrame(i) {
      if (!alive) return;
      const f = frames[i];
      if (!f) return;
      img.src = f.url + (f.url.includes('?') ? '&' : '?') + 't=' + Date.now();
    }
    function cycleFrame() {
      if (!alive || !frames.length) return;
      frameIdx = (frameIdx + 1) % frames.length;
      showFrame(frameIdx);
    }
    async function loadFrames() {
      if (!alive) return;
      try {
        const r = await fetch(stream.url, { cache: 'no-store' });
        const j = await r.json();
        const newFrames = j.frames || [];
        const newUrl = JSON.stringify(newFrames);
        // Only update frames if the URL list changed (avoids needless reloads)
        if (newUrl !== lastFetchUrl) {
          frames = newFrames;
          lastFetchUrl = newUrl;
          frameIdx = 0;
          if (frames.length === 0) {
            setState({ label: 'OFF', cls: 'offline' });
            return;
          }
          errStreak = 0;
          showFrame(0);
          // Show "SLIDE" if multiple frames, "STILL" if single frame
          setState({ label: frames.length > 1 ? 'SLIDE' : 'STILL', cls: 'live' });
        }
        // For single-frame cams, still re-fetch the image (with new cache buster)
        // to get the latest snapshot from the server
        if (frames.length === 1 && alive) {
          showFrame(0);
        }
      } catch (e) {
        errStreak++;
        if (errStreak >= 3) setState({ label: 'OFF', cls: 'offline' });
      }
    }
    wrap.appendChild(img);
    loadFrames();
    tick = setInterval(cycleFrame, FRAME_MS);
    refreshTick = setInterval(loadFrames, REFRESH_MS);
    return {
      dispose: () => {
        alive = false;
        if (tick) clearInterval(tick);
        if (refreshTick) clearInterval(refreshTick);
        if (img.parentNode) img.remove();
        hideOfflineOverlay(wrap);
      },
      type: 'slideshow',
    };
  }

  if (stream.type === 'mjpeg') {
    const img = document.createElement('img');
    img.alt = cam.name || `cam ${idx}`;
    img.loading = 'lazy';
    img.style.cssText = 'width:100%;height:100%;object-fit:contain;background:#000;';
    let alive = true;
    let n = 0;
    let tick = null;
    let errStreak = 0;
    let refreshMs = 3000;  // start at 3s to be kind to upstreams
    let loadToken = 0;  // detect hung requests
    const HUNG_TIMEOUT_MS = 12000;  // 12s hard timeout per request
    const MAX_RETRY = 3;  // auto-retry up to 3 times silently before showing OFFLINE
    function refresh() {
      if (!alive) return;
      const token = ++loadToken;
      // Hard timeout for hung requests
      const timeout = setTimeout(() => {
        if (alive && token === loadToken) {
          // Request hung - treat as error
          errStreak++;
          refreshMs = Math.min(30000, 3000 * Math.pow(2, Math.min(errStreak - 1, 4)));
          if (tick) { clearInterval(tick); tick = setInterval(refresh, refreshMs); }
          if (errStreak >= MAX_RETRY) {
            setState({ label: 'OFF', cls: 'offline', retry });
          } else {
            // Silent retry: keep showing "..." (no UI noise)
            setState({ label: '...', cls: 'loading' });
          }
        }
      }, HUNG_TIMEOUT_MS);
      const oldOnload = img.onload;
      const oldOnerror = img.onerror;
      img.onload = (...args) => { clearTimeout(timeout); if (oldOnload) oldOnload(...args); };
      img.onerror = (...args) => { clearTimeout(timeout); if (oldOnerror) oldOnerror(...args); };
      // bust cache to force re-fetch
      img.src = `/api/proxy/mjpeg?u=${encodeURIComponent(stream.url)}&n=${n++}&t=${Date.now()}`;
    }
    function retry() {
      errStreak = 0;
      refreshMs = 3000;
      if (tick) { clearInterval(tick); tick = setInterval(refresh, refreshMs); }
      hideOfflineOverlay(wrap);
      setState({ label: '...', cls: 'loading' });
      refresh();
    }
    img.onload = () => {
      if (disposed) return;
      if (img.naturalWidth < 32 || img.naturalHeight < 32) {
        errStreak++;
        refreshMs = Math.min(15000, 3000 * Math.pow(2, Math.min(errStreak - 1, 3)));
        if (tick) { clearInterval(tick); tick = setInterval(refresh, refreshMs); }
        if (errStreak >= MAX_RETRY) {
          setState({ label: 'OFF', cls: 'offline', retry });
        } else {
          // Silent retry: keep showing "..." 
          setState({ label: '...', cls: 'loading' });
        }
        return;
      }
      errStreak = 0;
      refreshMs = 3000;
      if (tick) { clearInterval(tick); tick = setInterval(refresh, refreshMs); }
      setState({ label: 'MJPG', cls: 'live' });
    };
    img.onerror = () => {
      if (disposed) return;
      errStreak++;
      // Exponential backoff: 3s, 6s, 12s, 24s, 30s cap
      refreshMs = Math.min(30000, 3000 * Math.pow(2, Math.min(errStreak - 1, 4)));
      if (tick) { clearInterval(tick); tick = setInterval(refresh, refreshMs); }
      if (errStreak >= MAX_RETRY) {
        setState({ label: 'OFF', cls: 'offline', retry });
      } else {
        // Silent retry: keep showing "..."
        setState({ label: '...', cls: 'loading' });
      }
    };
    wrap.appendChild(img);
    refresh();
    tick = setInterval(refresh, refreshMs);
    return { dispose: () => { alive = false; if (tick) clearInterval(tick); if (img.parentNode) img.remove(); hideOfflineOverlay(wrap); }, type: 'mjpeg' };
  }

  const video = document.createElement('video');
  video.muted = true;
  video.playsInline = true;
  video.autoplay = true;
  video.loop = true;
  video.controls = false;
  video.style.cssText = 'width:100%;height:100%;object-fit:contain;background:#000;';
  wrap.appendChild(video);

  let hls = null;
  let cleanup = () => {};
  let retryFn = null;

  function retry() {
    errStreak = 0;
    setState({ label: '...', cls: 'loading' });
    hideOfflineOverlay(wrap);
    if (stream.type === 'hls' && hls) {
      try { hls.destroy(); } catch {}
      hls = new Hls({ enableWorker: true, lowLatencyMode: false, maxBufferLength: 4, backBufferLength: 2, liveSyncDuration: 3, liveMaxLatencyDuration: 5 });
      hls.loadSource(stream.url);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (disposed) return;
        setState({ label: 'LIVE', cls: 'live' });
        video.play().catch(() => {});
      });
      hls.on(Hls.Events.ERROR, handleHlsError);
    } else {
      video.src = stream.url;
      video.load();
    }
  }
  retryFn = retry;

  let errStreak = 0;
  let fragErrorCount = 0;
  let lastFragErrorTime = 0;
  function handleHlsError(e, data) {
    if (disposed) return;
    // Track fragment errors. Only mark as ERR after MANY consecutive errors
    // so that brief network hiccups don't kill the player.
    if (data?.details === 'fragLoadError' || data?.details === 'fragLoadTimeOut') {
      const now = Date.now();
      // Reset counter if last error was a while ago
      if (now - lastFragErrorTime > 5000) {
        fragErrorCount = 0;
      }
      fragErrorCount++;
      lastFragErrorTime = now;
      if (fragErrorCount > 8) {
        // 8+ fragment errors in quick succession
        setState({ label: 'ERR', cls: 'error', retry: retryFn });
        try { hls.destroy(); } catch {}
        return;
      }
    }
    if (data?.fatal) {
      errStreak++;
      try { hls.destroy(); } catch {}
      if (errStreak >= 3) {
        setState({ label: 'OFF', cls: 'offline', retry: retryFn });
        return;
      }
      if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = stream.url;
        const onMeta = () => { if (!disposed) setState({ label: 'LIVE', cls: 'live' }); };
        const onErr = () => { if (!disposed) setState({ label: 'ERR', cls: 'error', retry: retryFn }); };
        video.addEventListener('loadedmetadata', onMeta, { once: true });
        video.addEventListener('error', onErr, { once: true });
      } else {
        setState({ label: 'ERR', cls: 'error', retry: retryFn });
      }
    }
  }

  if (stream.type === 'hls' && window.Hls && Hls.isSupported()) {
    // If kcscout: fetch token first, build full HLS URL with it
    async function startHls() {
      let playUrl = stream.url;
      if (stream.kcscout_file) {
        try {
          setState({ label: '...', cls: 'loading' });
          const r = await fetch(`/api/proxy/kcscout/token?file=${encodeURIComponent(stream.kcscout_file)}`);
          if (!r.ok) throw new Error('token endpoint ' + r.status);
          const tok = (await r.json()).token;
          // Build full URL: pick domain from the original URL (could be 5fca316e7c40f or 5fca96695ad7b)
          const domMatch = (stream.url || '').match(/streamlock\.net\/|https?:\/\/([a-z0-9]+\.streamlock\.net)\//i);
          // Fallback to common kcsout domain
          const domain = domMatch ? domMatch[1] : '5fca316e7c40f.streamlock.net';
          // Get app from kcscout_file (e.g. "live-secure/customInstance/...")
          const app = stream.kcscout_file.split('/')[0];
          playUrl = `https://${domain}/${app}/${stream.kcscout_file.split('/').slice(1).join('/')}/playlist.m3u8?${tok}`;
        } catch (e) {
          if (!disposed) setState({ label: 'AUTH', cls: 'offline', retry: retryFn });
          return;
        }
      }
      if (disposed) return;
      hls = new Hls({
        enableWorker: true,
        lowLatencyMode: false,
        maxBufferLength: 4,
        backBufferLength: 2,
        maxMaxBufferLength: 8,
        liveSyncDuration: 3,
        liveMaxLatencyDuration: 5,
      });
      hls.loadSource(playUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (disposed) return;
        setState({ label: 'LIVE', cls: 'live' });
        video.play().catch(() => {});
      });
      // "Stop after 30s playing" — bandwidth optimization (matches trafficvision.live).
      // After 30s of successful playback, pause the video and stop fetching segments.
      // The last frame stays visible. The video resumes on hover/click.
      let stopTimer = null;
      const onPlaying = () => {
        if (disposed || stopTimer) return;
        stopTimer = setTimeout(() => {
          if (disposed) return;
          try { hls.stopLoad(); } catch {}
          try { video.pause(); } catch {}
          // Mark as paused but keep tile looking live
          statusEl.textContent = 'LIVE';
          statusEl.className = 'tile-status live';
        }, 30000);
      };
      video.addEventListener('playing', onPlaying, { once: false });
      hls.on(Hls.Events.ERROR, (e, data) => {
        if (data?.fatal && !disposed) {
          // kcscout token may be IP-restricted — show AUTH
          if (stream.kcscout_file) {
            setState({ label: 'AUTH', cls: 'offline' });
          } else {
            handleHlsError(e, data);
          }
        }
      });
    }
    startHls();
    cleanup = () => { try { hls?.destroy(); } catch {} };
  } else if (stream.type === 'hls' && video.canPlayType('application/vnd.apple.mpegurl')) {
    // Safari native HLS — handle kcscout via token fetch first
    if (stream.kcscout_file) {
      (async () => {
        try {
          setState({ label: '...', cls: 'loading' });
          const r = await fetch(`/api/proxy/kcscout/token?file=${encodeURIComponent(stream.kcscout_file)}`);
          if (!r.ok) throw new Error('token ' + r.status);
          const tok = (await r.json()).token;
          const domMatch = (stream.url || '').match(/https?:\/\/([a-z0-9]+\.streamlock\.net)\//i);
          const domain = domMatch ? domMatch[1] : '5fca316e7c40f.streamlock.net';
          const app = stream.kcscout_file.split('/')[0];
          const playUrl = `https://${domain}/${stream.kcscout_file.split('/').slice(1).join('/')}/playlist.m3u8?${tok}`;
          if (!disposed) {
            video.src = playUrl;
            video.addEventListener('loadedmetadata', () => {
              if (!disposed) { setState({ label: 'LIVE', cls: 'live' }); video.play().catch(() => {}); }
            }, { once: true });
            video.addEventListener('error', () => {
              if (!disposed) setState({ label: 'AUTH', cls: 'offline' });
            }, { once: true });
          }
        } catch (e) {
          if (!disposed) setState({ label: 'AUTH', cls: 'offline', retry: retryFn });
        }
      })();
    } else {
      video.src = stream.url;
      video.addEventListener('loadedmetadata', () => {
        if (!disposed) { setState({ label: 'LIVE', cls: 'live' }); video.play().catch(() => {}); }
      }, { once: true });
      video.addEventListener('error', () => { if (!disposed) setState({ label: 'ERR', cls: 'error', retry: retryFn }); }, { once: true });
    }
  } else {
    video.src = stream.url;
    video.addEventListener('loadeddata', () => {
      if (!disposed) { setState({ label: 'MP4', cls: 'live' }); video.play().catch(() => {}); }
    }, { once: true });
    video.addEventListener('error', () => { if (!disposed) setState({ label: 'ERR', cls: 'error', retry: retryFn }); }, { once: true });
    // For SATAP cams (or any short looping MP4 that the server overwrites),
    // periodically re-fetch by appending a new timestamp. Otherwise the browser
    // would loop the same cached bytes and we'd see the same ~30s recording forever.
    if (u.includes('satapweb.it') && /\.mp4/i.test(u)) {
      const REFRESH_MS = 30_000;
      const r = setInterval(() => {
        if (disposed) { clearInterval(r); return; }
        const base = stream.url.replace(/[?&]t=\d+/, '');
        const sep = base.includes('?') ? '&' : '?';
        video.src = `${base}${sep}t=${Date.now()}`;
        video.play().catch(() => {});
      }, REFRESH_MS);
      const prevCleanup = cleanup;
      cleanup = () => { try { clearInterval(r); } catch {} prevCleanup(); };
    }
  }

  const tm = setTimeout(() => {
    if (!disposed && statusEl.classList.contains('loading')) {
      setState({ label: 'TIMEOUT', cls: 'offline', retry: retryFn });
      cleanup();
    }
  }, HARD_TIMEOUT_MS);

  return {
    type: stream.type,
    pause: () => {
      // Pause playback but keep buffer + connection alive.
      // Critical: do NOT call video.removeAttribute('src') or cleanup() here.
      try { video.pause(); } catch {}
      // For hls.js, optionally tell it to stop loading further segments but keep buffer
      if (hls) {
        try { hls.stopLoad = false; } catch {}
      }
    },
    resume: () => {
      // Resume from paused state — hls.js buffer is still valid
      if (disposed) return;
      try { video.play().catch(() => {}); } catch {}
    },
    dispose: () => {
      disposed = true;
      clearTimeout(tm);
      cleanup();
      try { video.pause(); } catch {}
      try { video.removeAttribute('src'); video.load(); } catch {}
      if (video.parentNode) video.remove();
      hideOfflineOverlay(wrap);
    }
  };
}

function showOfflineOverlay(wrap, label, onRetry) {
  if (!wrap) return;
  // Don't double-create
  if (wrap.querySelector('.offline-overlay')) {
    wrap.querySelector('.offline-overlay').dataset.label = label;
    return;
  }
  const overlay = document.createElement('div');
  overlay.className = 'offline-overlay';
  overlay.dataset.label = label;
  overlay.innerHTML = `
    <div class="offline-icon">⏻</div>
    <div class="offline-label">${label}</div>
    <button class="offline-retry" type="button" title="Retry">↻</button>
  `;
  overlay.style.cssText = 'position:absolute;inset:0;background:rgba(0,0,0,0.78);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;z-index:3;cursor:default;backdrop-filter:blur(2px);';
  overlay.addEventListener('click', (e) => {
    e.stopPropagation();
    if (e.target.closest('.offline-retry') && onRetry) onRetry();
  });
  wrap.appendChild(overlay);
}

function hideOfflineOverlay(wrap) {
  if (!wrap) return;
  const el = wrap.querySelector('.offline-overlay');
  if (el) el.remove();
}
