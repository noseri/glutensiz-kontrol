// Glutensiz Kontrol — Dernek listeleri: satır işaretleri, arama, marka kartları, kategori kutuları.
// Sayfanın betikleri ortak bir kapsamda, şu sırayla çalışır: temel → cevrimdisi → kisisel → ekle → veri → liste → tepki → gorunum → baslat.
// ---- satır işaretleri
const NEG = /(gluten\s+i̇?[çc]er(ir|iyor|mektedir|ebilir|di[gğ]i)|glutenli|alma(y[ıi]n[ıi]z|mal[ıi]y[ıi]z)|kullanma(y[ıi]n[ıi]z|mal[ıi]y[ıi]z)|kullan[ıi]lmamal[ıi]d[ıi]r|kullan[ıi]lmamal[ıi]|t[üu]ketilmemeli(dir)?|t[üu]ketmeyiniz|yememeliyiz|yasak(t[ıi]r)?)/gi;
const COND = /(hari[çc]|d[ıi][şs][ıi]nda(ki)?|olmayanlar|etiket(ini|leri|i|ine)?\s+(okuy\w*|dikkat\w*)|[üu]zeri(ni)?\s+okuy\w*|okuyarak|sadece\s+[^,.;)]{1,40}|glutensiz\s+(yazan|ibareli\w*|yaz[ıi]l[ıi]|etiketi\s+olan|etiketli)|glutensiz\s+yazmal[ıi])/gi;
const CONDT = new RegExp(COND.source, 'i');
function decorate(text, toks){
  let h = esc(text);
  h = h.replace(NEG, m => '<span class="neg">' + m + '</span>');
  h = h.replace(COND, m => /class=/.test(m) ? m : '<span class="cond">' + m + '</span>');
  return h;
}
function lineMark(l){
  if (l.k === 'warn') return ['m-no', ICON.warn, 'Gluten uyarısı — almayın'];
  if (l.k === 'read') return ['m-rd', ICON.eye, 'Onay değil: etiketi okunarak alınacak'];
  if (l.k === 'info') return ['m-rd', ICON.eye, 'Bilgi'];
  if (l.st === 'both') return ['m-ok', ICON.ok2, 'Diğer listede de var'];
  if (l.st === 'part' && l.g && (PB.has(l.i) || (LBY[l.b] || []).some(o => o.c === l.c && o.s !== l.s && o.k === 'ok'))) return ['m-part', ICON.half, 'Bu liste markanın tümünü sayıyor; diğer liste yalnızca belirli ürünleri'];
  if (l.st === 'part') return ['m-part', ICON.half, 'Marka diğer listede var, bu ürün yok'];
  return ['m-one', ICON.ok, 'Yalnızca bu listede'];
}
const KO = {ok:0, info:1, read:2, warn:3}, SO = {both:0, part:1, one:2, mixed:2};
function lineOrder(a, b){
  return (KO[a.k] ?? 1) - (KO[b.k] ?? 1) || (SO[a.st] ?? 2) - (SO[b.st] ?? 2) || (a.s === b.s ? a.i - b.i : (a.s === 'ist' ? -1 : 1));
}
function lineRow(l, toks, skip){
  const [cls, ic, tip] = lineMark(l);
  let h = D.heads[l.h];
  // başlık, kartta ayrıca gösterilen notu içeriyorsa (ör. Ankara'nın yoğurt notu) başlığı paranteze kadar kısalt
  if (h && skip && skip.length){
    const hn = norm(h);
    if (skip.some(x => hn.includes(x))){ const cut = h.split('(')[0].replace(/[\s:;,.-]+$/, ''); if (cut) h = cut; }
  }
  const tap = canTap(l);
  return '<li class="li"' + (tap ? ' data-ln="' + l.i + '"' : '') + '><span class="src" title="' + SRCN[l.s] + ' listesi">' + SRC[l.s] + '</span>' +
    '<div><div class="tx">' + decorate(l.t, toks) + '</div>' + (h ? '<div class="hd">' + SRCN[l.s] + ' · ' + esc(h) + '</div>' : '') + (tap ? rxAll(lineKeys(l)) + tpk(l.t) : '') + '</div>' +
    '<span class="mk ' + cls + '" role="img" title="' + tip + '" aria-label="' + tip + '">' + ic + '</span></li>';
}
const GST = {
  both: ['c-ok', ICON.ok2, 'İki listede de'],
  mixed: ['c-ok', ICON.half, 'Bazıları iki listede'],
  part: ['c-part', ICON.half, 'Marka iki listede, ürünler farklı'],
  ist: ['c-one', ICON.ok, 'Sadece İstanbul'],
  ank: ['c-one', ICON.ok, 'Sadece Ankara'],
  read: ['c-rd', ICON.eye, 'Etiketi okunarak'],
  warn: ['c-no', ICON.warn, 'Uyarı']
};
function chip(s){ const g = GST[s] || GST.ist; return '<span class="chip ' + g[0] + '">' + g[1] + g[2] + '</span>'; }
function groupStatus(b, c){
  const g = GBY[b + '|' + c];
  const ls = (LBY[b] || []).filter(l => l.c === c);
  if (ls.length && ls.every(l => l.k === 'warn')) return 'warn';
  if (ls.length && ls.every(l => l.k === 'read' || l.k === 'warn' || l.k === 'info')) return 'read';
  const s = g ? g.st : (ls.some(l => l.s === 'ist') ? (ls.some(l => l.s === 'ank') ? 'part' : 'ist') : 'ank');
  if (s === 'both' && ls.some(l => l.k === 'ok' && (l.st === 'part' || l.st === 'one'))) return 'mixed';
  return s;
}

