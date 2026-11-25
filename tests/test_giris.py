#!/usr/bin/env python3
"""Gizlilik ve giriş: şifresiz telefonda kişisel hiçbir şey görünmez; giriş, çıkış, geçersiz şifre, çevrimdışı kopya."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from ortak import U, A, H, API, check, bitir, tarayici, telefon, ara, axe_ihlal, ekran

async def main():
    async with async_playwright() as p:
        b = await tarayici(p)
        # 1) şifresiz telefon
        x = await telefon(b)
        istekler = []
        x.on('request', lambda r: istekler.append(r.url) if r.url.startswith(API) else None)
        await x.reload(); await x.wait_for_selector('.grid'); await x.wait_for_timeout(800)
        check('şifresiz: sunucuya hiç istek gitmiyor', not istekler, istekler)
        check('şifresiz: Bizim listemiz ve Tepkilerimiz yok', await x.locator('.sec', has_text='Bizim listemiz').count() == 0 and await x.locator('.sec', has_text='Tepkilerimiz').count() == 0)
        check('şifresiz: renk anahtarında 3 renk', await x.locator('.kc').count() == 3)
        check('şifresiz: altta “Bizim listemiz · giriş” bağlantısı', await x.locator('[data-giris]').count() == 1)
        check('şifresiz: Nasıl çalışır?’da kişisel kısım anlatılmıyor', 'Tepkiler' not in await x.locator('details.fold', has_text='Nasıl çalışır?').inner_text())
        await ara(x, 'eti')
        check('şifresiz arama: kişisel kart, ekleme bağlantısı, dokunulabilir satır yok', await x.locator('article.v-us').count() == 0 and await x.locator('[data-ekle]').count() == 0 and await x.locator('.li[data-ln]').count() == 0 and await x.locator('.tpk').count() == 0)
        await ara(x, 'xyzabc')
        check('şifresiz: listede yok kartında ekleme düğmesi yok', await x.locator('.v-no').count() == 1 and await x.locator('.addb').count() == 0)
        check('şifresiz: telefonda kişisel kopya yok', await x.evaluate("['gk-bizim','gk-tepki','gk-sifre'].map(k => localStorage.getItem(k))") == [None, None, None])
        await x.click('#clear'); await x.wait_for_timeout(200)
        # 2) giriş
        await x.locator('[data-giris]').click(); await x.wait_for_selector('dialog[aria-labelledby=grH][open]')
        check('giriş penceresi açılıyor, odak şifrede', await x.evaluate("document.activeElement.name") == 'sifre')
        v = await axe_ihlal(x, 'dialog[aria-labelledby=grH]'); check('giriş penceresi erişilebilir (axe)', not v, v)
        await x.click('dialog[open] .btn'); await x.wait_for_timeout(200)
        check('boş şifre uyarısı', 'Şifrenizi yazın' in await x.inner_text('dialog[open] .err'))
        await x.fill('dialog[open] [name=sifre]', 'yanlis-sifre-123'); await x.click('dialog[open] .btn'); await x.wait_for_timeout(1300)
        check('yanlış şifre: “Şifre tanınmadı”', 'Şifre tanınmadı' in await x.inner_text('dialog[open] .err'))
        await x.fill('dialog[open] [name=sifre]', H); await x.click('dialog[open] .btn'); await x.wait_for_timeout(1200)
        check('Türkçe harfli şifreyle açıldı: “Açıldı · heyybenbus”', await x.locator('dialog[open]').count() == 0 and (await x.inner_text('#toast')).startswith('Açıldı · heyybenbus'), await x.inner_text('#toast'))
        check('açılınca Bizim listemiz (Eti) ve Tepkilerimiz geldi', 'Kakaolu Kurabiye' in await x.locator('article.v-us').first.inner_text() and await x.locator('.sec', has_text='Tepkilerimiz').count() == 1)
        check('açılınca 4 renk, giriş bağlantısı kalktı', await x.locator('.kc').count() == 4 and await x.locator('[data-giris]').count() == 0)
        check('alt bilgi: heyybenbus olarak açık', 'heyybenbus olarak açık' in await x.locator('.us-f').inner_text())
        check('şifre ve kişisel kopya bu telefonda', await x.evaluate("[localStorage.getItem('gk-sifre'), localStorage.getItem('gk-ad'), !!localStorage.getItem('gk-bizim')]") == [H, 'heyybenbus', True])
        # 3) ekleme (giriş yapılmış): şifre sorulmaz
        await x.click('article.v-us .addb'); await x.wait_for_selector('dialog.sheet[open]')
        check('ekleme formunda şifre alanı yok', await x.locator('dialog[open] [name=sifre]').count() == 0)
        await x.fill('dialog[open] [name=marka]', 'Schär'); await x.fill('dialog[open] [name=urun]', 'Pan Carré')
        await x.check('dialog[open] input[name=dayanak][value=paket]'); await x.click('dialog[open] .btn'); await x.wait_for_timeout(900)
        check('eklendi · heyybenbus', (await x.inner_text('#toast')).startswith('Listemize eklendi · heyybenbus'), await x.inner_text('#toast'))
        await ekran(x, 'giris_acik')
        # 4) çevrimdışı: telefondaki son kopya
        await x.route(API + '/**', lambda r: r.abort())
        await x.reload(); await x.wait_for_selector('.grid'); await x.wait_for_timeout(900)
        t = await x.locator('article.v-us').first.inner_text()
        check('sunucuya ulaşılamazsa telefondaki kopya + not', 'Pan Carré' in t and 'ulaşılamıyor' in t, t[:160])
        await x.unroute(API + '/**')
        # 5) çıkış
        await x.reload(); await x.wait_for_selector('.grid'); await x.wait_for_timeout(800)
        await x.locator('[data-unut]').click(); await x.wait_for_timeout(300)
        check('çıkış: bildirim, kişisel kısım gizlendi', 'Çıkış yapıldı' in await x.inner_text('#toast') and await x.locator('.sec', has_text='Bizim listemiz').count() == 0 and await x.locator('[data-giris]').count() == 1)
        check('çıkış: şifre ve kişisel kopya silindi', await x.evaluate("['gk-sifre','gk-ad','gk-bizim','gk-tepki'].map(k => localStorage.getItem(k))") == [None, None, None, None])
        # 6) kayıtlı şifre artık geçerli değil
        y = await telefon(b, 'eski-sifre-artik-yok', 'mayildiz')
        await y.wait_for_timeout(1500)
        check('geçersiz kayıtlı şifre: kilitlenir, uyarı, kopya silinir', await y.locator('.sec', has_text='Bizim listemiz').count() == 0 and 'Şifre tanınmadı' in await y.inner_text('#toast') and await y.evaluate("localStorage.getItem('gk-sifre')") is None)
        for n, pg in (('şifresiz/giriş', x), ('geçersiz', y)):
            check(f'sayfa hatası yok ({n})', not pg.errs, pg.errs)
        await b.close()
    bitir()
asyncio.run(main())
