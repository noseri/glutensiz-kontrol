// Glutensiz Kontrol — Kişisel kısım: giriş/çıkış, Bizim listemiz (veri, satırlar, çıkarma).
// Sayfanın betikleri ortak bir kapsamda, şu sırayla çalışır: temel → cevrimdisi → kisisel → ekle → veri → liste → tepki → gorunum → baslat.
// ---- bizim listemiz: kendi eklediğimiz ürünler (Cloudflare Worker + D1, bkz. worker/)
// Kimin eklediğini telefondaki ekleme şifresi, ne zaman eklendiğini sunucunun saati belirler.
const API_URL = 'https://glutensiz-liste.noserinin-hesab.workers.dev';  // boş bırakılırsa bu bölüm hiç görünmez
const API = (/^(localhost|127\.0\.0\.1)$/.test(location.hostname) && new URLSearchParams(location.search).get('api')) || API_URL;
const DAY = {paket:'Paketinde glutensiz ibaresi var', uretici:'Üretici yazılı teyit verdi', analiz:'Analiz raporu var', deneyim:'Kendimiz kullandık, sorun olmadı', diger:'Diğer'};
const DAYS = ['paket', 'uretici', 'analiz', 'deneyim', 'diger'];
function lsGet(k){ try { return localStorage.getItem(k); } catch (e) { return null; } }
function lsSet(k, v){ try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) {} }
let US = {urunler:[], cikarilanlar:[], zaman:null, kaynak:null, hata:false, kontroller:[]};
let USKEY = lsGet('gk-sifre') || '', USNAME = lsGet('gk-ad') || '';
// kişisel kısım (Bizim listemiz, tepkiler, dokunma kayıtları) açık mı: şifre bu telefonda kayıtlıysa
const KIS = () => !!(API && USKEY);
function setUs(j, kaynak){
  if (!j || !Array.isArray(j.urunler)) return false;
  const ok = x => x && typeof x === 'object' && x.id != null && x.marka && x.urun && x.ekleyen && x.eklendi;
  US = {urunler: j.urunler.filter(ok), cikarilanlar: (Array.isArray(j.cikarilanlar) ? j.cikarilanlar : []).filter(ok), zaman: j.zaman || null, kaynak, hata: false,
    kontroller: (Array.isArray(j.kontroller) ? j.kontroller : []).filter(k => k && k.urun != null && k.kisi && k.zaman)};
  US.urunler.forEach(it => { it.nn = norm([it.marka, it.urun, it.kategori || ''].join(' ')); it.kn = norm(it.kategori || ''); });
  // düzeltme zinciri: her kayıt, düzelttiği eski kayda "onceki" ile bağlı
  US.byId = {}; US.next = {};
  US.urunler.concat(US.cikarilanlar).forEach(x => { US.byId[x.id] = x; if (x.onceki != null) US.next[x.onceki] = x; });
  return true;
}
function usRoot(r){ const by = US.byId || {}; let x = r, n = 0; while (x.onceki != null && by[x.onceki] && n++ < 50) x = by[x.onceki]; return x; }
const usNext = r => (US.next || {})[r.id] || null;
function usApply(urunler, cikarilanlar){ setUs({urunler, cikarilanlar, zaman: US.zaman, kontroller: US.kontroller}, US.kaynak || 'canli'); saveUs(); }
function saveUs(){
  const strip = x => { const o = Object.assign({}, x); delete o.nn; delete o.kn; return o; };
  lsSet('gk-bizim', JSON.stringify({zaman: US.zaman, urunler: US.urunler.map(strip), cikarilanlar: US.cikarilanlar.map(strip), kontroller: US.kontroller}));
}
// ---- yeniden kontrol: elle eklenen ürünün paketi 6 ayda bir yeniden okunsun (firmalar üretimi haber vermeden değiştirebilir)
const KONTROL_GUN = 180;
function usZincir(it){ const ids = []; let x = it, n = 0; while (x && n++ < 50){ ids.push(+x.id); x = x.onceki != null ? (US.byId || {})[x.onceki] : null; } return ids; }
// son kontrol: ilk eklenme ya da (düzeltilmiş hâlleri dahil) en son "kontrol ettim"
function sonKontrol(it){
  const ids = new Set(usZincir(it)), kok = usRoot(it);
  let son = {zaman: kok.eklendi, kisi: null};
  US.kontroller.forEach(k => { if (ids.has(+k.urun) && k.zaman > son.zaman) son = k; });
  return son;
}
const kontrolGecti = it => Date.now() - Date.parse(sonKontrol(it).zaman) > KONTROL_GUN * 864e5;
if (KIS()){ try { setUs(JSON.parse(lsGet('gk-bizim') || 'null'), 'onbellek'); } catch (e) {} } else lsSet('gk-bizim', null);
let usBusy = false, usLast = 0;
const usSig = () => US.urunler.map(x => x.id).join(',') + '/' + US.cikarilanlar.map(x => x.id).join(',') + '/' + US.kontroller.map(k => k.id).join(',') + '/' + US.hata;
// kişisel veriler tek istekte: Bizim listemiz, tepkiler, dokunma kayıtları (yalnızca şifreyle)
async function loadUs(draw){
  if (!KIS() || usBusy) return;
  usBusy = true; usLast = Date.now();
  const before = usSig() + '#' + tpSig();
  try {
    const ctl = typeof AbortController === 'function' ? new AbortController() : null;
    const tm = setTimeout(() => { if (ctl) ctl.abort(); }, 7000);
    const r = await fetch(API + '/veri', {cache: 'no-store', headers: authH(USKEY), signal: ctl ? ctl.signal : undefined});
    clearTimeout(tm);
    if (r.status === 401){ usBusy = false; kilitle('Şifre tanınmadı; Giriş’ten yeniden girin.'); return; }
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const j = await r.json();
    if (!setUs(j, 'canli')) throw new Error('biçim');
    setTp(j.tepkiler, j.dokunmalar);
    saveUs(); saveTp();
  } catch (e) {
    US.hata = true;
  }
  usBusy = false;
  if (draw && D && usSig() + '#' + tpSig() !== before) rerender();
}
addEventListener('online', () => loadUs(true));
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && Date.now() - usLast > 30000) loadUs(true); });
const TZF = (() => { try { return new Intl.DateTimeFormat('tr-TR', {timeZone: 'Europe/Istanbul', day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'}); } catch (e) { return null; } })();
function fmtWhen(iso){
  const d = new Date(iso); if (isNaN(d)) return '';
  if (TZF && TZF.formatToParts){ const p = {}; TZF.formatToParts(d).forEach(x => { p[x.type] = x.value; }); return p.day + ' ' + p.month + ' ' + p.year + ', ' + p.hour + ':' + p.minute; }
  return d.toLocaleString('tr-TR');
}
function searchUs(q){
  if (!KIS()) return [];
  const qn = norm(q); if (!qn) return [];
  const qt = qn.split(' ');
  return US.urunler.filter(it => { const w = it.nn.split(' '); return qt.every(t => w.some(x => x.startsWith(t))); });
}
function usRow(it, gone){
  const dn = (DOMAINS.find(d => d[0] === it.alan) || ['', ''])[1];
  const meta = [it.kategori || '', it.alan !== st.dom ? dn : ''].filter(Boolean).map(esc).join(' · ');
  const id = +it.id;
  let stamp;
  if (gone){
    const sonraki = usNext(it);
    stamp = '<b>' + esc(it.ekleyen) + '</b> ' + (it.onceki != null ? 'düzeltti' : 'ekledi') + ' · ' + fmtWhen(it.eklendi) +
      (it.cikarildi ? '<br><b>' + esc(it.cikaran) + '</b> ' + (sonraki ? (it.onceki != null ? 'yeniden düzeltti' : 'düzeltti') : 'listeden çıkardı') + ' · ' + fmtWhen(it.cikarildi) : '');
  } else {
    const kok = usRoot(it), son = sonKontrol(it);  // ilk eklenen hali, son "kontrol ettim"
    stamp = '<b>' + esc(kok.ekleyen) + '</b> ekledi · ' + fmtWhen(kok.eklendi) +
      (kok !== it ? '<br><b>' + esc(it.ekleyen) + '</b> düzeltti · ' + fmtWhen(it.eklendi) : '') +
      (son.kisi ? '<br><b>' + esc(son.kisi) + '</b> kontrol etti · ' + fmtWhen(son.zaman) : '');
  }
  const gec = !gone && KIS() && kontrolGecti(it);
  return '<div class="us-it' + (gone ? ' gone' : '') + '" id="us-' + (gone ? 'g' : '') + id + '"' + (gone ? '' : ' data-us="' + id + '"') + '><span class="mk m-us" aria-hidden="true">' + ICON.us + '</span><div>' +
    '<div class="us-t"><b>' + esc(it.marka) + '</b> ' + esc(it.urun) + (gone && usNext(it) ? '<span class="tag-d">düzeltildi</span>' : '') + '</div>' +
    (meta ? '<div class="us-m">' + meta + '</div>' : '') +
    '<div class="us-d"><span>Dayanak:</span> ' + esc(DAY[it.dayanak] || it.dayanak) + '</div>' +
    (gec ? '<div class="us-k">' + ICON.warn + '<span>6 aydır kontrol edilmedi: paketi yeniden okuyun.</span><button class="lnk" data-kontrol="' + id + '">Kontrol ettim</button></div>' : '') +
    (gone ? '' : rxAll([usKey(it)]) + tpk(it.marka + ' ' + it.urun)) +
    (it.notu ? '<div class="us-n">' + esc(it.notu) + '</div>' : '') +
    '<div class="us-s"><span>' + stamp + '</span>' +
      (!gone && KIS() ? '<span class="us-a"><button class="lnk" data-duzelt="' + id + '">Düzelt</button><button class="lnk" data-cikar="' + id + '">Listeden çıkar</button></span>' : '') + '</div></div></div>';
}
function addBtn(q, label){
  return '<button class="addb" data-ekle="' + esc(q || '') + '">' + ICON.plus + '<span>' + esc(label || 'Listemize ürün ekle') + '</span></button>';
}
function usCard(items){
  return '<article class="card v-us"><div class="verdict"><span class="dot">' + ICON.us + '</span><div><p class="vt">Bizim listemizde</p><p class="vs"><b class="k">Sizin eklediğiniz</b> · dernek onayı değil</p></div></div>' +
    '<div class="cats">' + items.map(it => usRow(it)).join('') + '</div></article>';
}
function usHistory(dom){
  const g = US.cikarilanlar.filter(it => it.alan === dom);
  if (!g.length) return '';
  const d = g.filter(it => usNext(it)).length, c = g.length - d;
  const ozet = [d ? d + ' düzeltme' : '', c ? c + ' çıkarma' : ''].filter(Boolean).join(', ');
  return '<details class="ush"><summary>Geçmiş: ' + ozet + '</summary>' + g.slice(0, 50).map(it => usRow(it, true)).join('') + '</details>';
}
function usHome(){
  if (!KIS()) return '';
  const mine = US.urunler.filter(it => it.alan === st.dom);
  const otherN = US.urunler.length - mine.length;
  const lim = st.usAll ? 999 : 5;
  let h = '<div class="sec"><span>Bizim listemiz</span><span>' + (mine.length || '') + '</span></div><article class="card v-us">';
  if (US.hata && US.kaynak) h += '<div class="us-off">Sunucuya şu an ulaşılamıyor; telefondaki son liste gösteriliyor.</div>';
  const gec = mine.filter(kontrolGecti).length;
  if (gec) h += '<div class="us-kz">' + ICON.warn + '<span>' + gec + ' ürünün yeniden kontrol zamanı geldi: paketini okuyup “Kontrol ettim”e dokunun.</span></div>';
  if (mine.length){
    h += mine.slice(0, lim).map(it => usRow(it)).join('');
    if (mine.length > lim) h += '<button class="more" data-usall="1">Tümünü göster (' + mine.length + ')</button>';
  }
  h += addBtn('');
  h += '<div class="us-f">' + (mine.length ? '' : 'Derneklerde olmayan ama güvendiğiniz ürünler için; kimin, ne zaman eklediği yazılır.<br>') +
    'Bu telefonda <b>' + esc(USNAME || '…') + '</b> olarak açık · <button class="lnk" data-unut="1">çıkış</button>' +
    (otherN ? '<br>Diğer sekmelerde ' + otherN + ' ürün daha var.' : '') + '</div>';
  return h + usHistory(st.dom) + '</article>';
}
function usCatBlock(c){
  if (!KIS()) return '';
  const its = US.urunler.filter(it => it.alan === c.d && it.kn && (it.kn === c.nn || it.kn.startsWith(c.nn + ' ') || c.nn.startsWith(it.kn + ' ')));
  return its.length ? '<div class="sec"><span>Bizim listemiz</span><span>' + its.length + '</span></div>' + usCard(its) : '';
}
// şifre ve kişisel verilerin bu telefondaki kopyası silinir
function forgetKey(){
  USKEY = ''; USNAME = '';
  ['gk-sifre', 'gk-ad', 'gk-tepki', 'gk-bizim'].forEach(k => lsSet(k, null));
  setUs({urunler: [], cikarilanlar: []}, null); setTp([], []);
  document.documentElement.classList.remove('kis');
}
function kilitle(msg){
  forgetKey();
  [dlg, tpDlg, grDlg].forEach(d => { if (d && d.open) d.close(); });
  rerender();
  if (msg) toast(msg);
}
// ---- giriş: kişisel kısım yalnızca şifresi girilmiş telefonda açılır
let grDlg = null;
function openGiris(){
  if (!API) return;
  if (!grDlg){
    grDlg = document.createElement('dialog');
    grDlg.className = 'sheet'; grDlg.setAttribute('aria-labelledby', 'grH');
    grDlg.innerHTML = '<form novalidate><h3 id="grH">Giriş</h3>' +
      '<p class="lead">Bizim listemiz, tepkiler ve “bize dokundu” kayıtları için şifrenizi girin. Bir kez girersiniz; bu telefonda saklanır.</p>' +
      '<label class="fl">Şifre<input name="sifre" type="password" autocomplete="current-password" autocapitalize="off" spellcheck="false" enterkeyhint="go"></label>' +
      '<p class="err" role="alert"></p>' +
      '<div class="acts"><button type="button" class="btn2" data-kapat="1">Vazgeç</button><button type="submit" class="btn">Aç</button></div></form>';
    document.body.appendChild(grDlg);
    grDlg.querySelector('form').addEventListener('submit', e => { e.preventDefault(); girisYap(); });
    grDlg.addEventListener('click', e => { if (e.target === grDlg || e.target.closest('[data-kapat]')) grDlg.close(); });
    grDlg.addEventListener('close', () => document.documentElement.classList.remove('modal'));
  }
  const f = grDlg.querySelector('form'); f.reset();
  grDlg.querySelector('.err').textContent = '';
  const b = f.querySelector('.btn'); b.disabled = false; b.textContent = 'Aç';
  document.documentElement.classList.add('modal');
  if (typeof grDlg.showModal === 'function') grDlg.showModal(); else grDlg.setAttribute('open', '');
  f.elements.namedItem('sifre').focus();
}
async function girisYap(){
  const f = grDlg.querySelector('form'), inp = f.elements.namedItem('sifre'), err = grDlg.querySelector('.err'), btn = f.querySelector('.btn');
  const key = inp.value.normalize('NFC').trim();
  err.textContent = '';
  if (key.length < 8){ err.textContent = 'Şifrenizi yazın (en az 8 karakter).'; inp.focus(); return; }
  btn.disabled = true; btn.textContent = 'Açılıyor…';
  try {
    const r = await fetch(API + '/ben', {cache: 'no-store', headers: authH(key)});
    let j = {}; try { j = await r.json(); } catch (x) {}
    if (r.ok && j.ad){
      USKEY = key; USNAME = j.ad; lsSet('gk-sifre', key); lsSet('gk-ad', j.ad);
      document.documentElement.classList.add('kis');
      grDlg.close();
      await loadUs(false);
      rerender();
      toast('Açıldı · ' + j.ad);
      return;
    }
    err.textContent = r.status === 401 ? 'Şifre tanınmadı. Yeniden yazıp deneyin.' : (j.hata || 'Açılamadı (hata ' + r.status + ').');
    inp.select();
  } catch (e) { err.textContent = netErr(e); }
  btn.disabled = false; btn.textContent = 'Aç';
}
// HTTP başlıkları ı, ş, ğ gibi harfleri taşıyamaz; şifre kodlanarak gönderilir, sunucu çözer
const authH = k => ({'Authorization': 'Bearer ' + encodeURIComponent(String(k).normalize('NFC'))});
function netErr(e){ return navigator.onLine === false ? 'İnternet bağlantısı yok; bağlanınca yeniden deneyin.' : 'Sunucuya ulaşılamadı; biraz sonra yeniden deneyin.' + (e && e.message ? ' (' + e.message + ')' : ''); }
async function kontrolEt(id, t){
  if (!KIS()) return kilitle();
  t.disabled = true; t.textContent = 'Kaydediliyor…';
  try {
    const r = await fetch(API + '/kontrol', {method: 'POST', headers: Object.assign({'Content-Type': 'application/json'}, authH(USKEY)), body: JSON.stringify({id})});
    let j = {}; try { j = await r.json(); } catch (x) {}
    if (r.ok && j.kontrol){
      US.kontroller = [j.kontrol].concat(US.kontroller); saveUs(); rerender();
      toast('Kontrol kaydedildi · ' + j.kontrol.kisi + ' · ' + fmtWhen(j.kontrol.zaman));
      return;
    }
    if (r.status === 401) return kilitle('Şifre tanınmadı; Giriş’ten yeniden girin.');
    toast(j.hata || ('Kaydedilemedi (hata ' + r.status + ').'));
    if (r.status === 404) loadUs(true); else rerender();
  } catch (e) { toast(netErr(e)); rerender(); }
}
async function removeUs(id, t){
  if (!KIS()) return kilitle();
  const box = t.closest('.cf'); if (box) box.textContent = 'Çıkarılıyor…';
  try {
    const r = await fetch(API + '/cikar', {method: 'POST', headers: Object.assign({'Content-Type': 'application/json'}, authH(USKEY)), body: JSON.stringify({id})});
    let j = {}; try { j = await r.json(); } catch (x) {}
    if (r.ok && j.urun){
      usApply(US.urunler.filter(x => +x.id !== id), [j.urun].concat(US.cikarilanlar.filter(x => +x.id !== id)));
      rerender(); toast('Listeden çıkarıldı · ' + j.urun.cikaran + ' · ' + fmtWhen(j.urun.cikarildi));
      return;
    }
    if (r.status === 401) return kilitle('Şifre tanınmadı; Giriş’ten yeniden girin.');
    toast(j.hata || ('Çıkarılamadı (hata ' + r.status + ').'));
    if (r.status === 404) loadUs(true); else rerender();
  } catch (e) { toast(netErr(e)); rerender(); }
}
function usClick(t){
  const ds = t.dataset;
  if ('ekle' in ds){ openAdd(ds.ekle); return true; }
  if (ds.duzelt){ openEdit(+ds.duzelt); return true; }
  if (ds.cikar){
    (t.closest('.us-a') || t).outerHTML = '<span class="cf">Listeden çıkarılsın mı? <button class="lnk yes" data-cikarevet="' + (+ds.cikar) + '">Evet, çıkar</button><button class="lnk" data-cikarhayir="1">Vazgeç</button></span>';
    return true;
  }
  if (ds.cikarevet){ removeUs(+ds.cikarevet, t); return true; }
  if (ds.cikarhayir){ rerender(); return true; }
  if (ds.unut){ kilitle('Çıkış yapıldı; şifre ve kişisel liste bu telefondan silindi.'); return true; }
  if (ds.giris){ openGiris(); return true; }
  if (ds.kontrol){ kontrolEt(+ds.kontrol, t); return true; }
  if (ds.usall){ st.usAll = true; rerender(); return true; }
  if (ds.tpt){ st.tpTab = ds.tpt; rerender(); return true; }
  return false;
}
