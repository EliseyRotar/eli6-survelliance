// api.js — fetch wrapper for the Flask backend
const API = '';

async function fetchJSON(path, params = {}) {
  const url = new URL(path, window.location.origin);
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v);
  }
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) {
    const err = new Error(`${r.status} ${r.statusText}`);
    err.status = r.status;
    throw err;
  }
  return r.json();
}

export const Api = {
  cams: (params = {}) => fetchJSON('/api/cams', params),
  cam: (idx) => fetchJSON(`/api/cams/${idx}`),
  stats: () => fetchJSON('/api/stats'),
  health: () => fetchJSON('/api/health'),
  geojson: (params = {}) => fetchJSON('/api/geojson', { ...params, live: 1 }),
  countries: () => fetchJSON('/api/countries'),
  regions: (country) => fetchJSON('/api/regions', { country }),
  cities: (country, region) => fetchJSON('/api/cities', { country, region }),

  // AI endpoints
  aiSnapshot: () => fetchJSON('/api/ai/snapshot'),
  aiInsights: () => fetchJSON('/api/ai/insights'),
  aiSimilar: (idx) => fetchJSON(`/api/ai/similar/${idx}`),
  aiSearch: (q) => fetchJSON('/api/ai/search', { q }),
  aiHotspots: () => fetchJSON('/api/ai/hotspots'),

  // Proxies
  proxyMjpeg: (url) => `/api/proxy/mjpeg?u=${encodeURIComponent(url)}`,
  proxyHls: (url) => `/api/proxy/hls?u=${encodeURIComponent(url)}`,
};