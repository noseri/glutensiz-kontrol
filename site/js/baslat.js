// Glutensiz Kontrol — Yönlendirme, gezinti (geri hareketi, ana sayfaya dönüş), dokunma ve klavye olayları, açılış.
// Sayfanın betikleri ortak bir kapsamda, şu sırayla çalışır: temel → cevrimdisi → kisisel → ekle → veri → liste → tepki → gorunum → baslat.
// ---- yönlendirme
let rotaHash = null;  // son çizilen ekranın adresi: bir geçişte ekran iki kez çizilmesin
function route(){
  if (!D) return;  // liste daha gelmedi
  rotaHash = location.hash;
  const hsh = rotaHash.slice(1);
  if (hsh.startsWith('k-') && CAT[hsh.slice(2)]){
    st.view = 'cat'; st.cat = hsh.slice(2);
    const d = CAT[st.cat].d; if (d !== st.dom){ st.dom = d; drawTabs(); }
    out.innerHTML = catView(st.cat, false);
  } else {
    st.view = st.q ? 'search' : 'home';
    if (st.q) results(st.q);
    else { if (st.dom !== st.pick){ st.dom = st.pick; drawTabs(); } home(); }
  }
  document.body.classList.toggle('icerde', st.view !== 'home');  // arama kutusunda ← ve altta "Yeni arama"
}

// ---- gezinti
// Her ekran geçmişte bir adımdır: ana sayfa → arama {gk:'ara', q} → kategori #k-… {gk:'kat', q}.
// d: ana sayfanın kaç adım üstünde olunduğu; y: o adımdan ayrılırken sayfanın kaydırma yeri (geri gelince aynı yer).
// Böylece iPhone'da ekranın sol kenarından sağa kaydırınca (Android'de geri tuşuyla) bir önceki ekrana dönülür.
// ←, başlık ve "Yeni arama" doğrudan ana sayfaya götürür; geride boşa giden adım bırakmaz.
if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
const YOL = () => location.pathname + location.search;
const derin = () => (history.state && history.state.d) || 0;
let tmr, geriT, simdiki = null, bizGeri = false;
function adimYaz(yeni, s, url){
  history[yeni ? 'pushState' : 'replaceState'](s, '', url);
  simdiki = {s: history.state, u: location.href};  // açık pencere varken gelen geri hareketini geri almak için
}
function adimAc(s, url){
  adimYaz(false, Object.assign({}, history.state, {y: Math.round(window.scrollY)}), location.href);
  adimYaz(true, Object.assign({d: derin() + 1}, s), url);
}
function geriGit(n){  // sayfanın kendi istediği geri adımı; ekranı popstate çizer
  bizGeri = true; clearTimeout(geriT); geriT = setTimeout(() => { bizGeri = false; }, 1500);
  history.go(-n);
}
function aramaYaz(q){
  qi.value = q; st.q = q; st.noAuto = false; st.open.clear();
  clearB.classList.toggle('on', !!q); document.body.classList.toggle('searching', !!q.trim());
}
// arama kutusu değişince: ilk harfte yeni adım açılır, yazdıkça aynı adım güncellenir
function aramaAdimi(){
  const s = history.state || {}, d = s.d || 0, q = st.q;
  if (q.trim()){
    if (s.gk === 'ara' || location.hash) adimYaz(false, {gk: 'ara', q, d}, YOL());
    else adimAc({gk: 'ara', q}, YOL());
  } else if (s.gk === 'ara' || location.hash){
    if (s.gk === 'ara' && d === 1) geriGit(1);  // arama silindi: ana sayfaya dönülür, geride boş adım kalmaz
    else adimYaz(false, d ? {gk: 'ara', q: '', d} : null, YOL());
  }
}
// ana sayfa: arama temizlenir, sayfanın başına gidilir
function eveDon(){
  if (bizGeri) return;  // dönüş zaten yolda
  clearTimeout(tmr);
  if (st.q.trim()) recentSave(st.q);
  aramaYaz('');
  const d = derin();
  if (d > 0 && history.length > d) return geriGit(d);
  if (location.hash || history.state) adimYaz(false, null, YOL());
  route(); window.scrollTo(0, 0);
}
// açık pencereler: içinde bir şey değiştirildiyse (yazı, seçim, düğme) kendiliğinden kapanmaz
const pencereler = () => [...document.querySelectorAll('dialog[open]')];
const kirli = () => pencereler().some(p => p.dataset.kirli);
function kirlet(e){
  const p = e.target.closest && e.target.closest('dialog');
  if (p && (e.type !== 'click' || e.target.closest('button:not([data-kapat]), input, select, textarea, label, [role=option], [data-kat]'))) p.dataset.kirli = '1';
}
['input', 'change', 'click'].forEach(t => document.addEventListener(t, kirlet, true));
document.addEventListener('close', e => { if (e.target.dataset) delete e.target.dataset.kirli; }, true);
window.addEventListener('popstate', () => {
  clearTimeout(tmr); clearTimeout(geriT);
  const biz = bizGeri; bizGeri = false;
  if (!biz && pencereler().length){
    // açık pencere varken geri hareketi (iPhone'da kenardan kaydırma) yalnızca pencereyi kapatır, ekran yerinde kalır;
    // pencerede yazılmış bir şey varsa pencere de açık kalır
    adimYaz(true, simdiki.s, simdiki.u);
    if (!kirli()) pencereler().forEach(p => p.close());
    return;
  }
  const s = history.state || {};
  simdiki = {s: history.state, u: location.href};
  if (biz && !s.gk && qi.value.trim()){ st.q = qi.value; aramaAdimi(); route(); return; }  // silip hemen yeniden yazmaya başladıysa
  aramaYaz(s.gk ? s.q || '' : '');
  route();
  window.scrollTo(0, biz ? 0 : s.y || 0);
});
window.addEventListener('hashchange', () => { if (location.hash !== rotaHash) route(); });
// uygulamaya dönünce: 2 dakikadan uzun arka planda kaldıysa temiz ana sayfa (markette sıradaki ürüne hazır).
// Kısa geçişlerde (mesaja bakıp dönmek) ekran olduğu gibi kalır.
const TAZE_MS = 120000;
let gizlendi = 0;
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden'){ gizlendi = Date.now(); lsSet('gk-gizli', String(gizlendi)); return; }
  const uzun = gizlendi && Date.now() - gizlendi > TAZE_MS;
  gizlendi = 0;
  if (!uzun || !D || kirli()) return;
  pencereler().forEach(p => p.close());
  eveDon();
});
$('#geri').addEventListener('click', eveDon);
$('#ana').addEventListener('click', e => { e.preventDefault(); eveDon(); });
$('#yeni').addEventListener('click', () => { eveDon(); qi.focus(); });  // başparmağın ulaştığı yerde: aramayı temizle, klavyeyi aç

