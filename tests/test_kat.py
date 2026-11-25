#!/usr/bin/env python3
"""Ekleme formu: kategori yazdıkça süzülen açılır liste (açık ve koyu tema)."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from ortak import U, A, H, check, bitir, tarayici
async def opts(pg): return await pg.locator('#katList li').all_inner_texts()
async def main():
    async with async_playwright() as p:
        b = await tarayici(p)
        for scheme in ['light', 'dark']:
            ctx = await b.new_context(viewport={'width': 390, 'height': 844}, color_scheme=scheme, service_workers='block', is_mobile=True, has_touch=True)
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(U); await pg.evaluate("localStorage.clear(); localStorage.setItem('gk-dom','kozmetik'); localStorage.setItem('gk-sifre','deneme-adem-1234'); localStorage.setItem('gk-ad','mayildiz')"); await pg.reload()
            await pg.wait_for_selector('article.v-us'); await pg.wait_for_timeout(600)
            await pg.click('article.v-us .addb'); await pg.wait_for_selector('dialog.sheet[open]')
            if scheme == 'light':
                check('liste başta kapalı', await pg.locator('#katList').is_hidden())
                await pg.tap('#fKat'); await pg.wait_for_timeout(450)
                o = await opts(pg)
                check('odakta açılıyor: 5 dernek kategorisi + bizim', len(o) == 6 and any('Dudak bakım' in x and 'bizim' in x for x in o) and not any('Etiketi okunacak' in x for x in o), o)
                await pg.fill('#fKat', 'sam'); await pg.wait_for_timeout(150)
                o = await opts(pg)
                check('"sam" → Şampuan kategorisi', o == ['Şampuan, sabun ve kişisel bakım'], o)
                check('eşleşen kelime kalın', await pg.locator('#katList mark').first.inner_text() == 'Şampuan,')
                await pg.fill('#fKat', 'BAKIM'); await pg.wait_for_timeout(150)
                o = await opts(pg)
                check('"BAKIM" (büyük harf, ı/i) → iki sonuç', len(o) == 2, o)
                await pg.fill('#fKat', 'xyz'); await pg.wait_for_timeout(150)
                check('eşleşme yoksa açıklama', 'yazdığınız gibi kaydedilir' in (await opts(pg))[0])
                await pg.fill('#fKat', 'kre'); await pg.wait_for_timeout(150)
                await pg.tap('#katList [data-kat]'); await pg.wait_for_timeout(250)
                check('dokununca seçiliyor ve kapanıyor', await pg.input_value('#fKat') == 'Krem, losyon ve güneş koruyucu' and await pg.locator('#katList').is_hidden())
                check('temizle düğmesi görünüyor', await pg.locator('.cb-x').is_visible())
                await pg.tap('.cb-x'); await pg.wait_for_timeout(250)
                check('temizle boşaltıyor', await pg.input_value('#fKat') == '')
                # klavye
                await pg.fill('#fKat', 'de'); await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
                check('ok tuşu + Enter seçiyor', await pg.input_value('#fKat') == 'Deodorant', await pg.input_value('#fKat'))
                # alan değişince başka listenin kategorisi temizlenir
                await pg.click('dialog .seg label:has(input[value=gida])'); await pg.wait_for_timeout(150)
                check('alan değişince seçili kategori temizlendi', await pg.input_value('#fKat') == '')
                await pg.tap('#fKat'); await pg.wait_for_timeout(300)
                n = len(await opts(pg))
                check('Gıda: 120 kategori', n == 120, n)
                await pg.fill('#fKat', 'makar'); await pg.wait_for_timeout(150)
                o = await opts(pg); check('"makar" → Makarna', any(x.startswith('Makarna') for x in o), o)
                # elle yazılan kategori alan değişince kalır
                await pg.fill('#fKat', 'Kendi kategorim'); await pg.click('dialog .seg label:has(input[value=kozmetik])'); await pg.wait_for_timeout(150)
                check('elle yazılan kategori korunuyor', await pg.input_value('#fKat') == 'Kendi kategorim')
                # kaydet: seçili kategoriyle
                await pg.fill('#fKat', 'sam'); await pg.wait_for_timeout(150); await pg.tap('#katList [data-kat]')
                await pg.fill('dialog input[name=marka]', 'Elidor'); await pg.fill('dialog input[name=urun]', 'Saç Kremi 350 ml')
                await pg.check('dialog input[name=dayanak][value=paket]')
                await pg.click('dialog .btn'); await pg.wait_for_selector('dialog.sheet:not([open])', state='attached', timeout=6000); await pg.wait_for_timeout(300)
                t = await pg.locator('article.v-us').first.inner_text()
                check('kaydedilen üründe kategori yazıyor', 'Şampuan, sabun ve kişisel bakım' in t, t[:200])
                await pg.goto(U + '#k-sampuan'); await pg.wait_for_timeout(500)
                check('kategori sayfasında da görünüyor', 'Saç Kremi 350 ml' in await pg.locator('main').inner_text())
            else:
                await pg.tap('#fKat'); await pg.wait_for_timeout(450); await pg.fill('#fKat', 'ba'); await pg.wait_for_timeout(200)
            check(scheme + ': sayfa hatası yok', not errs, errs)
            await ctx.close()
        await b.close()
    bitir()
asyncio.run(main())
