"""Testlerin ortak yardımcıları. Adresler ve test şifreleri tests/calistir.sh ile aynıdır."""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.environ.get('GK_API', 'http://127.0.0.1:8787')
SITE = os.environ.get('GK_SITE', 'http://localhost:8765')
U = SITE + '/index.html?api=' + API
# yalnızca yerel test sunucusunun şifreleri (gerçek şifreler GitHub'daki gizli değerlerdedir)
A = os.environ.get('GK_SIFRE_1', 'deneme-adem-1234')            # mayildiz
H = os.environ.get('GK_SIFRE_2', 'Mor kedi sabah çayı ğüşİı')   # heyybenbus
CHROME = os.environ.get('GK_CHROME') or None
AXE_YOL = os.environ.get('GK_AXE') or os.path.join(KOK, 'tests', 'node_modules', 'axe-core', 'axe.min.js')
DLG = 'dialog[aria-labelledby=tpH]'

ok = bad = 0
def check(n, c, i=''):
    global ok, bad
    if c: ok += 1; print('  ✓', n)
    else: bad += 1; print('  ✗', n, i)
def bitir():
    print(f'\n{ok} geçti, {bad} kaldı')
    sys.exit(1 if bad else 0)

def api(method, path, body=None, key=None, origin=None, raw=None, ctype='application/json'):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(API + path, data=data, method=method)
    if data is not None: r.add_header('Content-Type', ctype)
    if key: r.add_header('Authorization', 'Bearer ' + urllib.parse.quote(key, safe=''))
    if origin: r.add_header('Origin', origin)
    t0 = time.time()
    try:
        with urllib.request.urlopen(r) as x:
            b = x.read(); return x.status, (json.loads(b) if b else None), dict(x.headers), time.time() - t0
    except urllib.error.HTTPError as e:
        b = e.read(); return e.code, (json.loads(b) if b else None), dict(e.headers), time.time() - t0

def tohum():
    """Tarayıcı testlerinin beklediği başlangıç kayıtları (boş veritabanına)."""
    for body, key in [
        ({'alan': 'kozmetik', 'marka': 'Elidr', 'urun': 'Sampuan', 'kategori': 'Şampuan, sabun ve kişisel bakım', 'dayanak': 'paket'}, H),
        ({'alan': 'kozmetik', 'marka': 'Nivea', 'urun': 'Krem', 'dayanak': 'paket'}, A),
        ({'alan': 'kozmetik', 'marka': 'Bioderma', 'urun': 'Dudak Koruyucu', 'kategori': 'Dudak bakım', 'dayanak': 'uretici'}, H),
        ({'alan': 'gida', 'marka': 'Eti', 'urun': 'Glutensiz Kakaolu Kurabiye', 'dayanak': 'paket'}, H)]:
        s, j, _, _ = api('POST', '/ekle', body, key)
        assert s == 201, (s, j)

async def tarayici(p):
    return await p.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])

async def telefon(b, key=None, name=None, dom='gida', scheme='light', url=None):
    """Yeni bir telefon: temiz depolama; isteğe bağlı kayıtlı şifre."""
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, color_scheme=scheme, service_workers='block', is_mobile=True, has_touch=True)
    pg = await ctx.new_page(); pg.errs = []; pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    await pg.goto(url or U)
    js = "localStorage.clear(); localStorage.setItem('gk-dom', %s);" % json.dumps(dom)
    if key: js += "localStorage.setItem('gk-sifre', %s); localStorage.setItem('gk-ad', %s);" % (json.dumps(key), json.dumps(name))
    await pg.evaluate(js); await pg.reload(); await pg.wait_for_selector('.grid'); await pg.wait_for_timeout(700)
    return pg

async def ara(pg, text):
    await pg.fill('#q', text); await pg.wait_for_timeout(350)

async def ekran(pg, ad):
    """GK_EKRAN klasörü verilmişse ekran görüntüsü (gözle kontrol için)."""
    d = os.environ.get('GK_EKRAN')
    if d:
        os.makedirs(d, exist_ok=True); await pg.screenshot(path=os.path.join(d, ad + '.png'))

def axe():
    return open(AXE_YOL, encoding='utf-8').read()

async def axe_ihlal(pg, secici='document'):
    hedef = 'document' if secici == 'document' else "document.querySelector(%s)" % json.dumps(secici)
    return await pg.evaluate(axe() + "; axe.run(" + hedef + ", {runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']}).then(r => r.violations.map(v => v.id + ':' + v.nodes.length))")