// ---- arama kutusu
qi.addEventListener('input', () => {
  st.q = qi.value; st.noAuto = false; clearB.classList.toggle('on', !!st.q); st.open.clear();
  document.body.classList.toggle('searching', !!st.q.trim());
  clearTimeout(tmr); tmr = setTimeout(() => { aramaAdimi(); route(); }, 90);
});
qi.addEventListener('keydown', e => { if (e.key === 'Enter'){ recentSave(qi.value); qi.blur(); } });
// yazarken alttaki "Yeni arama" gizlenir (klavyenin üstünde boşuna durmasın)
qi.addEventListener('focus', () => document.body.classList.add('yaziyor'));
qi.addEventListener('blur', () => {
  setTimeout(() => { if (document.activeElement !== qi) document.body.classList.remove('yaziyor'); }, 200);  // × düğmesinde göz kırpmasın
  if (st.q.trim()) recentSave(st.q);
});
clearB.addEventListener('click', () => { recentSave(st.q); aramaYaz(''); aramaAdimi(); route(); qi.focus(); });
// sekme seçimi: kullanıcının tercihi (kalıcı); o anki aramada otomatik geçiş yapılmaz
function pickDom(d){
  st.pick = st.dom = d; st.noAuto = !!st.q; lsSet('gk-dom', d);
  drawTabs();
  if (location.hash){ const n = derin(); adimYaz(false, st.q.trim() || n ? {gk: 'ara', q: st.q, d: n} : null, YOL()); }  // kategori kapanır
  route();
}
$('#tabs').addEventListener('click', e => {
  const b = e.target.closest('[data-dom]'); if (!b || !D) return;
  pickDom(b.dataset.dom);
});
out.addEventListener('click', e => {
  // ürün satırına dokununca tepki penceresi (düğme ve bağlantılar hariç)
  const rxEl = e.target.closest('.li[data-ln], .us-it[data-us]');
  if (rxEl && (!e.target.closest('button, a, summary') || e.target.closest('.tpk'))){
    if (st.q.trim()) recentSave(st.q);
    if (rxEl.dataset.ln) openTp('l', +rxEl.dataset.ln); else openTp('b', +rxEl.dataset.us);
    return;
  }
  const t = e.target.closest('button,[data-cat]'); if (!t) return;
  if (st.q.trim()) recentSave(st.q);  // sonuçla ilgilenildi: aramayı son aramalara ekle
  if (usClick(t)) return;
  if (t.dataset.sonsil){ lsSet('gk-son', null); route(); return; }
  if (t.dataset.cat){ adimAc({gk: 'kat', q: st.q}, '#k-' + t.dataset.cat); route(); window.scrollTo(0, 0); return; }
  if (t.dataset.back){ if (derin() > 0) history.back(); else eveDon(); return; }  // "Tüm kategoriler" / "Aramaya dön"
  if (t.dataset.q){ qi.value = t.dataset.q; qi.dispatchEvent(new Event('input')); return; }
  if (t.dataset.dom){ pickDom(t.dataset.dom); return; }
  if (t.dataset.brand){ st.open.add(t.dataset.brand); route(); return; }
  if (t.dataset.ob){ const k = t.dataset.ob; st.open.has(k) ? st.open.delete(k) : st.open.add(k); out.innerHTML = catView(st.cat || k.split('|')[0], st.view !== 'cat'); return; }
});
out.addEventListener('toggle', e => { if (e.target.classList && e.target.classList.contains('key')) st.keyOpen = e.target.open; }, true);
const bar = $('#bar');
const io = new IntersectionObserver(([en]) => {
  bar.classList.toggle('stuck', !en.isIntersecting);
  document.body.classList.toggle('asagi', !en.isIntersecting);  // sayfa kaydırıldı: altta "Yeni arama"
}, {rootMargin:'-1px 0px 0px 0px'});
io.observe(document.querySelector('header.top'));
// iPhone uzun süre arka planda kalan uygulamayı kapatıp yeniden açabilir: o zaman da 2 dakikadan uzun aradan sonra
// son ekran değil ana sayfa açılır. Tarayıcıda açılan kategori adresi (paylaşılan bağlantı) olduğu gibi kalır.
if (STANDALONE && (location.hash || (history.state && history.state.gk)) && Date.now() - (+lsGet('gk-gizli') || 0) > TAZE_MS) history.replaceState(null, '', YOL());
simdiki = {s: history.state, u: location.href};
// liste gelmeden önce sekmeleri ve üst bölümü çiz: liste gelince sayfa kaymasın
drawTabs();
out.innerHTML = recentRow() + legend() + '<div class="loading">Listeler yükleniyor…</div>';
load();
