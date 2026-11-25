// Glutensiz Kontrol — Görünümler: son aramalar, sekmeler, ana sayfa, renk anahtarı, arama sonuçları, kategori sayfası.
// Sayfanın betikleri ortak bir kapsamda, şu sırayla çalışır: temel → cevrimdisi → kisisel → ekle → veri → liste → tepki → gorunum → baslat.
// ---- son aramalar (telefonda saklanır; markette aynı ürüne tekrar bakmak tek dokunuş)
function recentGet(){
  try { const a = JSON.parse(lsGet('gk-son') || '[]'); return Array.isArray(a) ? a.filter(x => typeof x === 'string').slice(0, 6) : []; } catch (e) { return []; }
}
function recentSave(q){
  q = String(q || '').trim().replace(/\s+/g, ' ');
  const n = norm(q);
  if (q.length < 2 || q.length > 40 || !n) return;
  lsSet('gk-son', JSON.stringify([q].concat(recentGet().filter(x => norm(x) !== n)).slice(0, 6)));
}
function recentRow(){
  const a = recentGet();
  if (!a.length) return '';
  return '<div class="recent"><span class="rl">Son aramalar</span>' + a.map(x => '<button class="sg" data-q="' + esc(x) + '">' + esc(x) + '</button>').join('') +
    '<button class="lnk" data-sonsil="1">temizle</button></div>';
}

