// Glutensiz Kontrol — Tepkiler (beğendim, beğenmedim, favori) ve "bize dokundu" günlüğü.
// Sayfanın betikleri ortak bir kapsamda, şu sırayla çalışır: temel → cevrimdisi → kisisel → ekle → veri → liste → tepki → gorunum → baslat.
// ---- tepkiler ve "bize dokundu" günlüğü (kişisel: yalnızca şifresi girilmiş telefonda görünür)
// Tepki: her kişinin bir ürüne beğendi / beğenmedi / favori tepkisi; değiştirilebilir.
// Dokunma: "bize dokundu" olayları; her biri ayrı kayıt (tarih, kim, ne oldu, parti no).
// Ürün anahtarı: dernek satırı 'u|<kalıcı numara>' (haftalık derleme verir; yazım değişse de korunur),
// Bizim listemiz ürünü 'b|<ilk kaydın id'si>' (düzeltmelerde değişmez).
let TP = {rows: [], dok: [], byKey: new Map(), dokByKey: new Map()}, TPV = 0, KM = null;
function setTp(rows, dok){
  TPV++;
  const anah = r => r && /^[ub]\|\d+$/.test(r.anahtar) && r.kisi;
  TP = {rows: (Array.isArray(rows) ? rows : []).filter(r => anah(r) && (r.tepki === 'begen' || r.tepki === 'begenme')),
    dok: (Array.isArray(dok) ? dok : []).filter(r => anah(r) && r.id != null && /^\d{4}-\d{2}-\d{2}$/.test(r.tarih)), byKey: new Map(), dokByKey: new Map()};
  const put = (m, r) => (m.get(r.anahtar) || m.set(r.anahtar, []).get(r.anahtar)).push(r);
  TP.rows.forEach(r => put(TP.byKey, r)); TP.dok.forEach(r => put(TP.dokByKey, r));
}
function saveTp(){ lsSet('gk-tepki', JSON.stringify({tepkiler: TP.rows, dokunmalar: TP.dok})); }
if (KIS()){ try { const c = JSON.parse(lsGet('gk-tepki') || 'null'); if (c && !Array.isArray(c)) setTp(c.tepkiler, c.dokunmalar); } catch (e) {} } else lsSet('gk-tepki', null);
function tpSig(){ return TP.rows.map(r => r.anahtar + r.kisi + r.zaman).join(',') + '/' + TP.dok.map(r => r.id).join(','); }
const lineKey = l => l.u ? 'u|' + l.u : '';
const usKey = it => 'b|' + usRoot(it).id;
const canTap = l => !!(KIS() && l.u && l.b && l.k !== 'note' && l.k !== 'info' && !KAT_DIS.has(l.c));
// anahtar → satır eşlemesi ve iki listedeki eşler; liste ya da tepkiler değişince bir kez kurulur
function keyMap(){
  if (KM && KM.d === D && KM.v === TPV) return KM;
  const k2l = new Map(), nb = new Map();
  LN.forEach(l => { if (l.u) k2l.set(lineKey(l), l); });
  // iki listedeki aynı ürün (eşleşme bazen tek yönlü yazılmış; iki yöne de bağlanır)
  const link = (a, b) => { if (a && b && a !== b) (nb.get(a) || nb.set(a, new Set()).get(a)).add(b); };
  LN.forEach(l => { if (l.st === 'both') (l.p || []).forEach(pid => { link(l, LN[pid]); link(LN[pid], l); }); });
  // ana sayfada aynı ürüne iki listeden verilen tepkiler tek satırda toplanır
  const resolve = k => k2l.get(k) || null, rl = new Set(), par = new Map(), top = new Map();
  TP.rows.concat(TP.dok).forEach(r => { const l = resolve(r.anahtar); if (l){ rl.add(l); par.set(l, l); } });
  const find = x => { while (par.get(x) !== x) x = par.get(x); return x; };
  rl.forEach(l => (nb.get(l) || []).forEach(o => { if (rl.has(o)){ const a = find(l), b = find(o); if (a !== b) par.set(a, b); } }));
  rl.forEach(l => { const r = find(l), k = lineKey(l); if (!top.has(r) || k < top.get(r)) top.set(r, k); });
  return KM = {d: D, v: TPV, nb, resolve, canon: l => rl.has(l) ? top.get(find(l)) : lineKey(l)};
}
// bir satırın anahtarları: kendisi ve diğer listedeki eşi
const lineKeys = l => [l].concat([...(keyMap().nb.get(l) || [])]).map(lineKey).filter(Boolean);
const tpCanon = k => { const m = keyMap(), l = m.resolve(k); return l ? m.canon(l) : k; };
// ürün artık yok: dernek listelerinde bu numarada satır kalmadı ya da Bizim listemiz'den çıkarıldı
const tpGone = k => k[0] === 'u' ? !keyMap().resolve(k) : !US.urunler.some(it => usKey(it) === k);
function rxFor(keys){
  const by = new Map();
  keys.forEach(k => (TP.byKey.get(k) || []).forEach(r => { const o = by.get(r.kisi); if (!o || o.zaman < r.zaman) by.set(r.kisi, r); }));
  return [...by.values()].sort((a, b) => a.kisi.localeCompare(b.kisi, 'tr'));
}
const dokSira = (a, b) => (b.tarih > a.tarih) - (b.tarih < a.tarih) || b.id - a.id;
function dokFor(keys){
  const seen = new Set(), out = [];
  keys.forEach(k => (TP.dokByKey.get(k) || []).forEach(r => { if (!seen.has(r.id)){ seen.add(r.id); out.push(r); } }));
  return out.sort(dokSira);
}
const bas = n => esc(String(n || '?').charAt(0).toLocaleUpperCase('tr'));
const tpk = t => '<button type="button" class="tpk">Tepki ver: ' + esc(String(t).split(/\s+/).slice(0, 6).join(' ')) + '</button>';
function rxBadges(rows, doks){
  let h = '';
  if (doks && doks.length) h += '<span class="rx-i dok">' + ICON.warn + 'Dokundu' + (doks.length > 1 ? ' ' + doks.length + ' kez' : '') + ' · ' + [...new Set(doks.map(r => r.kisi))].map(esc).join(', ') + '</span>';
  const rk = r => r.favori ? 0 : r.tepki === 'begen' ? 1 : 2;
  rows.slice().sort((a, b) => rk(a) - rk(b)).forEach(r => {
    if (r.favori) h += '<span class="rx-i fav" title="' + esc(r.kisi) + ': favori">' + ICON.heart + bas(r.kisi) + '</span>';
    else if (r.tepki === 'begen') h += '<span class="rx-i" title="' + esc(r.kisi) + ': beğendi">' + ICON.up + bas(r.kisi) + '</span>';
    else h += '<span class="rx-i down" title="' + esc(r.kisi) + ': beğenmedi">' + ICON.dn + bas(r.kisi) + (r.neden ? ' <span class="rn">“' + esc(r.neden) + '”</span>' : '') + '</span>';
  });
  return h ? '<span class="rx">' + h + '</span>' : '';
}
const rxAll = keys => KIS() ? rxBadges(rxFor(keys), dokFor(keys)) : '';
const tpText = r => r.favori ? 'Favori' : r.tepki === 'begen' ? 'Beğendi' : 'Beğenmedi' + (r.neden ? ' — “' + esc(r.neden) + '”' : '');
// dokunmanın olası nedeni: gerçek tehlike (bulaşma) ile glutenden bağımsız hassasiyeti aylar sonra ayırt edebilmek için
const DNEDEN = {bulasma: ['Çapraz bulaşma şüphesi', ''], agir: ['Gluten dışı bir şey ağır geldi', 'laktoz, gam, lif…'],
  baska: ['Aynı gün başka şüpheli bir şey yendi', ''], bilinmiyor: ['Bilmiyorum', '']};
