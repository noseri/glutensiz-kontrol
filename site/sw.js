/* Glutensiz Kontrol — çevrimdışı çalışma
 * Sayfa, liste ve analiz raporu listesi (index.html, data.json, reports.json): önce ağ; ağ yoksa ya da 4 sn'de yanıt gelmezse telefondaki son kopya.
 * Yazı tipleri ve simgeler: önce önbellek.
 */
const CACHE = 'gk-v2';
const SHELL = [
  './index.html',
  './data.json',
  './reports.json',
  './manifest.webmanifest',
  './fonts/manrope-latin.woff2',
  './fonts/manrope-latin-ext.woff2',
  './icons/icon-192.png',
  './icons/apple-touch-icon.png'
];
const NET_TIMEOUT = 4000;

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k.startsWith('gk-') && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  const fresh = req.mode === 'navigate' || /\/(index\.html|data\.json|reports\.json)?$/.test(url.pathname);
  e.respondWith(fresh ? networkFirst(e, req, url) : cacheFirst(req));
});

function cacheKey(req, url) {
  if (req.mode === 'navigate' || url.pathname.endsWith('/') || url.pathname.endsWith('/index.html')) return './index.html';
  if (url.pathname.endsWith('/data.json')) return './data.json';
  return url.pathname.endsWith('/reports.json') ? './reports.json' : req;
}

async function networkFirst(e, req, url) {
  const cache = await caches.open(CACHE);
  const key = cacheKey(req, url);
  const net = (req.mode === 'navigate' ? fetch(req) : fetch(url.href, {cache: 'no-cache'}))
    .then(res => {
      if (res.ok) cache.put(key, res.clone());
      return res;
    });
  // ağ geç kalırsa önbellekten yanıt ver, ama indirme bitince kopyayı yine güncelle
  e.waitUntil(net.catch(() => {}));
  let timer;
  const timeout = new Promise(resolve => { timer = setTimeout(() => resolve(null), NET_TIMEOUT); });
  let res = null;
  try {
    res = await Promise.race([net, timeout]);
  } catch (err) {
    res = null;
  }
  clearTimeout(timer);
  if (res && res.ok) return res;
  const hit = await cache.match(key, {ignoreSearch: true});
  if (hit) return markOffline(hit);
  return res || net;  // önbellekte yoksa ağın yanıtını bekle
}

async function markOffline(res) {
  const headers = new Headers(res.headers);
  headers.set('x-gk-offline', '1');
  return new Response(await res.blob(), {status: res.status, statusText: res.statusText, headers});
}

async function cacheFirst(req) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(req, {ignoreSearch: true});
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) cache.put(req, res.clone());
  return res;
}
