/* Glutensiz Kontrol — hızlı açılış ve çevrimdışı çalışma
 * Sayfa (index.html): önce ağ; 1,5 sn'de yanıt gelmezse telefondaki kopya. Yeni sürüm arka planda yine alınır;
 *   ancak stil ve betik dosyaları da önbelleğe alındıktan sonra saklanır (çevrimdışı açılışta sürümler karışmaz).
 * Stil ve betikler (app.css, js/*.js): adlarında sürüm var (?v=…, yayında GitHub damgalar); aynı sürüm hep önbellekten.
 * Listeler (data.json, reports.json): telefondaki kopya hemen verilir, yenisi arka planda alınır.
 * Kişisel veriler (Bizim listemiz, tepkiler) şifreyle sunucudan gelir; burada saklanmaz.
 *   data.json değiştiyse sayfaya "veri-yenilendi" iletisi gider ve liste kendiliğinden yenilenir.
 *   Arka plandaki istek başarısız olursa "ag-yok", başarılı olursa "ag-var" iletisi gider (çevrimdışı göstergesi).
 * Yazı tipleri ve simgeler: önce önbellek.
 * “Bizim listemiz” sunucusu başka adreste olduğu için service worker ona karışmaz; uygulama kendi kopyasını saklar.
 */
const SURUM = '__SURUM__';   // yayında scripts/surum.sh ile damgalanır; her yayın kendi önbelleğini kurar
const CACHE = 'gk-' + SURUM;
const EKLER = ['app.css', 'js/temel.js', 'js/cevrimdisi.js', 'js/kisisel.js', 'js/ekle.js', 'js/veri.js', 'js/liste.js', 'js/tepki.js', 'js/gorunum.js', 'js/baslat.js'].map(f => './' + f + '?v=' + SURUM);
const SHELL = [
  './index.html',
  './data.json',
  './reports.json',
  './manifest.webmanifest',
  './fonts/manrope-latin.woff2',
  './fonts/manrope-latin-ext.woff2',
  './icons/icon-192.png',
  './icons/apple-touch-icon.png'
].concat(EKLER);
const PAGE_TIMEOUT = 1500;

self.addEventListener('install', e => {
  // tarayıcının kendi önbelleğini atla: kurulumda dosyaların en yenisi alınsın
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL.map(u => new Request(u, {cache: 'reload'})))).then(() => self.skipWaiting()));
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
  if (req.mode === 'navigate' || /\/(index\.html)?$/.test(url.pathname)) {
    e.respondWith(page(e, req));
    return;
  }
  const m = url.pathname.match(/\/(data|reports)\.json$/);
  if (m) {
    e.respondWith(list(e, url, './' + m[1] + '.json'));
    return;
  }
  // sürümlü stil ve betikler: tam adresle (sürüm dahil) eşleşir; başka sürümün dosyası verilmez
  if (url.searchParams.has('v') && /\/(app\.css|js\/[a-z]+\.js)$/.test(url.pathname)) {
    e.respondWith(cacheFirst(req, false));
    return;
  }
  e.respondWith(cacheFirst(req, true));
});

async function tell(msg) {
  const cs = await self.clients.matchAll({type: 'window'});
  cs.forEach(c => c.postMessage(msg));
}

const imza = r => (r && (r.headers.get('etag') || r.headers.get('last-modified') || r.headers.get('content-length'))) || '';

// sayfa: önce ağ, kısa bekleme; gecikirse telefondaki kopya
async function page(e, req) {
  const cache = await caches.open(CACHE);
  const net = fetch(req);
  e.waitUntil(net.then(res => (res.ok && !res.redirected ? sakla(cache, res.clone()) : null)).catch(() => {}));
  let timer;
  const timeout = new Promise(resolve => { timer = setTimeout(() => resolve(null), PAGE_TIMEOUT); });
  let res = null;
  try {
    res = await Promise.race([net, timeout]);
  } catch (err) {
    res = null;
  }
  clearTimeout(timer);
  if (res && res.ok) return res;
  const hit = await cache.match('./index.html');
  return hit || res || net;
}

// yeni sayfa, bağlı olduğu stil ve betikler önbellekte olmadan saklanmaz: çevrimdışı açılışta eksik ya da başka sürüm dosya kalmasın
async function sakla(cache, res) {
  const html = await res.clone().text();
  const ekler = [...html.matchAll(/(?:href|src)="([^"]+\?v=[^"]+)"/g)].map(m => new URL(m[1], self.location.href).href);
  await Promise.all(ekler.map(async u => {
    if (await cache.match(u)) return;
    const r = await fetch(u, {cache: 'no-cache'});
    if (!r.ok) throw new Error(u);
    await cache.put(u, r);
  }));
  await cache.put('./index.html', res);
}

// listeler: telefondaki kopya hemen, yenisi arka planda
async function list(e, url, key) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(key);
  if (hit && url.searchParams.has('onbellek')) return hit;  // sayfa az önce yenilenen kopyayı istiyor
  const net = fetch(url.origin + url.pathname, {cache: 'no-cache'}).then(async res => {
    if (res.ok) {
      const degisti = !!hit && imza(hit) !== imza(res);
      await cache.put(key, res.clone());
      if (key === './data.json') await tell({type: degisti ? 'veri-yenilendi' : 'ag-var'});
    }
    return res;
  });
  if (!hit) return net;  // ilk açılış: telefonda kopya yok, ağı bekle
  e.waitUntil(net.catch(() => (key === './data.json' ? tell({type: 'ag-yok'}) : null)));
  return hit;
}

async function cacheFirst(req, ignoreSearch) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(req, {ignoreSearch});
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) cache.put(req, res.clone());
  return res;
}