const dnText = k => DNEDEN[k] ? DNEDEN[k][0] + (DNEDEN[k][1] ? ' (' + DNEDEN[k][1] + ')' : '') : '';
const dokText = r => '<b>' + fmtDate(r.tarih) + '</b> · ' + esc(r.kisi) + (r.notu ? ' — “' + esc(r.notu) + '”' : '') +
  (DNEDEN[r.neden] ? ' · ' + esc(dnText(r.neden)) : '') + (r.parti ? ' · Paket: ' + esc(r.parti) : '');
// marka kartında: bu markanın "bize dokundu" denen ürünleri (Bizim listemiz'deki aynı marka dahil)
function dokWarn(b){
  if (!TP.dok.length) return '';
  const m = keyMap(), bn = BNORM[b];
  const n = new Set(TP.dok.filter(r => { const l = m.resolve(r.anahtar); return l ? l.b === b : norm(r.marka) === bn; }).map(r => tpCanon(r.anahtar))).size;
  return n ? ' · <span class="dokw">Bu markanın ' + n + ' ürünü size dokundu</span>' : '';
}
// Türkiye saatiyle bugün (YYYY-AA-GG)
const bugun = () => new Date(Date.now() + 3 * 3600e3).toISOString().slice(0, 10);
// tepki penceresi
let tpDlg = null, tpCur = null, tpS = {tepki: null, favori: false, yeni: false, dneden: null};
function buildTp(){
  const d = document.createElement('dialog');
  d.className = 'sheet'; d.setAttribute('aria-labelledby', 'tpH');
  d.innerHTML = '<form novalidate>' +
    '<h3 id="tpH" class="tp-t" tabindex="-1" autofocus></h3><p class="lead" id="tpSub"></p>' +
    '<div class="tp-o" id="tpO" hidden></div>' +
    '<fieldset class="rad"><legend id="tpL">Sizin tepkiniz</legend><div class="tp-b">' +
      '<button type="button" class="tpb" data-v="begen" aria-pressed="false">' + ICON.up + 'Beğendim</button>' +
      '<button type="button" class="tpb" data-v="begenme" aria-pressed="false">' + ICON.dn + 'Beğenmedim</button>' +
      '<button type="button" class="tpb" data-v="favori" aria-pressed="false">' + ICON.heart + 'Favori</button>' +
    '</div></fieldset>' +
    '<label class="fl" data-neden hidden><span>Neden beğenmediniz? <span class="opt">· isteğe bağlı</span></span><input name="neden" maxlength="140" autocomplete="off" enterkeyhint="done" placeholder="ör. çok kuru, pahalı, dağılıyor"></label>' +
    '<section class="dok-b" aria-labelledby="dkH"><h4 id="dkH">' + ICON.warn + 'Bize dokundu</h4>' +
      '<ul class="dk-l" id="dkL" hidden></ul>' +
      '<button type="button" class="tpb dok" data-v="yeni" aria-pressed="false">' + ICON.plus + '<span>Bize dokundu ekle</span></button>' +
      '<div class="dk-f" data-yeni hidden>' +
        '<label class="fl">Ne zaman?<input name="dtarih" type="date"></label>' +
        '<fieldset class="dk-n"><legend>Olası neden <span class="opt">· isteğe bağlı</span></legend><div class="dk-nb">' +
          Object.entries(DNEDEN).map(([k, [n, alt]]) => '<button type="button" class="nb" data-dn="' + k + '" aria-pressed="false">' + n + (alt ? '<small>' + alt + '</small>' : '') + '</button>').join('') +
        '</div></fieldset>' +
        '<label class="fl"><span>Ne oldu? <span class="opt">· isteğe bağlı</span></span><input name="dnotu" maxlength="200" autocomplete="off" enterkeyhint="next" placeholder="ör. 2 saat sonra karın ağrısı"></label>' +
        '<label class="fl"><span>Paket bilgisi <span class="opt">· isteğe bağlı</span></span><input name="dparti" maxlength="80" autocomplete="off" spellcheck="false" enterkeyhint="done" placeholder="Parti no, son kullanma tarihi, üretici"></label>' +
      '</div>' +
      '<p class="small">Listede olsa bile rahatsızlık yaptıysa ekleyin; ikinizde de uyarı olarak görünür. Tat tercihinden ayrı tutulur.</p>' +
    '</section>' +
    '<p class="err" role="alert"></p>' +
    '<div class="acts"><button type="button" class="btn2" data-kapat="1">Vazgeç</button><button type="submit" class="btn">Kaydet</button></div></form>';
  document.body.appendChild(d);
  d.querySelector('form').addEventListener('submit', e => { e.preventDefault(); submitTp(); });
  d.addEventListener('click', e => {
    if (e.target === d || e.target.closest('[data-kapat]')) return d.close();
    const sil = e.target.closest('[data-dsil]'), evet = e.target.closest('[data-dsilevet]');
    if (sil){ sil.outerHTML = '<span class="cf">Silinsin mi? <button type="button" class="lnk yes" data-dsilevet="' + (+sil.dataset.dsil) + '">Evet, sil</button><button type="button" class="lnk" data-dsilhayir="1">Vazgeç</button></span>'; return; }
    if (evet) return dokSil(+evet.dataset.dsilevet, evet);
    if (e.target.closest('[data-dsilhayir]')) return dkPaint();
    const nb = e.target.closest('.nb'); if (nb){ tpS.dneden = tpS.dneden === nb.dataset.dn ? null : nb.dataset.dn; return tpPaint(); }
    const b = e.target.closest('.tpb'); if (b) tpToggle(b.dataset.v);
  });
  d.addEventListener('close', () => document.documentElement.classList.remove('modal'));
  return d;
}
function tpPaint(){
  const q = x => tpDlg.querySelector(x);
  q('.tpb[data-v=begen]').setAttribute('aria-pressed', String(tpS.tepki === 'begen'));
  q('.tpb[data-v=begenme]').setAttribute('aria-pressed', String(tpS.tepki === 'begenme'));
  q('.tpb[data-v=favori]').setAttribute('aria-pressed', String(tpS.favori));
  q('.tpb[data-v=yeni]').setAttribute('aria-pressed', String(tpS.yeni));
  q('[data-neden]').hidden = tpS.tepki !== 'begenme';
  q('[data-yeni]').hidden = !tpS.yeni;
  tpDlg.querySelectorAll('.nb').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.dn === tpS.dneden)));
}
// beğendim ile beğenmedim birbirini dışlar; favori beğeni sayılır
function tpToggle(v){
  if (v === 'begen'){ tpS.tepki = tpS.tepki === 'begen' ? null : 'begen'; if (tpS.tepki !== 'begen') tpS.favori = false; }
  else if (v === 'begenme'){ tpS.tepki = tpS.tepki === 'begenme' ? null : 'begenme'; if (tpS.tepki) tpS.favori = false; }
  else if (v === 'favori'){ tpS.favori = !tpS.favori; if (tpS.favori) tpS.tepki = 'begen'; }
  else if (v === 'yeni') tpS.yeni = !tpS.yeni;
  tpPaint();
}
// pencerede bu ürünün dokunma kayıtları (en yenisi üstte); kişi kendi kaydını silebilir
function dkPaint(){
  const doks = dokFor(tpCur.keys), ul = tpDlg.querySelector('#dkL');
  ul.hidden = !doks.length;
  ul.innerHTML = doks.map(r => '<li>' + dokText(r) + (r.kisi === USNAME ? ' <button type="button" class="lnk" data-dsil="' + (+r.id) + '">Sil</button>' : '') + '</li>').join('');
  const b = tpDlg.querySelector('.tpb[data-v=yeni] span'); b.textContent = doks.length ? 'Yeniden dokundu ekle' : 'Bize dokundu ekle';
}
function openTp(kind, id){
  if (!KIS() || !D) return;
  let cur;
  if (kind === 'l'){
    const l = LN[id]; if (!l || !canTap(l)) return;
    cur = {anahtar: lineKey(l), keys: lineKeys(l), alan: l.d, marka: String(BN[l.b] || l.b).slice(0, 80), urun: l.t.slice(0, 300),
      baslik: l.t, alt: [BN[l.b], (CAT[l.c] || {}).n, keyMap().nb.has(l) ? 'iki listede de var' : SRCN[l.s] + ' listesi'].filter(Boolean).join(' · ')};
  } else {
    const it = US.urunler.find(x => +x.id === id); if (!it) return;
    const k = usKey(it);
    cur = {anahtar: k, keys: [k], alan: it.alan, marka: String(it.marka).slice(0, 80), urun: String(it.urun).slice(0, 300), baslik: it.marka + ' ' + it.urun, alt: ['Bizim listemiz', it.kategori].filter(Boolean).join(' · ')};
  }
  tpCur = cur;
  tpDlg = tpDlg || buildTp();
  const f = tpDlg.querySelector('form'), el = n => f.elements.namedItem(n);
  f.reset();
  tpDlg.querySelector('#tpH').textContent = cur.baslik;
  tpDlg.querySelector('#tpSub').textContent = cur.alt;
  const rows = rxFor(cur.keys), mine = rows.find(r => r.kisi === USNAME) || null, others = rows.filter(r => r !== mine);
  if (mine) cur.anahtar = mine.anahtar;
  tpS = {tepki: mine ? mine.tepki : null, favori: !!(mine && mine.favori), yeni: false, dneden: null};
  el('neden').value = (mine && mine.neden) || '';
  el('dtarih').value = bugun(); el('dtarih').max = bugun();
  const o = tpDlg.querySelector('#tpO');
  o.hidden = !others.length;
  o.innerHTML = others.map(r => '<div><b>' + esc(r.kisi) + ':</b> ' + tpText(r) + '</div>').join('');
  tpDlg.querySelector('#tpL').textContent = 'Sizin tepkiniz (' + (USNAME || '…') + ')';
  tpDlg.querySelector('.err').textContent = '';
  const b = f.querySelector('.btn'); b.disabled = false; b.textContent = 'Kaydet';
  dkPaint(); tpPaint();
  document.documentElement.classList.add('modal');
  if (typeof tpDlg.showModal === 'function') tpDlg.showModal(); else tpDlg.setAttribute('open', '');
}
const jsonH = () => Object.assign({'Content-Type': 'application/json'}, authH(USKEY));
async function submitTp(){
  const f = tpDlg.querySelector('form'), el = n => f.elements.namedItem(n), err = tpDlg.querySelector('.err'), btn = f.querySelector('.btn');
  err.textContent = '';
  if (!KIS()) return kilitle();
  const mine = rxFor(tpCur.keys).find(r => r.kisi === USNAME) || null;
  const neden = tpS.tepki === 'begenme' ? el('neden').value.trim() : '';
  const degisti = (mine ? mine.tepki : null) !== tpS.tepki || !!(mine && mine.favori) !== tpS.favori || (tpS.tepki === 'begenme' && ((mine && mine.neden) || '') !== neden);
  let dk = null;
  if (tpS.yeni){
    dk = {tarih: el('dtarih').value || bugun(), neden: tpS.dneden, notu: el('dnotu').value.trim(), parti: el('dparti').value.trim()};
    if (dk.tarih > bugun()){ err.textContent = 'İleri bir tarih seçilemez.'; el('dtarih').focus(); return; }
  }
  if (!degisti && !dk){ tpDlg.close(); return; }
  const base = {anahtar: tpCur.anahtar, alan: tpCur.alan, marka: tpCur.marka, urun: tpCur.urun};
  btn.disabled = true; btn.textContent = 'Kaydediliyor…';
  let tj = null;
  try {
    if (degisti){
      const r = await fetch(API + '/tepki', {method: 'POST', headers: jsonH(), body: JSON.stringify(Object.assign({tepki: tpS.tepki, favori: tpS.favori, neden}, base))});
      tj = await r.json().catch(() => ({}));
      if (r.status === 401) return kilitle('Şifre tanınmadı; Giriş’ten yeniden girin.');
      if (!r.ok || !tj.kisi){ err.textContent = tj.hata || ('Kaydedilemedi (hata ' + r.status + '). Biraz sonra yeniden deneyin.'); btn.disabled = false; btn.textContent = 'Kaydet'; return; }
      // bu kişinin bu üründe (eşleşmiş satırlar dahil) başka anahtarla kalmış eski kaydı silinir
      TP.rows.filter(x => x.kisi === tj.kisi && x.anahtar !== base.anahtar && tpCur.keys.includes(x.anahtar)).forEach(x =>
        fetch(API + '/tepki', {method: 'POST', headers: jsonH(), body: JSON.stringify({anahtar: x.anahtar, alan: x.alan, marka: x.marka, urun: x.urun, tepki: null})}).catch(() => {}));
      setTp(TP.rows.filter(x => !(x.kisi === tj.kisi && tpCur.keys.includes(x.anahtar))).concat(tj.tepki ? [tj.tepki] : []), TP.dok);
      saveTp();
    }
    if (dk){
      const r = await fetch(API + '/dokunma', {method: 'POST', headers: jsonH(), body: JSON.stringify(Object.assign(dk, base))});
      const dj = await r.json().catch(() => ({}));
      if (r.status === 401) return kilitle('Şifre tanınmadı; Giriş’ten yeniden girin.');
      if (!r.ok || !dj.dokunma){
        err.textContent = (degisti ? 'Tepkiniz kaydedildi ama dokunma kaydı eklenemedi: ' : '') + (dj.hata || ('hata ' + r.status + '. Biraz sonra yeniden deneyin.'));
        if (degisti) rerender();
        btn.disabled = false; btn.textContent = 'Kaydet'; return;
      }
      setTp(TP.rows, [dj.dokunma].concat(TP.dok)); saveTp();
    }
    tpDlg.close(); rerender();
    toast(dk ? 'Kaydedildi · “bize dokundu” ikinizde de uyarı olarak görünecek' : !tj.tepki ? 'Tepki kaldırıldı' : tj.tepki.favori ? 'Favorilere eklendi' : 'Kaydedildi');
    return;
  } catch (e) { err.textContent = netErr(e); }
  btn.disabled = false; btn.textContent = 'Kaydet';
}
async function dokSil(id, t){
  const box = t.closest('.cf'); if (box) box.textContent = 'Siliniyor…';
  const at = () => { setTp(TP.rows, TP.dok.filter(x => +x.id !== id)); saveTp(); dkPaint(); rerender(); };
  try {
    const r = await fetch(API + '/dokunma-sil', {method: 'POST', headers: jsonH(), body: JSON.stringify({id})});
    let j = {}; try { j = await r.json(); } catch (x) {}
    if (r.ok){ at(); toast('Kayıt silindi'); return; }
    if (r.status === 401) return kilitle('Şifre tanınmadı; Giriş’ten yeniden girin.');
    if (r.status === 404){ at(); toast('Bu kayıt zaten silinmiş'); return; }
    toast(j.hata || ('Silinemedi (hata ' + r.status + ').')); dkPaint();
  } catch (e) { toast(netErr(e)); dkPaint(); }
}
// ana sayfa: Tepkilerimiz (ürün bazında; iki listedeki aynı ürün tek satır)
const TPT = [['dokundu', 'Dokunan', 'warn', 'dk'], ['ikimiz', 'İkimiz de', 'iki', 'fv'], ['favori', 'Favori', 'heart', 'fv'], ['begen', 'Beğenilen', 'up', ''], ['begenme', 'Beğenilmeyen', 'dn', '']];
function tpName(r){
  const u = String(r.urun || ''), mw = norm(r.marka).split(' ').filter(Boolean).length, w = u.split(/\s+/);
  const rest = norm(w.slice(0, mw).join(' ')) === norm(r.marka) ? w.slice(mw).join(' ') : u;
  return rest || u;
}
const tpQuery = r => (r.marka + ' ' + tpName(r).split(/\s+/).slice(0, 3).join(' ')).trim();
function tpGroups(dom){
  const prod = new Map();
  const add = (r, dok) => {
    if (r.alan !== dom) return;
    const c = tpCanon(r.anahtar);
    if (!prod.has(c)) prod.set(c, {key: c, rs: [], doks: [], snap: r, son: ''});
    const p = prod.get(c);
    (dok ? p.doks : p.rs).push(r);
    if ((r.zaman || '') > p.son){ p.son = r.zaman || ''; p.snap = r; }
  };
  TP.rows.forEach(r => add(r, false)); TP.dok.forEach(r => add(r, true));
  const items = [...prod.values()].map(p => {
    const by = new Map(); p.rs.forEach(r => { const o = by.get(r.kisi); if (!o || o.zaman < r.zaman) by.set(r.kisi, r); });
    p.rows = [...by.values()].sort((a, b) => a.kisi.localeCompare(b.kisi, 'tr'));
    p.doks.sort(dokSira);
    p.gone = tpGone(p.key);
    return p;
  }).sort((a, b) => (b.son > a.son) - (b.son < a.son));
  return {
    dokundu: items.filter(p => p.doks.length),
    // ikimiz de: en az iki kişi beğendi (favori dahil), beğenmeyen yok: ortak alınacaklar için
    ikimiz: items.filter(p => p.rows.filter(r => r.tepki === 'begen').length >= 2 && !p.rows.some(r => r.tepki === 'begenme')),
    favori: items.filter(p => p.rows.some(r => r.favori)),
    begen: items.filter(p => p.rows.some(r => r.tepki === 'begen' && !r.favori)),
    begenme: items.filter(p => p.rows.some(r => r.tepki === 'begenme'))
  };
}
function tpRow(p, tab){
  const d = tab === 'dokundu' ? p.doks[0] : null;
  return '<button class="tp-row" data-q="' + esc(tpQuery(p.snap)) + '"><span class="tn"><b>' + esc(p.snap.marka) + '</b> ' + esc(tpName(p.snap)) + '</span>' +
    (p.gone ? '<span class="tp-g">' + ICON.warn + (p.key[0] === 'b' ? 'Bizim listemiz’den çıkarıldı' : 'Dernek listelerinde artık bu satır yok; aratıp kontrol edin') + '</span>' : '') +
    rxBadges(p.rows, p.doks) + (d ? '<span class="tp-d">Son: ' + dokText(d) + '</span>' : '') + '</button>';
}
function tpHome(){
  if (!KIS()) return '';
  const g = tpGroups(st.dom);
  const total = new Set([].concat(g.dokundu, g.ikimiz, g.favori, g.begen, g.begenme).map(p => p.key)).size;
  const h = '<div class="sec"><span>Tepkilerimiz</span><span>' + (total || '') + '</span></div><article class="card">';
  if (!total) return h + '<div class="us-e">Bir ürünün satırına dokunarak beğendim, beğenmedim, favori ya da “bize dokundu” diyebilirsiniz. Kimin ne dediği burada toplanır.</div></article>';
  const tab = st.tpTab && g[st.tpTab] && g[st.tpTab].length ? st.tpTab : TPT.find(([k]) => g[k].length)[0];
  return h + '<div class="tp-tabs" role="group" aria-label="Tepki türü">' +
    TPT.filter(([k]) => g[k].length).map(([k, n, ic, c]) => '<button class="tt' + (c ? ' ' + c : '') + '" data-tpt="' + k + '" aria-pressed="' + (k === tab) + '">' + ICON[ic] + '<span>' + n + '</span><b>' + g[k].length + '</b></button>').join('') + '</div>' +
    g[tab].slice(0, 40).map(p => tpRow(p, tab)).join('') + '</article>';
}