// ---- arama
function tokMatch(qt, words){ return words.some(w => w.startsWith(qt)); }
function search(q){
  const qn = norm(q); if (!qn) return null;
  const qt = qn.split(' ');
  const qc = qn.replace(/ /g, '');
  const res = new Map(); // brand -> lines
  const loose = [];      // markasız eşleşen notlar
  for (const l of LN){
    if (l.d !== st.dom) continue;
    const bwords = l.b ? (BNORM[l.b] || '').split(' ').concat([l.b]) : [];
    const words = l.nn.split(' ').concat(bwords, (CAT[l.c] || {}).nn ? CAT[l.c].nn.split(' ') : [], l.hn ? l.hn.split(' ') : []);
    const ok = qt.every(t => tokMatch(t, words)) || (qc.length >= 4 && l.b && (l.b.startsWith(qc) || (BNORM[l.b] || '').replace(/ /g, '').startsWith(qc)));
    if (!ok) continue;
    if (!l.b || l.k === 'note') { loose.push(l); continue; }
    if (!res.has(l.b)) res.set(l.b, []);
    res.get(l.b).push(l);
  }
  // marka adı eşleşme gücüne göre sırala
  const score = b => {
    const n = BNORM[b] || b, nc = n.replace(/ /g, '');
    if (n === qn || nc === qc || b === qc) return 0;
    if (n.startsWith(qn) || nc.startsWith(qc)) return 1;
    if (n.split(' ').some(w => qt.some(t => w.startsWith(t)))) return 2;
    return 3;
  };
  const brands = [...res.keys()].sort((a, b) => score(a) - score(b) || res.get(b).length - res.get(a).length || (BN[a] || a).localeCompare(BN[b] || b, 'tr'));
  const cats = D.cats.filter(c => c.d === st.dom && qt.every(t => c.nn.split(' ').some(w => w.startsWith(t))) && (CATL[c.id] || []).length);
  return {qn, qt, brands, res, loose, cats, score};
}
function suggestions(qn){
  const qc = qn.replace(/ /g, ''); if (qc.length < 3) return [];
  const seen = new Set(), outS = [];
  for (const b in BNORM){
    if (!(LBY[b] || []).some(l => l.d === st.dom)) continue;
    const n = BNORM[b].replace(/ /g, '');
    const lim = qc.length >= 7 ? 2 : 1;
    const d = Math.min(lev(qc, n), lev(qc, n.slice(0, qc.length)) + (n.length > qc.length ? 0 : 9));
    if (d <= lim && !seen.has(BN[b])) { seen.add(BN[b]); outS.push([d, BN[b]]); }
  }
  return outS.sort((a, b) => a[0] - b[0]).slice(0, 6).map(x => x[1]);
}
function verdictFor(sts){
  if (sts.includes('both') || sts.includes('mixed')) return 'ok';
  if (sts.includes('part')) return 'part';
  if (sts.includes('ist') || sts.includes('ank')) return 'one';
  if (sts.includes('read')) return 'rd';
  return 'no';
}
function brandCard(b, lines, toks, full){
  const byC = new Map();
  lines.forEach(l => { if (!byC.has(l.c)) byC.set(l.c, []); byC.get(l.c).push(l); });
  const order = {both:0, mixed:1, part:2, ist:3, ank:3, read:4, warn:5};
  const isCond = l => l.k === 'ok' && (l.w || CONDT.test(l.t));
  const condC = new Set(lines.filter(isCond).map(l => l.c));
  const cs = [...byC.keys()].map(c => [c, groupStatus(b, c)]).sort((x, y) => order[x[1]] - order[y[1]] || condC.has(y[0]) - condC.has(x[0]) || CAT[x[0]].n.localeCompare(CAT[y[0]].n, 'tr'));
  const sts = cs.map(x => x[1]);
  const v = verdictFor(sts);
  const nb = sts.filter(s => s === 'both').length, n1 = sts.filter(s => s === 'ist' || s === 'ank' || s === 'part').length;
  const hasWarn = lines.some(l => l.k === 'warn');
  const hasOk = lines.some(l => l.k === 'ok');
  const sartli = condC.size > 0;
  let title, sub;
  if (hasWarn && !hasOk){
    const ic2 = ICON.warn;
    return brandCardShell(b, 'no', ic2, 'Gluten uyarısı var', 'Listelerde bu marka için uyarı satırı bulunuyor; satırları okuyun.' + dokWarn(b), cs, byC, toks, full);
  }
  const okL = lines.filter(l => l.k === 'ok');
  const pBoth = Math.max(okL.filter(l => l.st === 'both' && l.s === 'ist').length, okL.filter(l => l.st === 'both' && l.s === 'ank').length);
  const pOne = okL.filter(l => l.st === 'part' || l.st === 'one').length;
  if (v === 'ok' && pOne){ title = pBoth >= pOne ? 'Çoğu ürünü iki listede' : 'Bazı ürünleri iki listede'; sub = '<strong>' + pBoth + ' ürün iki listede</strong>, ' + pOne + ' ürün tek listede' + (sartli ? '<br>Şart var (' + [...condC].map(c => esc(CAT[c].n)).slice(0, 3).join(', ') + '): altı çizili ifadeleri okuyun.' : ''); }
  else if (v === 'ok'){ title = 'İki listede de var'; sub = nb + ' kategoride <strong>iki listede</strong>' + (n1 ? ', ' + n1 + ' kategoride tek listede' : '') + (sartli ? '<br>Şart var (' + [...condC].map(c => esc(CAT[c].n)).slice(0, 3).join(', ') + '): altı çizili ifadeleri okuyun.' : ''); }
  else if (v === 'part'){ title = 'Marka iki listede, bu ürünler tek listede'; sub = 'Ürünü kontrol edin: aşağıda iki listenin metni yan yana.'; }
  else if (v === 'one'){ const only = sts.includes('ist') && !sts.includes('ank') ? 'İstanbul' : (sts.includes('ank') && !sts.includes('ist') ? 'Ankara' : 'tek'); title = 'Yalnızca ' + (only === 'tek' ? 'tek listede' : only + ' listesinde'); sub = '<span class="k">Paketi inceleyerek</span> alın.'; }
  else if (v === 'rd'){ title = 'Onay listesinde değil — etiketi okunacak firmalar arasında'; sub = 'Dernekler bu firmanın ürünlerini ambalaj okunarak almayı öneriyor.'; }
  else { title = 'Uyarı'; sub = 'Aşağıdaki ürün(ler) için gluten uyarısı var.'; }
  if (v === 'one' && st.dom === 'ilac') sub = 'Diğer listede adı geçmiyor. Kutudaki <strong>üretici firmayı</strong> aşağıdaki listeyle karşılaştırın.';
  const ic = {ok:ICON.ok2, part:ICON.half, one:ICON.ok, rd:ICON.eye, no:ICON.warn}[v];
  return brandCardShell(b, v, ic, title, sub + (hasWarn && v !== 'no' ? ' · <span style="color:var(--no);font-weight:700">uyarı içeren satır var</span>' : '') + dokWarn(b), cs, byC, toks, full, sartli && v === 'ok');
}
function repLink(b, v){
  const r = REP[b];
  if (!r || !['ok', 'part', 'one'].includes(v)) return '';
  return '<a class="rep" href="' + esc(r.url) + '" target="_blank" rel="noopener" title="Satıcının yayınladığı laboratuvar raporları. Bilgi amaçlıdır, dernek onayı yerine geçmez; raporların çoğu parti bazlı değildir.">' +
    ICON.lab + '<span><b>Analiz raporu var</b> <span class="rs">· ' + r.n + ' rapor' + (r.last ? ', son: ' + fmtMonth(r.last) : '') + ' · Doğa Evinizde</span></span>' + ICON.ext + '</a>';
}
function brandCardShell(b, v, ic, title, sub, cs, byC, toks, full, sartli){
  const limit = full ? 99 : 4;
  let rows = '';
  cs.slice(0, limit).forEach(([c, s]) => {
    const ls = byC.get(c).slice().sort(lineOrder);
    const shown = new Set(ls.map(l => l.i)), extra = [];
    ls.forEach(l => l.st === 'both' && (l.p || []).forEach(pid => { const pl = LN[pid]; if (pl && pl.c !== c && pl.b === b && !shown.has(pid)) { shown.add(pid); extra.push(pl); } }));
    const notes = (CATL[c] || []).filter(n => n.k === 'note' && (n.af || /serbest|ko[sş]ulu|olmamas/i.test(n.t))).slice(0, 3);
    const nskip = notes.map(n => norm(n.t)).filter(x => x.length > 20);  // aynı not başlıkta da geçiyorsa bir kez göster
    rows += '<div class="crow"><div class="chead"><span class="cname">' + esc(CAT[c].n) + '</span>' + chip(s) + '</div><ul class="ls">' +
      ls.map(l => lineRow(l, toks, nskip)).join('') + extra.map(l => lineRow(l, toks, nskip)).join('') + '</ul>' +
      (extra.length ? '<p class="xc">Diğer listede bu ürün başka bir başlık altında yer alıyor.</p>' : '') +
      notes.map(n => '<div class="note' + (n.af ? ' af' : '') + '"><span class="src">' + SRC[n.s] + '</span>' + esc(n.t) + '</div>').join('') + '</div>';
  });
  const moreBtn = cs.length > limit ? '<button class="more" data-brand="' + esc(b) + '">Tüm kategoriler (' + cs.length + ')</button>' : '';
  return '<article class="card v-' + v + '"><div class="verdict"><span class="dot">' + ic + '</span><div><p class="vt">' + esc(BN[b] || b) + '</p><p class="vs"><b class="k">' + title + '</b>' + (sartli ? '<span class="sart">Şartlı</span>' : '') + (sub ? ' · ' + sub : '') + '</p></div></div>' + repLink(b, v) + '<div class="cats">' + rows + '</div>' + moreBtn + '</article>';
}
function catCounts(c){
  const bs = new Map();
  (CATL[c] || []).forEach(l => { if (l.b && (l.k === 'ok')) { const s = groupStatus(l.b, c); bs.set(l.b, s === 'mixed' ? 'both' : s); } });
  const n = {both:0, part:0, ist:0, ank:0};
  bs.forEach(s => { if (n[s] !== undefined) n[s]++; });
  return n;
}
function meter(n){
  const t = n.both + n.part + n.ist + n.ank || 1;
  return '<span class="meter" aria-hidden="true"><i class="a" style="width:' + (n.both / t * 100) + '%"></i><i class="b" style="width:' + (n.part / t * 100) + '%"></i><i class="c" style="width:' + ((n.ist + n.ank) / t * 100) + '%"></i></span>';
}
function catTile(c){
  const n = catCounts(c.id);
  const tot = n.both + n.part + n.ist + n.ank;
  const af = (CATL[c.id] || []).find(l => l.k === 'note' && l.af);
  if (!tot && af) return '<button class="cat" data-cat="' + c.id + '"><span class="n">' + esc(c.n) + '</span><span class="s" style="color:var(--ok);font-weight:700">' + SRCN[af.s] + ': ' + esc(af.t.replace(/[()]/g, '')) + '</span></button>';
  return '<button class="cat" data-cat="' + c.id + '"><span class="n">' + esc(c.n) + '</span>' + meter(n) + '<span class="s">' + n.both + ' iki listede · ' + (n.part + n.ist + n.ank) + ' tek listede</span></button>';
}
function afNotes(dom){
  const seen = new Set();
  return (LN.filter(l => l.k === 'note' && l.af && l.d === dom)).filter(l => { const k = l.c; if (seen.has(k)) return false; seen.add(k); return true; });
}
