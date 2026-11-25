// Glutensiz Kontrol — Bizim listemiz ekleme ve düzeltme formu, kategori seçici.
// Sayfanın betikleri ortak bir kapsamda, şu sırayla çalışır: temel → cevrimdisi → kisisel → ekle → veri → liste → tepki → gorunum → baslat.
// ---- ekleme / düzeltme formu
let dlg = null;
// aramadaki metinden marka ve ürünü ayır (bilinen marka adlarıyla)
function prefill(q){
  const raw = String(q || '').trim().replace(/\s+/g, ' ');
  if (!raw) return {marka: '', urun: ''};
  const qn = norm(raw);
  let best = '', bestN = '';
  const tryB = (name, n) => { if (n && n.length > bestN.length && (qn === n || qn.startsWith(n + ' '))){ best = name; bestN = n; } };
  for (const b in BNORM) tryB(BN[b] || b, BNORM[b]);
  US.urunler.forEach(it => tryB(it.marka, norm(it.marka)));
  const parts = raw.split(' ');
  if (best){
    let i = 0;
    while (i < parts.length && norm(parts.slice(0, i + 1).join(' ')).length < bestN.length) i++;
    return {marka: best, urun: parts.slice(i + 1).join(' ')};
  }
  return {marka: parts[0].charAt(0).toLocaleUpperCase('tr') + parts[0].slice(1), urun: parts.slice(1).join(' ')};
}
function buildDlg(){
  const d = document.createElement('dialog');
  d.className = 'sheet'; d.setAttribute('aria-labelledby', 'addH');
  d.innerHTML = '<form novalidate>' +
    '<h3 id="addH">Listemize ekle</h3>' +
    '<p class="lead">Dernek onayı yerine geçmez. Ürün mavi “Bizim listemiz” etiketiyle, kimin ve ne zaman eklediği yazılı olarak görünür.</p>' +
    '<fieldset class="seg"><legend>Liste</legend><div class="opts">' + DOMAINS.map(([id, n]) => '<label><input type="radio" name="alan" value="' + id + '"><span>' + n + '</span></label>').join('') + '</div></fieldset>' +
    '<label class="fl">Marka<input name="marka" maxlength="60" list="dlMarka" autocomplete="off" autocapitalize="words" enterkeyhint="next"></label>' +
    '<label class="fl">Ürün<input name="urun" maxlength="120" autocomplete="off" enterkeyhint="next" placeholder="ör. Onarıcı şampuan 400 ml"></label>' +
    '<div class="fl"><label for="fKat"><span>Kategori <span class="opt">· isteğe bağlı</span></span></label>' +
      '<div class="cb"><input id="fKat" name="kategori" maxlength="60" autocomplete="off" autocorrect="off" spellcheck="false" enterkeyhint="done" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="katList" placeholder="Seçin ya da yazmaya başlayın">' +
      '<button type="button" class="cb-x" aria-label="Kategoriyi temizle" hidden>' + ICON.x + '</button>' +
      '<button type="button" class="cb-v" aria-label="Kategorileri göster" tabindex="-1">' + ICON.down + '</button>' +
      '<ul class="cb-list" id="katList" role="listbox" aria-label="Kategoriler" hidden></ul></div></div>' +
    '<fieldset class="rad"><legend>Neye dayanarak ekliyorsunuz?</legend><div class="opts">' + DAYS.map(k => '<label><input type="radio" name="dayanak" value="' + k + '">' + (k === 'diger' ? 'Diğer (not alanına yazın)' : DAY[k]) + '</label>').join('') + '</div></fieldset>' +
    '<label class="fl"><span>Not <span class="opt">· isteğe bağlı</span></span><textarea name="notu" maxlength="280" rows="2" placeholder="ör. Parti no, nereden alındı, ne zaman bakıldı"></textarea></label>' +
    '<p class="err" role="alert"></p>' +
    '<div class="acts"><button type="button" class="btn2" data-kapat="1">Vazgeç</button><button type="submit" class="btn">Listemize ekle</button></div>' +
    '<datalist id="dlMarka"></datalist></form>';
  document.body.appendChild(d);
  const f = d.querySelector('form');
  f.addEventListener('submit', e => { e.preventDefault(); submitAdd(); });
  f.addEventListener('change', e => { if (e.target.name === 'alan') fillLists(e.target.value, true); });
  d.addEventListener('click', e => { if (e.target === d || e.target.closest('[data-kapat]')) d.close(); });
  d.addEventListener('close', () => document.documentElement.classList.remove('modal'));
  katWire(d);
  return d;
}
function fillLists(alan, changed){
  const bs = new Set();
  LN.forEach(l => { if (l.d === alan && l.b && BN[l.b]) bs.add(BN[l.b]); });
  US.urunler.forEach(it => { if (it.alan === alan) bs.add(it.marka); });
  dlg.querySelector('#dlMarka').innerHTML = [...bs].sort((a, b) => a.localeCompare(b, 'tr')).map(n => '<option value="' + esc(n) + '">').join('');
  KATS = katOptions(alan);
  // başka listeden seçilmiş bir kategori yeni listede yoksa temizle (elle yazılan kalır)
  if (changed && katPicked && !KATS.some(k => k.nn === norm(katPicked))){ dlg.querySelector('#fKat').value = ''; katPicked = ''; }
  katSync();
}
// ---- kategori seçici: yazdıkça süzülen açılır liste. İsteğe bağlı; listede olmayan bir kategori de yazılabilir.
let KATS = [], katAct = -1, katPicked = '';
function katOptions(alan){
  const seen = new Set(), res = [];
  const add = (n, own) => { const nn = norm(n); if (nn && !seen.has(nn)){ seen.add(nn); res.push({n, nn, own}); } };
  D.cats.forEach(c => { if (c.d === alan && !KAT_DIS.has(c.id) && (CATL[c.id] || []).length) add(c.n, false); });
  US.urunler.concat(US.cikarilanlar).forEach(it => { if (it.alan === alan && it.kategori) add(it.kategori, true); });
  return res.sort((a, b) => a.n.localeCompare(b.n, 'tr'));
}
const katEls = () => ({inp: dlg.querySelector('#fKat'), list: dlg.querySelector('#katList'), box: dlg.querySelector('.cb'), x: dlg.querySelector('.cb-x')});
function katMatches(q){
  const qn = norm(q); if (!qn) return KATS;
  const qt = qn.split(' ');
  return KATS.filter(k => { const w = k.nn.split(' '); return qt.every(t => w.some(x => x.startsWith(t))); })
    .sort((a, b) => (b.nn.startsWith(qn) - a.nn.startsWith(qn)) || a.n.localeCompare(b.n, 'tr'));
}
function katHl(name, q){
  const qt = norm(q).split(' ').filter(Boolean);
  if (!qt.length) return esc(name);
  return name.split(/(\s+)/).map(w => { const wn = norm(w); return wn && qt.some(t => wn.split(' ').some(x => x.startsWith(t))) ? '<mark>' + esc(w) + '</mark>' : esc(w); }).join('');
}
function katSync(){ const {inp, x} = katEls(); x.hidden = !inp.value; }
function katOpen(){
  const {inp, list, box} = katEls();
  const items = katMatches(inp.value);
  katAct = -1;
  list.innerHTML = items.length
    ? items.map((k, i) => '<li role="option" id="kat-' + i + '" data-kat="' + esc(k.n) + '" aria-selected="false">' + katHl(k.n, inp.value) + (k.own ? ' <span class="tag">bizim</span>' : '') + '</li>').join('')
    : '<li class="cb-none" role="presentation">Listede yok; yazdığınız gibi kaydedilir.</li>';
  list.hidden = false; box.dataset.open = '1';
  inp.setAttribute('aria-expanded', 'true'); inp.removeAttribute('aria-activedescendant');
}
function katClose(){
  const {inp, list, box} = katEls();
  list.hidden = true; delete box.dataset.open; katAct = -1;
  inp.setAttribute('aria-expanded', 'false'); inp.removeAttribute('aria-activedescendant');
}
function katMove(step){
  const {inp, list} = katEls();
  const opts = [...list.querySelectorAll('[role=option]')]; if (!opts.length) return;
  katAct = (katAct + step + opts.length) % opts.length;
  opts.forEach((o, i) => o.setAttribute('aria-selected', i === katAct ? 'true' : 'false'));
  opts[katAct].scrollIntoView({block: 'nearest'});
  inp.setAttribute('aria-activedescendant', opts[katAct].id);
}
function katPick(v){ const {inp} = katEls(); inp.value = v; katPicked = v; katSync(); katClose(); }
function katWire(d){
  const inp = d.querySelector('#fKat'), list = d.querySelector('#katList'), box = d.querySelector('.cb');
  inp.addEventListener('focus', () => {
    katOpen();
    // klavye açılınca liste görünsün diye alanı formun üstüne taşı
    setTimeout(() => { if (document.activeElement === inp) box.parentElement.scrollIntoView({block: 'start', behavior: 'smooth'}); }, 300);
  });
  inp.addEventListener('input', () => { katPicked = ''; katSync(); katOpen(); });
  inp.addEventListener('blur', () => setTimeout(() => { if (document.activeElement !== inp) katClose(); }, 150));
  inp.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp'){ e.preventDefault(); if (list.hidden) katOpen(); katMove(e.key === 'ArrowDown' ? 1 : -1); }
    else if (e.key === 'Enter'){
      e.preventDefault();
      const a = list.hidden ? null : list.querySelector('[aria-selected=true]');
      if (a) katPick(a.dataset.kat); else { katClose(); inp.blur(); }
    }
    else if (e.key === 'Escape' && !list.hidden){ e.preventDefault(); e.stopPropagation(); katClose(); }
  });
  list.addEventListener('mousedown', e => e.preventDefault());  // seçerken kutu odağı kaybetmesin
  list.addEventListener('click', e => { const o = e.target.closest('[data-kat]'); if (o){ katPick(o.dataset.kat); inp.blur(); } });
  const v = box.querySelector('.cb-v');
  v.addEventListener('mousedown', e => e.preventDefault());
  v.addEventListener('click', () => { if (list.hidden){ inp.focus(); katOpen(); } else { katClose(); inp.blur(); } });
  box.querySelector('.cb-x').addEventListener('click', () => { inp.value = ''; katPicked = ''; katSync(); inp.focus(); });
}
const LEAD_EKLE = 'Dernek onayı yerine geçmez. Ürün mavi “Bizim listemiz” etiketiyle, kimin ve ne zaman eklediği yazılı olarak görünür.';
const LEAD_DUZ = 'Eski kayıt silinmez: geçmişte “düzeltildi” olarak, kimin ne zaman düzelttiğiyle birlikte kalır.';
function openAdd(q, noFocus){
  if (!API || !D) return;
  dlg = dlg || buildDlg();
  const f = dlg.querySelector('form'), el = n => f.elements.namedItem(n);
  f.reset();
  delete dlg.dataset.duzelt;
  dlg.querySelector('#addH').textContent = 'Listemize ekle';
  dlg.querySelector('.lead').textContent = LEAD_EKLE;
  dlg.querySelector('.rad legend').textContent = 'Neye dayanarak ekliyorsunuz?';
  const p = prefill(q);
  el('marka').value = p.marka; el('urun').value = p.urun;
  f.querySelectorAll('input[name=alan]').forEach(r => { r.checked = r.value === st.dom; });
  katPicked = '';
  fillLists(st.dom);
  katClose();
  dlg.querySelector('.err').textContent = '';
  const b = f.querySelector('.btn'); b.disabled = false; b.textContent = 'Listemize ekle';
  document.documentElement.classList.add('modal');
  if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
  if (!p.marka && !noFocus) el('marka').focus();
}
// düzelt: aynı form, kaydın bilgileriyle dolu
function openEdit(id){
  const it = US.urunler.find(x => +x.id === id); if (!it) return;
  openAdd('', true);
  const f = dlg.querySelector('form'), el = n => f.elements.namedItem(n);
  dlg.dataset.duzelt = String(it.id);
  dlg.querySelector('#addH').textContent = 'Düzelt';
  dlg.querySelector('.lead').textContent = LEAD_DUZ;
  dlg.querySelector('.rad legend').textContent = 'Neye dayanarak?';
  f.querySelectorAll('input[name=alan]').forEach(r => { r.checked = r.value === it.alan; });
  fillLists(it.alan);
  el('marka').value = it.marka; el('urun').value = it.urun;
  el('kategori').value = it.kategori || ''; katPicked = it.kategori || ''; katSync();
  f.querySelectorAll('input[name=dayanak]').forEach(r => { r.checked = r.value === it.dayanak; });
  el('notu').value = it.notu || '';
  f.querySelector('.btn').textContent = 'Düzeltmeyi kaydet';
}
async function submitAdd(){
  const f = dlg.querySelector('form'), el = n => f.elements.namedItem(n), err = dlg.querySelector('.err'), btn = f.querySelector('.btn');
  const pick = n => { const c = f.querySelector('input[name=' + n + ']:checked'); return c ? c.value : ''; };
  const v = {alan: pick('alan'), marka: el('marka').value.trim(), urun: el('urun').value.trim(), kategori: el('kategori').value.trim(), dayanak: pick('dayanak'), notu: el('notu').value.trim()};
  const key = USKEY;
  if (!KIS()) return kilitle();
  const duzId = dlg.dataset.duzelt ? +dlg.dataset.duzelt : 0;
  const btnText = duzId ? 'Düzeltmeyi kaydet' : 'Listemize ekle';
  err.textContent = '';
  if (!v.marka || !v.urun){ err.textContent = 'Marka ve ürün adını yazın.'; (v.marka ? el('urun') : el('marka')).focus(); return; }
  if (!v.dayanak){ err.textContent = 'Neye dayanarak eklediğinizi seçin.'; return; }
  if (v.dayanak === 'diger' && !v.notu){ err.textContent = '“Diğer” seçtiyseniz nedenini not alanına yazın.'; el('notu').focus(); return; }
  btn.disabled = true; btn.textContent = duzId ? 'Kaydediliyor…' : 'Ekleniyor…';
  try {
    const r = await fetch(API + (duzId ? '/duzelt' : '/ekle'), {method: 'POST', headers: Object.assign({'Content-Type': 'application/json'}, authH(key)), body: JSON.stringify(duzId ? Object.assign({id: duzId}, v) : v)});
    let j = {}; try { j = await r.json(); } catch (x) {}
    if (duzId && r.status === 200 && j.yeni && j.eski){
      USNAME = j.yeni.ekleyen; lsSet('gk-ad', USNAME);
      usApply([j.yeni].concat(US.urunler.filter(x => +x.id !== duzId && +x.id !== +j.yeni.id)), [j.eski].concat(US.cikarilanlar.filter(x => +x.id !== duzId)));
      dlg.close();
      if (j.yeni.alan !== st.dom && !st.q){ st.pick = st.dom = j.yeni.alan; lsSet('gk-dom', st.pick); drawTabs(); }
      rerender();
      const row = document.getElementById('us-' + (+j.yeni.id));
      if (row){ row.classList.add('new'); row.scrollIntoView({block: 'nearest', behavior: 'smooth'}); }
      toast('Düzeltildi · ' + j.yeni.ekleyen + ' · ' + fmtWhen(j.yeni.eklendi));
      return;
    }
    if (!duzId && r.status === 201 && j.urun){
      USNAME = j.urun.ekleyen; lsSet('gk-ad', USNAME);
      usApply([j.urun].concat(US.urunler.filter(x => +x.id !== +j.urun.id)), US.cikarilanlar);
      dlg.close();
      if (j.urun.alan !== st.dom && !st.q){ st.pick = st.dom = j.urun.alan; lsSet('gk-dom', st.pick); drawTabs(); }
      rerender();
      const row = document.getElementById('us-' + (+j.urun.id));
      if (row){ row.classList.add('new'); row.scrollIntoView({block: 'nearest', behavior: 'smooth'}); }
      toast('Listemize eklendi · ' + j.urun.ekleyen + ' · ' + fmtWhen(j.urun.eklendi));
      return;
    }
    if (r.status === 401) return kilitle('Şifre tanınmadı; Giriş’ten yeniden girin.');
    if (r.status === 409 && j.urun){
      err.textContent = (duzId ? 'Bu adla başka bir ürün zaten listede: ' : 'Bu ürün zaten listede: ') + j.urun.ekleyen + ' ekledi · ' + fmtWhen(j.urun.eklendi) + '.';
      loadUs(true);
    } else if (duzId && r.status === 404){
      err.textContent = j.hata || 'Bu ürün listede değil; az önce çıkarılmış ya da düzeltilmiş olabilir.';
      loadUs(true);
    } else {
      err.textContent = j.hata || ((duzId ? 'Düzeltilemedi' : 'Eklenemedi') + ' (hata ' + r.status + '). Biraz sonra yeniden deneyin.');
    }
  } catch (e) {
    err.textContent = netErr(e);
  }
  btn.disabled = false; btn.textContent = btnText;
}