// ---- görünümler
function drawTabs(){
  $('#tabs').innerHTML = DOMAINS.map(([id, n]) => '<button class="tab" aria-pressed="' + (st.dom === id) + '" data-dom="' + id + '">' + n + '</button>').join('');
}
function legend(){
  const rows = [
    ['v-ok', ICON.ok2, 'İki listede', 'Yeşil — iki listede de', 'Önceliğiniz: hem İstanbul hem Ankara onaylı.'],
    ['v-one', ICON.ok, 'Tek listede', 'Sarı — tek listede', 'Yalnızca bir dernek onaylı: paketi inceleyerek alın.'],
    ['v-no', ICON.no, 'Listede yok', 'Kırmızı — hiçbir listede yok', 'Kuralınıza göre almıyorsunuz.']
  ];
  if (KIS()) rows.push(['v-us', ICON.us, 'Bizim listemiz', 'Mavi — bizim listemiz', 'Sizin eklediğiniz ürünler; dernek onayı değil. Kimin, ne zaman eklediği yazılı.']);
  return '<details class="key"' + (st.keyOpen ? ' open' : '') + '><summary><span class="kg">' +
    rows.map(r => '<span class="kc ' + r[0] + '"><span class="dot" aria-hidden="true">' + r[1] + '</span>' + r[2] + '</span>').join('') +
    '</span><span class="kq">Renkler ne anlama geliyor?' + ICON.down + '</span></summary>' +
    '<div class="legend">' + rows.map(r => '<div class="lg ' + r[0] + '"><span class="dot" aria-hidden="true">' + r[1] + '</span><div><b>' + r[3] + '</b><span>' + r[4] + '</span></div></div>').join('') + '</div></details>';
}
// son 8 gün içinde liste değiştiyse ana sayfanın tepesinde göster
function weekChanges(){
  const e = (D.changes || [])[0];
  if (!e || !(e.added.length + e.removed.length)) return '';
  const age = (Date.now() - new Date(e.date + 'T12:00:00+03:00').getTime()) / 864e5;
  if (!(age <= 8)) return '';
  const row = (x, add) => '<li>' + (add ? '+' : '−') + ' <span class="src">' + SRC[x.s] + '</span> ' + (add ? esc(x.t) : '<s>' + esc(x.t) + '</s>') +
    ((CAT[x.c] || {}).n ? ' <span class="cn">· ' + esc(CAT[x.c].n) + '</span>' : '') + '</li>';
  const items = e.added.slice(0, 8).map(x => row(x, true)).join('') + e.removed.slice(0, 8).map(x => row(x, false)).join('');
  const more = e.added.length > 8 || e.removed.length > 8 ? '<p class="more">Tamamı aşağıda, “Son değişiklikler” bölümünde.</p>' : '';
  return '<div class="sec"><span>Bu hafta değişenler</span><span>' + fmtDate(e.date) + '</span></div>' +
    '<div class="card wk"><p class="wk-h"><b>' + e.added.length + '</b> satır eklendi · <b>' + e.removed.length + '</b> satır çıkarıldı</p><ul class="chg">' + items + '</ul>' + more + '</div>';
}
function home(){
  const cats = D.cats.filter(c => c.d === st.dom && (CATL[c.id] || []).some(l => l.k === 'ok' || (l.k === 'note' && l.af)));
  cats.sort((a, b) => a.n.localeCompare(b.n, 'tr'));
  let h = recentRow() + legend() + weekChanges() + tpHome() + usHome();
  const af = afNotes(st.dom);
  if (st.dom === 'ilac') h += ilacFirms();
  h += '<div class="sec"><span>Kategoriler</span><span>' + cats.length + '</span></div><div class="grid">' + cats.map(catTile).join('') + '</div>';
  if (af.length) h += '<details class="fold"><summary>Ankara’nın “tüm markalar serbest” dediği kategoriler</summary><div class="fbody">' + af.map(n => '<p><b>' + esc(CAT[n.c].n) + ':</b> ' + esc(n.t) + '</p>').join('') + '<p class="small">Bu kategorilerde listede adı geçmeyen markalar da Ankara listesine göre serbest sayılıyor.</p></div></details>';
  h += infoBlocks();
  out.innerHTML = h;
}
function ilacFirms(){
  const fs = LN.filter(l => l.c === 'ilac-firma' && l.k === 'ok');
  const by = new Map();
  fs.forEach(l => { const k = l.b; if (!by.has(k)) by.set(k, []); by.get(k).push(l); });
  const rows = [...by.entries()].sort((a, b) => (BN[a[0]] || a[0]).localeCompare(BN[b[0]] || b[0], 'tr')).map(([b, ls]) => {
    const s = groupStatus(b, 'ilac-firma');
    return '<div class="crow"><div class="chead"><span class="cname">' + esc(BN[b] || b) + '</span>' + chip(s) + '</div><ul class="ls">' + ls.map(l => lineRow(l, [])).join('') + '</ul></div>';
  }).join('');
  return '<div class="sec"><span>Tüm ilaçları glutensiz sayılan firmalar</span></div><article class="card v-ok"><div class="verdict"><span class="dot">' + ICON.ok2 + '</span><div><p class="vt">Kutudaki üretici firmaya bakın</p><p class="vs">İlaç adı listede yoksa bile üreticisi bu firmalardansa dernek(ler) glutensiz sayıyor.</p></div></div><div class="cats">' + rows + '</div></article>';
}
function infoBlocks(){
  const s = D.sources;
  const src = ['ist', 'ank'].map(k => s[k].pages.map(p => '<a href="' + esc(p.url) + '" target="_blank" rel="noopener"><span><b>' + esc(s[k].city) + '</b> · ' + esc(p.title) + '</span><span>' + fmtDate(p.modified) + '</span></a>').join('')).join('');
  const ch = D.changes || [];
  const chHtml = ch.length ? ch.map(e => '<p><b>' + fmtDate(e.date) + '</b></p><ul class="chg">' +
      e.added.slice(0, 40).map(x => '<li>+ <span class="src">' + SRC[x.s] + '</span> ' + esc(x.t) + '</li>').join('') +
      e.removed.slice(0, 40).map(x => '<li>− <span class="src">' + SRC[x.s] + '</span> <s>' + esc(x.t) + '</s></li>').join('') + '</ul>').join('')
    : '<p>İlk sürüm. Listeler bundan sonra her hafta otomatik kontrol edilecek; eklenen ve çıkarılan ürünler burada görünecek.</p>';
  const ex = D.extras || {};
  const inst = STANDALONE ? '' : '<details class="fold"><summary>Telefona uygulama gibi ekleyin</summary><div class="fbody">' +
      '<p><b>iPhone:</b> Safari’de açın → Paylaş düğmesi → <b>Ana Ekrana Ekle</b>.</p>' +
      '<p><b>Android:</b> Chrome’da açın → sağ üstteki menü → <b>Ana ekrana ekle</b> (ya da <b>Uygulamayı yükle</b>).</p>' +
      '<p class="small">Bir kez açtıktan sonra liste telefona kaydedilir; markette internet çekmese de arama çalışır. İnternet varken her açılışta güncel liste alınır.</p></div></details>';
  return '<div class="sec"><span>Kaynaklar ve diğer bölümler</span></div>' + inst +
    '<details class="fold"><summary>Son değişiklikler</summary><div class="fbody">' + chHtml + '</div></details>' +
    '<details class="fold"><summary>Kaynak listeler ve son güncelleme tarihleri</summary><div class="fbody"><div class="src-l">' + src + '</div><p class="small">Tarihler derneklerin sitesindeki sayfanın son düzenlenme tarihidir.</p></div></details>' +
    '<details class="fold"><summary>Ek kaynaklar (bilgi amaçlı, onay yerine geçmez)</summary><div class="fbody">' +
      '<p><a href="https://www.dogaevinizde.com/gluten-analiz-raporlari" target="_blank" rel="noopener"><b>Gluten analiz raporları</b></a> · Doğa Evinizde. 18 markanın laboratuvar raporları (PDF). Listelerde de geçen markaların kartında “Analiz raporu var” bağlantısı görünür. Raporların çoğu parti bazlı değil; elinizdeki paketin raporu olmayabilir.</p>' +
      '<p><a href="https://guvenilirgida.tarimorman.gov.tr/gkd" target="_blank" rel="noopener"><b>Taklit veya tağşiş yapılan gıdalar</b></a> · Tarım ve Orman Bakanlığı. Site otomatik taramaya kapalı olduğu için burada izlenmiyor; marka adıyla elle aranabilir ya da Bakanlığın Güvenilir Gıda uygulamasından bakılabilir.</p>' +
      '</div></details>' +
    '<details class="fold" id="ext"><summary>Ankara listesi: glutensiz mekânlar, oteller, üniversiteler</summary><div class="fbody">' +
      '<p class="small">Bu bölümler yalnızca Ankara listesinde var; karşılaştırma yapılmadı.</p>' +
      '<p><b>Mekânlar (' + (ex.mekan || []).length + ')</b></p>' + (ex.mekan || []).map(v => '<div class="venue"><b>' + esc(v.name) + '</b><span>' + esc(v.details.join(' · ')) + '</span></div>').join('') +
      '<p style="margin-top:14px"><b>Oteller (' + (ex.otel || []).length + ')</b></p>' + (ex.otel_note ? '<p class="small">' + esc(ex.otel_note) + '</p>' : '') + (ex.otel || []).map(v => '<div class="venue"><b>' + esc(v.name) + '</b><span>' + esc(v.details.join(' · ')) + '</span></div>').join('') +
      '<p style="margin-top:14px"><b>Glutensiz menüsü olan üniversiteler</b></p><p>' + esc((ex.universite || []).join(', ')) + '</p></div></details>' +
    '<details class="fold"><summary>Nasıl çalışır?</summary><div class="fbody">' +
      '<p>Sayfa iki derneğin listesini satır satır okur, her satırın markasını ve kategorisini bulur, sonra diğer listede aynı markanın aynı ürününü arar.</p>' +
      '<p><span class="kbd">Yeşil çift tik</span>: aynı ürün (ya da markanın o kategorideki tüm ürünleri) diğer listede de var. <span class="kbd">Sarı çizgi</span>: marka diğer listede var ama bu ürün yok. <span class="kbd">Sarı tik</span>: yalnızca bu listede. <span class="kbd">Göz</span>: onay değil, “etiketi okunarak alınacak” firmalar. <span class="kbd">Kırmızı üçgen</span>: listede gluten uyarısı.</p>' +
      '<p>Eşleştirme temkinlidir: emin olamadığında “tek listede” der. Her satır listedeki orijinal metindir; altı çizili ifadeler koşul (hariç, sadece, etiketi okuyun), kırmızı ifadeler gluten uyarısıdır. Listeler her pazartesi kontrol edilir; son kontrol 2 haftadan eskiyse (ör. uzun süre internetsiz kalındıysa) başlıktaki tarih sarı görünür ve kaç gün olduğu yazar.</p>' +
      (KIS() ? '<p><span class="kbd">Mavi yer imi</span>: “Bizim listemiz”, yani sizin eklediğiniz ürünler. Dernek onayı değildir ve yeşil/sarı/kırmızı kararı değiştirmez. Kimin eklediğini telefondaki ekleme şifresi, tarihi sunucunun saati belirler; kayıt sonradan değiştirilemez. Listeden çıkarılan ürünler “Geçmiş” bölümünde kimin, ne zaman çıkardığıyla birlikte kalır. Elle eklenen ürün 6 aydır kontrol edilmediyse yanında sarı “paketi yeniden okuyun” uyarısı çıkar; paketi okuyup “Kontrol ettim”e dokunduğunuzda kimin, ne zaman kontrol ettiği yazılır.</p>' : '') +
      (KIS() ? '<p><span class="kbd">Tepkiler</span>: bir ürün satırına dokunarak beğendim, beğenmedim ya da favori diyebilirsiniz; satırda baş harflerle görünür, ana sayfada “Tepkilerimiz” altında toplanır; “İkimiz de” ikinizin de beğendiklerini gösterir. Tat bilgisi güvenlik kararını değiştirmez.</p><p><span class="kbd">Bize dokundu</span>: listede olsa bile rahatsızlık yapan ürün için tarih, ne olduğu, olası neden (çapraz bulaşma mı, gluten dışı bir şey mi ağır geldi) ve paket bilgisiyle (parti no, son kullanma tarihi, üretici) kayıt tutulur; ürünün ve markanın yanında ikinizde de uyarı olarak görünür. Kendi kaydınızı silebilirsiniz.</p><p>Bu bölümler yalnızca şifresi girilmiş telefonlarda görünür; herkese açık sayfada ve depoda yer almaz.</p>' : '') +
      '</div></details>' +
    '<p class="foot">Dernekler, üreticilerin üretim koşullarını haber vermeden değiştirebildiğini ve listede olsa bile ambalajdaki alerjen bilgisinin okunması gerektiğini belirtiyor. Bu sayfa listeleri birleştirir; onay vermez.</p>' +
    (API && !KIS() ? '<p class="giris"><button class="lnk" data-giris="1">Bizim listemiz · giriş</button></p>' : '');
}
function results(q){
  // her arama kullanıcının seçtiği sekmeden başlar; aşağıdaki otomatik geçiş yalnızca bu arama içindir
  if (st.dom !== st.pick){ st.dom = st.pick; drawTabs(); }
  let r = search(q);
  if (!r) return home();
  let h = '';
  // bu sekmede hiç sonuç yoksa diğer sekmelere bak (ör. Gıda'da "Parol" → İlaç); sekme elle seçildiyse bakma
  if (!r.brands.length && !r.cats.length && !st.noAuto){
    const from = st.dom;
    let moved = null;
    for (const [d, n] of DOMAINS){
      if (d === from) continue;
      st.dom = d;
      const r2 = search(q);
      if (r2 && (r2.brands.length || r2.cats.length)){ r = r2; moved = n; break; }
    }
    if (moved){
      drawTabs();
      h += '<p class="small moved">“' + esc(q.trim()) + '” ' + DOMAINS.find(d => d[0] === from)[1] + ' sekmesinde yok; <b>' + moved + '</b> listesinde gösteriliyor.</p>';
    } else st.dom = from;
  }
  // bizim listemizdeki eşleşmeler (tüm sekmelerde)
  const us = searchUs(q);
  const usBlock = us.length ? '<div class="sec"><span>Bizim listemiz</span><span>' + us.length + '</span></div>' + usCard(us.slice(0, 30)) : '';
  const addLine = KIS() ? '<p class="addline"><button class="lnk us" data-ekle="' + esc(q.trim()) + '">＋ Aradığınız ürün yoksa listemize ekleyin</button></p>' : '';
  // kategori adıyla eşleşme
  const catOnly = r.cats.length && !r.brands.some(b => r.score(b) <= 1);
  if (catOnly){
    const best = r.cats.slice().sort((a, b) => (a.nn.split(' ')[0] === r.qt[0] ? 0 : 1) - (b.nn.split(' ')[0] === r.qt[0] ? 0 : 1) || a.nn.length - b.nn.length)[0];
    const others = r.cats.filter(c => c !== best);
    st.cat = best.id;
    out.innerHTML = h + usBlock + catView(best.id, true) + (others.length ? '<div class="sec"><span>İlgili kategoriler</span></div><div class="grid">' + others.slice(0, 6).map(catTile).join('') + '</div>' : '') + addLine;
    return;
  }
  const exact = r.brands.filter(b => r.score(b) === 0);
  const strong = r.brands.filter(b => r.score(b) <= 2);
  const weak = r.brands.filter(b => r.score(b) === 3);
  const catHtml = r.cats.length ? '<div class="sec"><span>Kategori</span></div><div class="grid">' + r.cats.slice(0, 6).map(catTile).join('') + '</div>' : '';
  if (!exact.length) h += catHtml;
  if (r.brands.length){
    const cards = strong.length ? strong : weak;
    const rest = strong.length ? weak : [];
    h += '<div class="sec"><span><b>' + cards.length + '</b> marka</span><span>' + DOMAINS.find(d => d[0] === st.dom)[1] + '</span></div>';
    cards.slice(0, 30).forEach(b => { h += brandCard(b, r.res.get(b), r.qt, st.open.has(b)); });
    if (cards.length > 30) h += '<p class="small">İlk 30 marka gösteriliyor; aramayı daraltın.</p>';
    if (rest.length){
      h += '<div class="sec"><span>Ürün adında geçenler</span><span>' + rest.length + '</span></div><div class="card">' +
        rest.slice(0, 40).map(b => {
          const ls = r.res.get(b), cs = [...new Set(ls.map(l => l.c))];
          const so = {both:0, mixed:1, part:2, ist:3, ank:3, read:4, warn:5};
          const s0 = cs.map(c => groupStatus(b, c)).sort((x, y) => so[x] - so[y])[0];
          return '<button class="brow" data-q="' + esc(BN[b] || b) + '"><span class="lft"><span class="bn">' + esc(BN[b] || b) + '</span><span class="pv">' + esc(ls.map(l => l.t).join(' · ')) + '</span></span>' + chip(s0) + '</button>';
        }).join('') + '</div>';
    }
  }
  const none = !r.brands.length && !r.cats.length;
  if (!none) h += usBlock;
  if (exact.length) h += catHtml;
  if (st.dom === 'ilac' && r.brands.length) h += ilacFirms();
  if (r.loose.length){
    h += '<div class="sec"><span>Notlarda geçiyor</span></div><div class="card"><div class="cats">' + r.loose.slice(0, 8).map(l => '<div class="crow"><div class="chead"><span class="cname">' + esc(CAT[l.c].n) + '</span></div><ul class="ls">' + lineRow(l, r.qt) + '</ul></div>').join('') + '</div></div>';
  }
  let other = [];
  if (none){
    const sg = suggestions(r.qn);
    other = DOMAINS.filter(d => d[0] !== st.dom).map(d => [d, LN.filter(l => l.d === d[0] && r.qt.every(t => l.nn.split(' ').some(w => w.startsWith(t)))).length]).filter(x => x[1]);
    h += usBlock;
    if (other.length){
      // sekme elle seçildi; burada yok ama başka listelerde var: kırmızı karar verme
      h += '<article class="card"><div class="verdict"><span class="dot" style="background:var(--soft);color:var(--mut)">' + ICON.eye + '</span><div><p class="vt">“' + esc(q.trim()) + '” ' + DOMAINS.find(d => d[0] === st.dom)[1] + ' listesinde yok</p><p class="vs">Başka listelerde sonuç var:</p></div></div>' +
        '<div class="sugg">' + other.map(([d, n]) => '<button class="sg" data-dom="' + d[0] + '">' + d[1] + ' listesinde ' + n + ' sonuç</button>').join('') + '</div></article>';
    } else {
    h += '<article class="card v-no"><div class="verdict"><span class="dot">' + ICON.no + '</span><div>' +
      (us.length ? '<p class="vt">“' + esc(q.trim()) + '” dernek listelerinde yok</p><p class="vs"><b class="k">Derneklerde bulunamadı</b> · Yalnızca bizim listemizde var (yukarıda).</p>'
        : '<p class="vt">“' + esc(q.trim()) + '” hiçbir listede yok</p><p class="vs"><b class="k">Hiçbir listede bulunamadı</b> · Kuralınıza göre almıyorsunuz.</p>') + '</div></div>' +
      (sg.length ? '<div class="empty" style="padding-top:0">Yazım farkı olabilir — bunu mu demek istediniz?</div><div class="sugg">' + sg.map(s => '<button class="sg" data-q="' + esc(s) + '">' + esc(s) + '</button>').join('') + '</div>' : '') +
      (other.length ? '<div class="sugg">' + other.map(([d, n]) => '<button class="sg" data-dom="' + d[0] + '">' + d[1] + ' listesinde ' + n + ' sonuç</button>').join('') + '</div>' : '') +
      (KIS() && !us.length ? addBtn(q.trim(), '“' + q.trim() + '” ürününü listemize ekle') : '') +
      '</article>';
    if (st.dom === 'gida'){
      const af = afNotes('gida');
      if (af.length) h += '<details class="fold"><summary>Ama şu kategorilerde Ankara tüm markaları serbest sayıyor</summary><div class="fbody">' + af.map(n => '<p><b>' + esc(CAT[n.c].n) + ':</b> ' + esc(n.t) + '</p>').join('') + '</div></details>';
    }
    }
  }
  if (!(none && !us.length && !other.length)) h += addLine;  // boş sonuçta ekleme düğmesi zaten kırmızı kartın içinde
  out.innerHTML = h;
}
function catView(id, fromSearch){
  const c = CAT[id]; if (!c) return '';
  const ls = CATL[id] || [];
  const bs = new Map();
  ls.forEach(l => { if (l.b && l.k !== 'note') { if (!bs.has(l.b)) bs.set(l.b, []); bs.get(l.b).push(l); } });
  const sec = {both:[], part:[], ist:[], ank:[], read:[], warn:[]};
  bs.forEach((lst, b) => { const s = groupStatus(b, id); (sec[s === 'mixed' ? 'both' : s] || sec.ist).push(b); });
  for (const k in sec) sec[k].sort((a, b) => (BN[a] || a).localeCompare(BN[b] || b, 'tr'));
  const notes = ls.filter(l => l.k === 'note');
  const n = catCounts(id);
  let h = (fromSearch ? '' : '<button class="back" data-back="1">' + ICON.back + 'Tüm kategoriler</button>') +
    '<h2>' + esc(c.n) + '</h2>' + (() => { const ps = [[n.both, 'marka iki listede'], [n.part, 'marka iki listede ama ürünler farklı'], [n.ist, 'sadece İstanbul'], [n.ank, 'sadece Ankara']].filter(x => x[0]).map(x => x[0] + ' ' + x[1]); return ps.length ? '<p class="small">' + ps.join(' · ') + '</p>' : ''; })();
  if (notes.length) h += notes.map(nn => '<div class="note' + (nn.af ? ' af' : '') + '"><span class="src">' + SRC[nn.s] + '</span>' + esc(nn.t) + '</div>').join('');
  if (!fromSearch) h += usCatBlock(c);  // aramadan gelindiyse eşleşmeler zaten yukarıda
  const block = (key, title) => {
    if (!sec[key].length) return '';
    return '<div class="sec"><span>' + title + '</span><span>' + sec[key].length + '</span></div><div class="card">' +
      sec[key].map(b => {
        const lst = bs.get(b).slice().sort(lineOrder);
        const open = st.open.has(id + '|' + b);
        return '<button class="brow" data-ob="' + esc(id + '|' + b) + '" aria-expanded="' + open + '"><span class="lft"><span class="bn">' + esc(BN[b] || b) + '</span><span class="pv">' + esc(lst.map(l => l.t).join(' · ')) + '</span></span>' + chip(key === 'both' ? groupStatus(b, id) : key) + '</button>' +
          (open ? '<div class="bdet"><ul class="ls">' + lst.map(l => lineRow(l, [])).join('') + '</ul></div>' : '');
      }).join('') + '</div>';
  };
  h += block('both', 'İki listede de') + block('part', 'Marka iki listede, ürünler farklı') + block('ist', 'Sadece İstanbul') + block('ank', 'Sadece Ankara') + block('read', 'Etiketi okunarak alınacak') + block('warn', 'Uyarılar');
  return h;
}
