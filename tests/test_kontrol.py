#!/usr/bin/env python3
"""Bizim listemiz: 6 aylık yeniden kontrol hatırlatıcısı, "Kontrol ettim", düzeltmeden sonra da sayılması."""
import asyncio, json, os, sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from ortak import U, A, H, check, bitir, tarayici, telefon, axe_ihlal, ekran

ETI = 'article.v-us > .us-it'
async def saatli_telefon(b, gun):
    """Telefonun saati bugünden `gun` gün ileride (sunucunun saati değişmez)."""
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, service_workers='block', is_mobile=True, has_touch=True)
    pg = await ctx.new_page(); pg.errs = []; pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    await pg.clock.set_fixed_time(datetime.now(timezone.utc) + timedelta(days=gun))
    await pg.goto(U)
    await pg.evaluate("localStorage.clear(); localStorage.setItem('gk-dom', 'gida'); localStorage.setItem('gk-sifre', %s); localStorage.setItem('gk-ad', 'mayildiz')" % json.dumps(A))
    await pg.reload(); await pg.wait_for_selector('.grid'); await pg.wait_for_timeout(900)
    return pg

async def main():
    async with async_playwright() as p:
        b = await tarayici(p)
        a = await telefon(b, A, 'mayildiz')
        check('yeni eklenen üründe hatırlatıcı yok', await a.locator('.us-k').count() == 0 and await a.locator('.us-kz').count() == 0)
        # 1) telefon saati 200 gün ileride: eklenmesinin üzerinden 6 ay geçmiş
        z = await saatli_telefon(b, 200)
        row = z.locator(ETI, has_text='Kakaolu Kurabiye').first
        k = await row.locator('.us-k').inner_text() if await row.locator('.us-k').count() else ''
        check('6 ayı geçen üründe sarı uyarı ve "Kontrol ettim"', '6 aydır kontrol edilmedi: paketi yeniden okuyun.' in k and await row.locator('[data-kontrol]').count() == 1, k)
        check('Bizim listemiz başında özet: "1 ürünün yeniden kontrol zamanı geldi"', '1 ürünün yeniden kontrol zamanı geldi' in await z.locator('.us-kz').inner_text())
        v = await axe_ihlal(z); check('uyarılı ana sayfa erişilebilir (axe)', not v, v)
        await ekran(z, 'kontrol_uyari')
        # 2) kontrol ettim: uyarı kalkmaz çünkü telefonun saati ileride; kayıt sunucuya gider ve kim/ne zaman yazılır
        await row.locator('[data-kontrol]').click(); await z.wait_for_timeout(900)
        check('"Kontrol kaydedildi · mayildiz"', (await z.inner_text('#toast')).startswith('Kontrol kaydedildi · mayildiz'), await z.inner_text('#toast'))
        # 3) gerçek saatli telefonda: kontrol bilgisi, uyarı yok
        await a.reload(); await a.wait_for_selector('.grid'); await a.wait_for_timeout(900)
        row = a.locator(ETI, has_text='Kakaolu Kurabiye').first
        check('"mayildiz kontrol etti" yazıyor', 'mayildiz kontrol etti' in await row.locator('.us-s').inner_text())
        # 4) kontrolden 100 gün sonra (eklenmeden 100 gün sonra da): uyarı yok; 200 gün sonra yine var
        y = await saatli_telefon(b, 100)
        check('100 gün sonra uyarı yok', await y.locator('.us-k').count() == 0)
        # 5) düzeltmeden sonra da kontrol sayılır
        await row.locator('[data-duzelt]').click(); await a.wait_for_selector('dialog.sheet[open]')
        await a.fill('dialog [name=urun]', 'Glutensiz Kakaolu Kurabiye 150 g'); await a.click('dialog[open] .btn'); await a.wait_for_timeout(900)
        row = a.locator(ETI, has_text='150 g').first
        s = await row.locator('.us-s').inner_text()
        check('düzeltilen üründe ilk ekleyen, düzelten ve kontrol eden', 'heyybenbus ekledi' in s and 'mayildiz düzeltti' in s and 'mayildiz kontrol etti' in s, s)
        h = await telefon(b, H, 'heyybenbus')
        check('heyybenbus telefonunda da kontrol bilgisi', 'mayildiz kontrol etti' in await h.locator(ETI, has_text='150 g').first.locator('.us-s').inner_text())
        # 6) çıkarılmış ürün kontrol edilemez (başka telefonda çıkarıldıysa): uyarı ve liste yenilenir
        await h.locator(ETI, has_text='150 g').first.locator('[data-cikar]').click(); await h.wait_for_timeout(100)
        await h.locator('[data-cikarevet]').click(); await h.wait_for_timeout(800)
        z2 = await saatli_telefon(b, 400)
        n = await z2.locator('[data-kontrol]').count()
        check('çıkarılan ürün listede görünmez, kontrol düğmesi de yok', n == 0 and await z2.locator(ETI, has_text='Kakaolu').count() == 0)
        for ad, pg in (('gerçek saat', a), ('ileri saat', z), ('heyybenbus', h), ('100 gün', y), ('400 gün', z2)):
            check(f'sayfa hatası yok ({ad})', not pg.errs, pg.errs)
        await b.close()
    bitir()
asyncio.run(main())
