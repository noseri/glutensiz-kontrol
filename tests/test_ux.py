#!/usr/bin/env python3
"""Arayüz: açılış, sekmeler, son aramalar, renk anahtarı, dokunma alanları, erişilebilirlik (şifresiz telefon)."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from ortak import U, A, check, bitir, tarayici, ara, axe_ihlal

async def secili(pg): return await pg.locator('.tab[aria-pressed=true]').inner_text()
async def main():
    async with async_playwright() as p:
        b = await tarayici(p)
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, service_workers='block', is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        # A) liste gelmeden önce: sekmeler ve üst bölüm hazır, sonra kayma yok
        async def yavas(route):
            await asyncio.sleep(1.5); await route.continue_()
        await pg.route('**/data.json*', yavas)
        await pg.goto(U, wait_until='domcontentloaded'); await pg.wait_for_timeout(300)
        check('liste gelmeden sekmeler çizili', await pg.locator('.tab').count() == 4)
        check('liste gelmeden renk anahtarı çizili (şifresiz: 3 renk)', await pg.locator('details.key .kc:visible').count() == 3)
        y0 = await pg.evaluate("document.querySelector('#q').getBoundingClientRect().top")
        await pg.wait_for_selector('.grid', timeout=10000)
        y1 = await pg.evaluate("document.querySelector('#q').getBoundingClientRect().top")
        check('liste gelince arama kutusu yerinden oynamıyor', abs(y1 - y0) < 1, (y0, y1))
        await pg.unroute('**/data.json*')
        await pg.evaluate("localStorage.removeItem('gk-son'); localStorage.setItem('gk-dom','gida')"); await pg.reload(); await pg.wait_for_selector('.grid'); await pg.wait_for_timeout(400)
        # D) renk anahtarı
        check('anahtar kapalı başlar, 3 etiket (Bizim listemiz şifresiz görünmez)', not await pg.locator('details.key').get_attribute('open') and await pg.locator('.kc').count() == 3)
        h_key = await pg.evaluate("document.querySelector('details.key').getBoundingClientRect().height")
        check('anahtar ilk ekranda az yer kaplıyor (<140 px)', h_key < 140, h_key)
        await pg.click('details.key summary'); await pg.wait_for_timeout(150)
        check('dokununca açıklama açılıyor', await pg.locator('details.key[open] .lg').count() == 3)
        await pg.click('.tab[data-dom=kozmetik]'); await pg.wait_for_timeout(200); await pg.click('.tab[data-dom=gida]'); await pg.wait_for_timeout(200)
        check('yeniden çizimde açık kalıyor', await pg.locator('details.key[open]').count() == 1)
        # B) sekme geçişi geçici
        await ara(pg, 'parol')
        check('parol → İlaç gösteriliyor + not', await secili(pg) == 'İlaç' and await pg.locator('.moved').count() == 1)
        await pg.click('#clear'); await pg.wait_for_timeout(250)
        check('arama silinince seçilen sekmeye (Gıda) dönülüyor', await secili(pg) == 'Gıda')
        await ara(pg, 'ekmek')
        check('ekmek: gereksiz "sekmesinde yok" notu yok', await pg.locator('.moved').count() == 0 and await secili(pg) == 'Gıda')
        check('otomatik geçiş kalıcı tercihi değiştirmiyor', await pg.evaluate("localStorage.getItem('gk-dom')") == 'gida')
        await ara(pg, 'parol'); await pg.click('.tab[data-dom=gida]'); await pg.wait_for_timeout(250)
        txt = await pg.locator('main').inner_text()
        check('elle Gıda seçilince: kırmızı değil, nötr kart + İlaç düğmesi', 'Gıda listesinde yok' in txt and 'hiçbir listede yok' not in txt and await pg.locator('.sugg [data-dom=ilac]').count() == 1, txt[:200])
        await pg.click('.sugg [data-dom=ilac]'); await pg.wait_for_timeout(250)
        check('İlaç düğmesi sonuçları açıyor', await secili(pg) == 'İlaç' and 'PAROL' in await pg.locator('main').inner_text())
        await pg.click('.tab[data-dom=gida]'); await pg.wait_for_timeout(150)
        # C) son aramalar
        await ara(pg, 'pinar'); await pg.press('#q', 'Enter'); await pg.wait_for_timeout(150)
        await ara(pg, 'nivea'); await pg.click('#clear'); await pg.wait_for_timeout(250)
        chips = await pg.locator('.recent .sg').all_inner_texts()
        check('son aramalar: en yeni başta, yinelenmeden', chips[:3] == ['nivea', 'pinar', 'parol'], chips)
        await pg.click('.recent .sg >> text=pinar'); await pg.wait_for_timeout(300)
        check('çipe dokununca arama yapılıyor', await pg.input_value('#q') == 'pinar' and await pg.locator('article.card').count() > 0)
        await pg.click('#clear'); await pg.wait_for_timeout(200)
        await pg.click('[data-sonsil]'); await pg.wait_for_timeout(200)
        check('temizle son aramaları siliyor', await pg.locator('.recent').count() == 0)
        # E) sıfır sayılar
        await pg.goto(U + '#k-ekmek'); await pg.wait_for_timeout(400)
        sub = await pg.locator('main h2 + p.small').inner_text()
        check('kategori alt başlığında sıfır yok', ' 0 ' not in (' ' + sub + ' ') and not sub.startswith('0 '), sub)
        await pg.goto(U); await pg.wait_for_selector('.grid'); await pg.wait_for_timeout(300)
        # F) yinelenen not
        await ara(pg, 'pinar yogurt')
        hd = await pg.locator('.li .hd').all_inner_texts()
        notes = await pg.locator('.note').all_inner_texts()
        check('Ankara satır başlığı kısaldı', any(h.strip() == 'Ankara · YOĞURT' for h in hd), hd)
        check('not kutusu bir kez duruyor', sum('Üzeri okunmak' in n for n in notes) == 1, notes)
        await pg.click('#clear'); await pg.wait_for_timeout(200)
        # H) dokunma alanı: sekmenin 3 px üstü/altı da sekmeyi seçer
        hit = await pg.evaluate("""() => { const t = document.querySelector('.tab[data-dom=kozmetik]'), r = t.getBoundingClientRect();
          const x = r.left + r.width / 2; return [document.elementFromPoint(x, r.top - 3), document.elementFromPoint(x, r.bottom + 2)].map(e => e && e.closest('.tab') === t); }""")
        check('sekme dokunma alanı ≥ 44 px', all(hit), hit)
        # J) sekmeler sığıyor + ipucu kısa
        for w in (390, 375):
            await pg.set_viewport_size({'width': w, 'height': 844}); await pg.wait_for_timeout(150)
            fit = await pg.evaluate("(() => { const t = document.querySelector('#tabs'); return [t.scrollWidth, t.clientWidth]; })()")
            check(f'{w}px: dört sekme sığıyor', fit[0] <= fit[1], fit)
        # yazı tipi yüklendikten sonra ölç; kutunun iç genişliği kenarlık ve iç boşluk düşülerek hesaplanır
        # (input.clientWidth tarayıcı sürümüne göre iç boşluğu içerebiliyor ya da içermiyor)
        fits = await pg.evaluate("""async () => { const i = document.querySelector('#q'), cs = getComputedStyle(i);
          await document.fonts.load(cs.fontWeight + ' ' + cs.fontSize + ' Manrope', i.placeholder); await document.fonts.ready;
          const c = document.createElement('canvas').getContext('2d'); c.font = cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
          const ic = i.getBoundingClientRect().width - ['borderLeftWidth', 'borderRightWidth', 'paddingLeft', 'paddingRight'].reduce((t, k) => t + parseFloat(cs[k]), 0);
          return [Math.round(c.measureText(i.placeholder).width), Math.round(ic)]; }""")
        check('arama ipucu kesilmiyor', fits[0] < fits[1] - 20, fits)
        await pg.set_viewport_size({'width': 390, 'height': 844})
        # I) erişilebilirlik
        for label, setup in [('ana sayfa', None), ('arama', 'pinar yogurt')]:
            if setup: await ara(pg, setup)
            v = await axe_ihlal(pg)
            check('axe ' + label + ': ihlal yok', not v, v)
        await pg.click('#clear'); await pg.wait_for_timeout(200)
        # G) şifre kayıtlı telefonda: Bizim listemiz boş sekmede sade kart
        await pg.evaluate("localStorage.setItem('gk-sifre', %r); localStorage.setItem('gk-ad', 'mayildiz')" % A); await pg.reload(); await pg.wait_for_selector('.grid'); await pg.wait_for_timeout(700)
        await pg.click('.tab[data-dom=ilac]'); await pg.wait_for_timeout(250)
        card = pg.locator('article.v-us').first
        check('boş sekmede sade kart (önce ekle düğmesi, uzun metin yok)', await card.locator('.us-e').count() == 0 and await card.locator(':scope > .addb').count() == 1, await card.inner_text())
        check('boşken başlıkta 0 yazmıyor', (await pg.locator('.sec', has_text='Bizim listemiz').inner_text()).strip() == 'Bizim listemiz')
        check('şifre kayıtlıyken renk anahtarında 4 renk', await pg.locator('.kc').count() == 4)
        check('sayfa hatası yok', not errs, errs)
        await b.close()
    bitir()
asyncio.run(main())
