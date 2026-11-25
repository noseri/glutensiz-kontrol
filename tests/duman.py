#!/usr/bin/env python3
"""Duman testi: gerçek liste (site/data.json) açılıyor ve aranabiliyor mu? Haftalık güncellemeden sonra da çalışır.
Belirli bir ürüne bağlı değildir; yalnızca listenin sağlam olduğunu denetler."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from ortak import KOK, check, bitir, tarayici

U = os.environ.get('GK_SITE_GERCEK', 'http://localhost:8767') + '/index.html'
d = json.load(open(os.path.join(KOK, 'site', 'data.json'), encoding='utf-8'))
L = d['lines']
check('liste biçimi: sürüm ve satırlar', d.get('v', 0) >= 4 and len(L) > 1000, (d.get('v'), len(L)))
check('her satırda kalıcı numara, hepsi farklı', all(isinstance(l.get('u'), int) for l in L) and len({l['u'] for l in L}) == len(L))
check('son verilen numara satırlardakinden küçük değil', d.get('son_u', 0) >= max(l['u'] for l in L))
check('iki listeden de satır var', {l['s'] for l in L} == {'ist', 'ank'})
async def main():
    async with async_playwright() as p:
        b = await tarayici(p)
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, service_workers='block', is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(U); await pg.wait_for_selector('.grid', timeout=15000)
        check('ana sayfa açıldı, kategoriler çizildi', await pg.locator('.grid a, .grid button').count() > 10)
        for q in ('ekmek', 'glutensiz', 'cips'):   # kategori adı da olabilir, marka kartı da
            await pg.fill('#q', q); await pg.wait_for_timeout(400)
            check(f'"{q}" araması sonuç veriyor', await pg.locator('article.card, main h2').count() > 0 and await pg.locator('.v-no').count() == 0)
        await pg.fill('#q', 'qqqxyzbulunmaz'); await pg.wait_for_timeout(400)
        check('bulunmayan aramada kırmızı kart', await pg.locator('.v-no').count() == 1)
        check('sayfa hatası yok', not errs, errs)
        await b.close()
asyncio.run(main())
bitir()
