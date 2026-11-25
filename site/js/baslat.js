// Glutensiz Kontrol — Yönlendirme, dokunma ve klavye olayları, açılış.
// Sayfanın betikleri ortak bir kapsamda, şu sırayla çalışır: temel → cevrimdisi → kisisel → ekle → veri → liste → tepki → gorunum → baslat.
// ---- yönlendirme
function route(){
  if (!D) return;  // liste daha gelmedi
  const hsh = (location.hash || '').slice(1);
  if (hsh.startsWith('k-') && CAT[hsh.slice(2)]){
    st.view = 'cat'; st.cat = hsh.slice(2);
    const d = CAT[st.cat].d; if (d !== st.dom){ st.dom = d; drawTabs(); }
    out.innerHTML = catView(st.cat, false);
    return;
  }
  st.view = st.q ? 'search' : 'home';
  if (st.q) results(st.q);
  else { if (st.dom !== st.pick){ st.dom = st.pick; drawTabs(); } home(); }
}
let tmr;
qi.addEventListener('input', () => {
  st.q = qi.value; st.noAuto = false; clearB.classList.toggle('on', !!st.q); st.open.clear();
  document.body.classList.toggle('searching', !!st.q.trim());
  clearTimeout(tmr); tmr = setTimeout(() => { if (location.hash) history.replaceState(null, '', location.pathname + location.search); route(); }, 90);
});
qi.addEventListener('keydown', e => { if (e.key === 'Enter'){ recentSave(qi.value); qi.blur(); } });
qi.addEventListener('blur', () => { if (st.q.trim()) recentSave(st.q); });
clearB.addEventListener('click', () => { recentSave(st.q); qi.value = ''; st.q = ''; clearB.classList.remove('on'); document.body.classList.remove('searching'); route(); qi.focus(); });
// sekme seçimi: kullanıcının tercihi (kalıcı); o anki aramada otomatik geçiş yapılmaz
function pickDom(d){
  st.pick = st.dom = d; st.noAuto = !!st.q; lsSet('gk-dom', d);
  drawTabs(); if (location.hash) history.replaceState(null, '', location.pathname + location.search); route();
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
  if (t.dataset.cat){ location.hash = 'k-' + t.dataset.cat; window.scrollTo(0, 0); return; }
  if (t.dataset.back){ history.length > 1 ? history.back() : (location.hash = ''); return; }
  if (t.dataset.q){ qi.value = t.dataset.q; qi.dispatchEvent(new Event('input')); return; }
  if (t.dataset.dom){ pickDom(t.dataset.dom); return; }
  if (t.dataset.brand){ st.open.add(t.dataset.brand); route(); return; }
  if (t.dataset.ob){ const k = t.dataset.ob; st.open.has(k) ? st.open.delete(k) : st.open.add(k); out.innerHTML = catView(st.cat || k.split('|')[0], st.view !== 'cat'); return; }
});
out.addEventListener('toggle', e => { if (e.target.classList && e.target.classList.contains('key')) st.keyOpen = e.target.open; }, true);
window.addEventListener('hashchange', route);
const bar = $('#bar');
const io = new IntersectionObserver(([en]) => bar.classList.toggle('stuck', !en.isIntersecting), {rootMargin:'-1px 0px 0px 0px'});
io.observe(document.querySelector('header.top'));
// liste gelmeden önce sekmeleri ve üst bölümü çiz: liste gelince sayfa kaymasın
drawTabs();
out.innerHTML = recentRow() + legend() + '<div class="loading">Listeler yükleniyor…</div>';
load();
