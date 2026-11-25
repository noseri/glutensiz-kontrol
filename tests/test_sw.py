#!/usr/bin/env python3
"""Hızlı açılış ve çevrimdışı çalışma (service worker): ayrı bir site kopyasında (8766), sabit test verisiyle."""
import asyncio, json, os, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from ortak import check, bitir, tarayici
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
        check('önbellek gk-v5 (eski önbellekler silindi)', keys == ['gk-v5'], keys)
        upd0 = await pg.inner_text('#upd')
        check('çevrimiçi: çevrimdışı yazmıyor', 'çevrimdışı' not in upd0, upd0)
        # sunucudaki liste değişiyor
        d = json.load(open(os.path.join(KOPYA, 'data.json'), encoding='utf-8'))
        d['generated'] = '2026-12-01'; d['checked'] = '2026-12-01'
        json.dump(d, open(os.path.join(KOPYA, 'data.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        await pg.reload(); await pg.wait_for_selector('.grid')
        await pg.wait_for_function("document.querySelector('#upd').textContent.includes('1 Aralık 2026')", timeout=6000)
        seq = [x for x in await pg.evaluate('window.__upd') if x.strip()]
        check('önce telefondaki liste (eski tarih), sonra yenisi gösterildi', seq and 'Aralık' not in seq[0] and '1 Aralık 2026' in seq[-1], seq)
        check('arka planda yeni liste alınıp sayfa kendiliğinden yenilendi', True)
        tt = await pg.inner_text('#toast')
        check('"Listeler güncellendi" bildirimi', tt.startswith('Listeler güncellendi · 1 Aralık 2026'), tt)
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
        check('sayfa hatası yok', not errs, errs)
        await b.close()
    bitir()
asyncio.run(main())
