#!/usr/bin/env python3
"""Hızlı açılış ve çevrimdışı çalışma (service worker): ayrı bir site kopyasında (8766), sabit test verisiyle."""
import asyncio, json, os, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from ortak import KOK, check, bitir, tarayici
KOPYA = os.environ['GK_SW_KOPYA']
shutil.copy(os.environ['GK_SW_VERI'], os.path.join(KOPYA, 'data.json'))  # her çalıştırmada temiz başlangıç
U = 'http://localhost:8766/index.html'
async def main():
    async with async_playwright() as p:
        b = await tarayici(p)
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, service_workers='allow', is_mobile=True, has_touch=True)
        await ctx.add_init_script("""window.__upd = []; document.addEventListener('DOMContentLoaded', () => { const el = document.querySelector('#upd');
          new MutationObserver(() => window.__upd.push(el.textContent)).observe(el, {childList: true, characterData: true, subtree: true}); });""")
        pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(U); await pg.wait_for_selector('.grid')
        await pg.evaluate("navigator.serviceWorker.ready.then(() => true)")
        await pg.reload(); await pg.wait_for_selector('.grid'); await pg.wait_for_timeout(800)
        check('service worker sayfayı kontrol ediyor', await pg.evaluate("!!navigator.serviceWorker.controller"))
        keys = await pg.evaluate("caches.keys()")
        check('önbellek bu sürüme özgü (gk-test1)', keys == ['gk-test1'], keys)
        ekler = await pg.evaluate("caches.open('gk-test1').then(c => c.keys()).then(ks => ks.map(r => r.url.split('/').pop()).filter(u => u.includes('?v=')))")
        check('stil ve 9 betik sürümleriyle önbellekte', len(ekler) == 10 and all(u.endswith('?v=test1') for u in ekler), ekler)
        upd0 = await pg.inner_text('#upd')
        check('çevrimiçi: çevrimdışı yazmıyor', 'çevrimdışı' not in upd0, upd0)
        # sunucudaki liste değişiyor
        d = json.load(open(os.path.join(KOPYA, 'data.json'), encoding='utf-8'))
        from datetime import datetime, timedelta, timezone
        bugun = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
        AY = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
        YENI = f'{bugun.day} {AY[bugun.month - 1]} {bugun.year}'
        d['generated'] = bugun.isoformat(); d['checked'] = bugun.isoformat()
        json.dump(d, open(os.path.join(KOPYA, 'data.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        await pg.reload(); await pg.wait_for_selector('.grid')
        await pg.wait_for_function("t => document.querySelector('#upd').textContent.includes(t)", arg=YENI, timeout=6000)
        seq = [x for x in await pg.evaluate('window.__upd') if x.strip()]
        check('önce telefondaki liste (eski tarih), sonra yenisi gösterildi', seq and YENI not in seq[0] and YENI in seq[-1], seq)
        check('arka planda yeni liste alınıp sayfa kendiliğinden yenilendi', True)
        tt = await pg.inner_text('#toast')
        check('"Listeler güncellendi" bildirimi', tt.startswith('Listeler güncellendi · ' + YENI), tt)
        # çevrimdışı
        await ctx.set_offline(True)
        t0 = time.time(); await pg.reload(); await pg.wait_for_selector('.grid', timeout=8000); dt = time.time() - t0
        check(f'internetsiz açılış hızlı ({dt:.2f} sn)', dt < 2.5, dt)
        await pg.wait_for_function("document.querySelector('#upd').textContent.includes('çevrimdışı')", timeout=6000)
        check('internetsizken "çevrimdışı" yazıyor', True)
        await pg.fill('#q', 'pinar'); await pg.wait_for_timeout(300)
        check('internetsiz arama çalışıyor', await pg.locator('article.card').count() > 0)
        await ctx.set_offline(False)
        await pg.fill('#q', ''); await pg.reload(); await pg.wait_for_selector('.grid'); await pg.wait_for_timeout(1500)
        u = await pg.inner_text('#upd')
        check('internet gelince "çevrimdışı" kalkıyor', 'çevrimdışı' not in u, u)
        # yeni sürüm yayınlanıyor: telefon yeni dosyalara karışıksız geçmeli
        shutil.rmtree(KOPYA); shutil.copytree(os.environ['GK_SW_HAM'], KOPYA)
        subprocess.run(['bash', os.path.join(KOK, 'scripts', 'surum.sh'), KOPYA, 'test2'], check=True, capture_output=True)
        await pg.reload(); await pg.wait_for_selector('.grid')
        await pg.wait_for_function("caches.keys().then(k => k.length === 1 && k[0] === 'gk-test2')", timeout=15000, polling=300)
        check('yeni sürüm kuruldu, eski önbellek silindi (gk-test2)', True)
        await pg.reload(); await pg.wait_for_selector('.grid'); await pg.wait_for_timeout(500)
        src = await pg.evaluate("[...document.scripts].map(s => s.getAttribute('src')).filter(Boolean)")
        check('sayfa yeni sürümün betikleriyle açıldı', len(src) == 9 and all(x.endswith('?v=test2') for x in src), src)
        await ctx.set_offline(True)
        await pg.reload(); await pg.wait_for_selector('.grid', timeout=8000)
        src = await pg.evaluate("[...document.scripts].map(s => s.getAttribute('src')).filter(Boolean)")
        await pg.fill('#q', 'pinar'); await pg.wait_for_timeout(300)
        check('yeni sürüm internetsiz de açılıyor ve arıyor', all(x.endswith('?v=test2') for x in src) and await pg.locator('article.card').count() > 0, src)
        await ctx.set_offline(False)
        check('sayfa hatası yok', not errs, errs)
        await b.close()
    bitir()
asyncio.run(main())
