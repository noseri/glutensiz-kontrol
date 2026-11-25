// Glutensiz Kontrol — Çevrimdışı kullanım: service worker kaydı, "son kontrol" satırı, arka planda yenilenen liste.
// Sayfanın betikleri ortak bir kapsamda, şu sırayla çalışır: temel → cevrimdisi → kisisel → ekle → veri → liste → tepki → gorunum → baslat.
// ---- çevrimdışı kullanım
let NET_DOWN = false, PENDING = false;  // NET_DOWN: service worker yeni listeyi arka planda alamadı
// listeler her pazartesi kontrol edilir; 2 haftadan eskiyse (internetsiz kalındıysa ya da kontrol yapılamadıysa) belirgin uyarı
const ESKI_GUN = 14;
function showUpd(){
  if (!D) return;
  const t = D.checked || D.generated, g = fmtDate(t);
  const gun = Math.floor((Date.now() - Date.parse(t)) / 864e5);
  const eski = gun > ESKI_GUN;
  const off = NET_DOWN || !navigator.onLine;
  const el = $('#upd');
  // eskiyse yıl yazılmaz (satır dar ekranda da tek satıra sığsın), kaç gün olduğu yazılır
  el.textContent = (g ? 'Son kontrol: ' + (eski ? g.replace(/ \d{4}$/, '') + ' · ' + gun + ' gün önce' : g) : '') + (off ? ' · çevrimdışı' : '');
  el.title = eski ? 'Liste ' + gun + ' gündür kontrol edilmedi; değişmiş olabilir. İnternete bağlanınca yenisi alınır; o zamana kadar paketi okuyun.'
    : off ? 'İnternet yok: telefona kaydedilmiş son liste gösteriliyor.' : '';
  el.classList.toggle('off', off);
  el.classList.toggle('eski', eski);
}
addEventListener('online', () => { NET_DOWN = false; showUpd(); });
addEventListener('offline', showUpd);
if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
  addEventListener('load', () => navigator.serviceWorker.register('sw.js', {updateViaCache: 'none'}).catch(() => {}));
}
// liste telefondaki kopyadan hemen açılır; service worker yenisini arka planda alıp haber verir
if ('serviceWorker' in navigator){
  navigator.serviceWorker.addEventListener('message', e => {
    const m = e.data || {};
    if (m.type === 'ag-yok'){ NET_DOWN = true; showUpd(); }
    else if (m.type === 'ag-var'){ NET_DOWN = false; showUpd(); }
    else if (m.type === 'veri-yenilendi'){ NET_DOWN = false; if (D) reloadData(); else PENDING = true; }
  });
  if (navigator.serviceWorker.startMessages) navigator.serviceWorker.startMessages();
}
const STANDALONE = (typeof matchMedia === 'function' && matchMedia('(display-mode: standalone)').matches) || navigator.standalone === true;
