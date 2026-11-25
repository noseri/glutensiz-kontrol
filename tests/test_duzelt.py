#!/usr/bin/env python3
"""Bizim listemiz: Düzelt (geçmiş, çakışma, zincir)."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from ortak import U, A, H, check, bitir, tarayici
def row(pg, text): return pg.locator('article.v-us > .us-it', has_text=text).first
async def save(pg):
    await pg.click('dialog .btn'); await pg.wait_for_timeout(700)
async def main():
    async with async_playwright() as p:
        b = await tarayici(p)
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, service_workers='block', is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(U); await pg.evaluate("localStorage.clear(); localStorage.setItem('gk-dom','kozmetik'); localStorage.setItem('gk-sifre','deneme-adem-1234'); localStorage.setItem('gk-ad','mayildiz')"); await pg.reload()
        await pg.wait_for_selector('article.v-us > .us-it'); await pg.wait_for_timeout(500)
        r = row(pg, 'Elidr')
        check('satırda Düzelt ve Listeden çıkar', await r.locator('[data-duzelt]').count() == 1 and await r.locator('[data-cikar]').count() == 1)
        await r.locator('[data-duzelt]').click(); await pg.wait_for_selector('dialog.sheet[open]')
        f = lambda n: pg.input_value(f'dialog [name={n}]')
        check('form: başlık "Düzelt", açıklama, düğme', await pg.inner_text('#addH') == 'Düzelt' and 'düzeltildi' in await pg.inner_text('dialog .lead') and await pg.inner_text('dialog .btn') == 'Düzeltmeyi kaydet')
        check('form kayıt bilgileriyle dolu', [await f('marka'), await f('urun'), await f('kategori')] == ['Elidr', 'Sampuan', 'Şampuan, sabun ve kişisel bakım'] and await pg.is_checked('dialog input[name=dayanak][value=paket]') and await pg.is_checked('dialog input[name=alan][value=kozmetik]'))
        check('formda şifre alanı yok (giriş yapılmış telefon)', await pg.locator('dialog [name=sifre]').count() == 0)
        await save(pg)
        check('değişiklik yoksa uyarı', 'Değişiklik yapmadınız' in await pg.inner_text('dialog .err'), await pg.inner_text('dialog .err'))
        await pg.fill('dialog [name=marka]', 'Elidor'); await pg.fill('dialog [name=urun]', 'Şampuan 400 ml')
        await save(pg)
        check('kaydedince form kapanıyor', await pg.locator('dialog.sheet[open]').count() == 0)
        t = await pg.inner_text('#toast'); check('"Düzeltildi · mayildiz" bildirimi', t.startswith('Düzeltildi · mayildiz · '), t)
        r = row(pg, 'Şampuan 400 ml'); s = await r.locator('.us-s').inner_text()
        check('yeni satır: ilk ekleyen + düzelten', 'heyybenbus ekledi' in s and 'mayildiz düzeltti' in s, s)
        check('eski ad listede yok', await row(pg, 'Elidr').count() == 0)
        summ = await pg.inner_text('details.ush summary'); check('geçmiş özeti: 1 düzeltme', summ == 'Geçmiş: 1 düzeltme', summ)
        await pg.click('details.ush summary'); await pg.wait_for_timeout(150)
        g = pg.locator('details.ush .us-it', has_text='Elidr').first; gt = await g.inner_text()
        check('geçmişte eski kayıt "düzeltildi" ve kim, ne zaman', 'düzeltildi' in gt and 'heyybenbus ekledi' in gt and 'mayildiz düzeltti' in gt, gt)
        deco = await g.locator('.tag-d').evaluate("e => getComputedStyle(e.closest('.us-t')).textDecorationLine")
        check('eski kaydın adı üstü çizili', 'line-through' in deco, deco)
        # çakışma
        await row(pg, 'Şampuan 400 ml').locator('[data-duzelt]').click(); await pg.wait_for_selector('dialog.sheet[open]')
        await pg.fill('dialog [name=marka]', 'NIVEA'); await pg.fill('dialog [name=urun]', 'krem'); await save(pg)
        e = await pg.inner_text('dialog .err'); check('başka ürünün adına düzeltme engelleniyor', e.startswith('Bu adla başka bir ürün zaten listede: mayildiz ekledi'), e)
        # zincir: yalnız not
        await pg.fill('dialog [name=marka]', 'Elidor'); await pg.fill('dialog [name=urun]', 'Şampuan 400 ml'); await pg.fill('dialog [name=notu]', 'Parti 2611'); await save(pg)
        r = row(pg, 'Şampuan 400 ml'); s = await r.locator('.us-s').inner_text()
        check('ikinci düzeltmede de ilk ekleyen korunuyor', 'heyybenbus ekledi' in s and 'mayildiz düzeltti' in s and 'Parti 2611' in await r.inner_text(), s)
        summ = await pg.inner_text('details.ush summary'); check('geçmiş özeti: 2 düzeltme', summ == 'Geçmiş: 2 düzeltme', summ)
        # çıkarma onayı Düzelt'i de gizler
        r = row(pg, 'Dudak Koruyucu'); await r.locator('[data-cikar]').click(); await pg.wait_for_timeout(100)
        check('çıkarma onayında Düzelt gizleniyor', await r.locator('[data-duzelt]').count() == 0 and await r.locator('.cf').count() == 1)
        await r.locator('[data-cikarevet]').click(); await pg.wait_for_timeout(700)
        summ = await pg.inner_text('details.ush summary'); check('geçmiş özeti: 2 düzeltme, 1 çıkarma', summ == 'Geçmiş: 2 düzeltme, 1 çıkarma', summ)
        # normal ekleme formu eski haline dönüyor
        await pg.click('article.v-us .addb'); await pg.wait_for_selector('dialog.sheet[open]')
        check('ekleme formu sıfırlandı', await pg.inner_text('#addH') == 'Listemize ekle' and await pg.inner_text('dialog .btn') == 'Listemize ekle' and await f('marka') == '' and await f('notu') == '')
        await pg.keyboard.press('Escape')
        # sayfa yenilenince sunucudan gelen veriyle aynı görünüm
        await pg.reload(); await pg.wait_for_selector('article.v-us > .us-it'); await pg.wait_for_timeout(600)
        s = await row(pg, 'Şampuan 400 ml').locator('.us-s').inner_text()
        check('yenileyince de ilk ekleyen + düzelten', 'heyybenbus ekledi' in s and 'mayildiz düzeltti' in s, s)
        await pg.click('details.ush summary'); await pg.wait_for_timeout(200); await pg.locator('details.ush').scroll_into_view_if_needed();        await row(pg, 'Şampuan 400 ml').locator('[data-duzelt]').click(); await pg.wait_for_selector('dialog.sheet[open]'); await pg.wait_for_timeout(300);        check('sayfa hatası yok', not errs, errs)
        await b.close()
    bitir()
asyncio.run(main())
