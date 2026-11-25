// Glutensiz Kontrol — Liste verisini (data.json) yükleme ve dizinleme.
// Sayfanın betikleri ortak bir kapsamda, şu sırayla çalışır: temel → cevrimdisi → kisisel → ekle → veri → liste → tepki → gorunum → baslat.
// ---- veri
function useData(d){
  D = d; CAT = {}; BNORM = {}; LBY = {}; GRP = {}; GBY = {}; CATL = {}; PB = new Set();
  D.cats.forEach(c => { CAT[c.id] = c; c.nn = norm(c.n); });
  BN = D.brands;
  for (const k in BN) BNORM[k] = norm(BN[k]);
  LN = D.lines;
  LN.forEach(l => { if (l.st === 'both') (l.p || []).forEach(pid => PB.add(pid)); });
  LN.forEach(l => {
    l.d = (CAT[l.c] || {}).d || 'gida';
    l.nn = norm(l.t);
    l.hn = norm(D.heads[l.h] || '');
    if (l.b) (LBY[l.b] = LBY[l.b] || []).push(l);
    (CATL[l.c] = CATL[l.c] || []).push(l);
  });
  D.groups.forEach(g => { GBY[g.b + '|' + g.c] = g; (GRP[g.b] = GRP[g.b] || []).push(g); });
}
async function load(){
  const repP = fetch('reports.json', {cache:'no-cache'}).then(r => r.ok ? r.json() : null).catch(() => null);
  try {
    const r = await fetch('data.json', {cache:'no-cache'});
    useData(await r.json());
  } catch (e) {
    out.innerHTML = '<div class="card"><div class="empty">Liste verisi yüklenemedi. Sayfayı yenileyin.</div></div>';
    return;
  }
  showUpd();
  const rj = await repP;
  if (rj && rj.brands) REP = rj.brands;
  drawTabs();
  route();
  loadUs(true);
  if (PENDING){ PENDING = false; reloadData(); }
}
// service worker yeni listeyi aldığında: sessizce yenile, içerik değiştiyse kısaca haber ver
async function reloadData(){
  try {
    const d = await fetch('data.json?onbellek=1', {cache:'no-cache'}).then(r => r.json());
    if (!d || !Array.isArray(d.lines)) return;
    const changed = d.generated !== D.generated;
    useData(d); showUpd(); drawTabs(); route();
    if (changed) toast('Listeler güncellendi · ' + fmtDate(d.generated));
  } catch (e) {}
}
