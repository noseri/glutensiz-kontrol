#!/usr/bin/env python3
"""Gezinti (markette tek elle kullanım): arama kutusundaki ←, iPhone'da kenardan kaydırma (geçmiş adımları),
başlık, sağ alttaki "Yeni arama", uygulamaya uzun aradan sonra dönünce ana sayfa, açık pencereler,
ana ekrandan yeniden açılış."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from ortak import U, A, SITE, DLG, check, bitir, tarayici, telefon, ara, axe_ihlal, ekran

GORUNUR = """s => { const e = document.querySelector(s); if (!e) return false;
  const r = e.getBoundingClientRect(); return getComputedStyle(e).display !== 'none' && r.width > 0 && r.bottom > 0 && r.top < innerHeight; }"""

async def gorunur(pg, s): return await pg.evaluate(GORUNUR, s)
async def durum(pg): return (await pg.evaluate('history.state')) or {}
async def adim(pg): return await pg.evaluate('history.length')
async def ana_mi(pg):  # ana sayfa: arama boş, kategori ızgarası var, ← gizli
    return await pg.evaluate("!location.hash && !document.querySelector('#q').value && !!document.querySelector('main .grid') && !document.body.classList.contains('icerde') && !document.querySelector('main .back')")
async def uzakta(pg, sn):  # uygulama sn saniye arka planda kalmış gibi
    await pg.evaluate("""sn => {
      const ayar = v => Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => v});
      ayar('hidden'); document.dispatchEvent(new Event('visibilitychange'));
      gizlendi = Date.now() - sn * 1000;
      ayar('visible'); document.dispatchEvent(new Event('visibilitychange'));
    }""", sn)
    await pg.wait_for_timeout(400)
async def geri(pg):   # iPhone'da sol kenardan kaydırma / Android geri tuşu
    await pg.evaluate('history.back()'); await pg.wait_for_timeout(400)
async def ileri(pg):
    await pg.evaluate('history.forward()'); await pg.wait_for_timeout(400)
async def bitti(pg):  # klavyede "Ara": kutu odaktan çıkar
    await pg.press('#q', 'Enter'); await pg.wait_for_timeout(300)
async def odak(pg): return await pg.evaluate('document.activeElement && document.activeElement.id')

async def main():
    async with async_playwright() as p:
        b = await tarayici(p)
        # ---- A) arama, ←, geri hareketi, başlık
        pg = await telefon(b)
        L0 = await adim(pg)
        check('ana sayfada ← ve "Yeni arama" gizli', not await gorunur(pg, '#geri') and not await gorunur(pg, '#yeni'))
        await ara(pg, 'pinar')
        check('aramada kutunun solunda ← (büyüteç yerine)', await gorunur(pg, '#geri') and
              await pg.evaluate("getComputedStyle(document.querySelector('.search > svg')).visibility") == 'hidden')
        check('arama geçmişe tek adım olarak yazıldı', await durum(pg) == {'gk': 'ara', 'q': 'pinar', 'd': 1} and await adim(pg) == L0 + 1, await durum(pg))
        check('yazarken "Yeni arama" gizli', not await gorunur(pg, '#yeni'))
        await bitti(pg)
        check('yazma bitince sağ altta "Yeni arama"', await gorunur(pg, '#yeni'))
        r = await pg.evaluate("(() => { const r = document.querySelector('#yeni').getBoundingClientRect(); return [innerWidth - r.right, innerHeight - r.bottom, r.height]; })()")
        check('"Yeni arama" başparmak bölgesinde, en az 44 px', r[0] <= 24 and r[1] <= 24 and r[2] >= 44, r)
        await geri(pg)
        check('geri hareketi: arama kapanır, ana sayfa', await ana_mi(pg))
        await ileri(pg)
        check('ileri: arama ve sonuçlar geri gelir', await pg.input_value('#q') == 'pinar' and await pg.locator('article.card').count() > 0)
        await pg.click('#geri'); await pg.wait_for_timeout(400)
        check('← ana sayfaya götürür, sayfanın başına', await ana_mi(pg) and await pg.evaluate('scrollY') == 0)
        check('← sonrası ana sayfa adımındayız (geride boş adım yok)', not (await durum(pg)).get('d'), await durum(pg))
        await ara(pg, 'eti')
        check('sonraki arama yine tek adım', await adim(pg) == L0 + 1, await adim(pg))
        await pg.click('#clear'); await pg.wait_for_timeout(400)
        check('× : ana sayfa, kutu odakta kalır', await ana_mi(pg) and await odak(pg) == 'q')
        await ara(pg, 'nivea')
        check('× sonrası arama da tek adım (boş adım birikmiyor)', await adim(pg) == L0 + 1 and (await durum(pg)).get('d') == 1, (await adim(pg), await durum(pg)))
        await bitti(pg)
        await pg.click('#ana'); await pg.wait_for_timeout(400)
        check('başlığa dokununca ana sayfa', await ana_mi(pg))

        # ---- B) kategori sayfası
        tile = pg.locator('main .grid .cat').nth(6)
        await tile.scroll_into_view_if_needed(); await pg.wait_for_timeout(200)
        y0 = await pg.evaluate('scrollY')
        await tile.click(); await pg.wait_for_timeout(400)
        check('kategori açılır, sayfanın başından', await pg.evaluate("location.hash.startsWith('#k-')") and await pg.evaluate('scrollY') == 0)
        check('ana sayfadan açılınca düğme "Tüm kategoriler"', (await pg.locator('main .back').inner_text()).strip() == 'Tüm kategoriler')
        await pg.evaluate('scrollTo(0, 2500)'); await pg.wait_for_timeout(250)
        check('aşağı inince de ← ve "Yeni arama" görünür', await pg.evaluate('scrollY') > 200 and await gorunur(pg, '#geri') and await gorunur(pg, '#yeni'))
        await geri(pg)
        y1 = await pg.evaluate('scrollY')
        check('geri: ana sayfada ızgaradaki yere dönülür', await ana_mi(pg) and y0 > 100 and abs(y1 - y0) <= 2, (y0, y1))
        await ara(pg, 'ekmek'); await bitti(pg)
        await pg.locator('main .grid .cat').first.click(); await pg.wait_for_timeout(400)
        check('aramadan açılan kategoride düğme "Aramaya dön"', (await pg.locator('main .back').inner_text()).strip() == 'Aramaya dön')
        await pg.click('main .back'); await pg.wait_for_timeout(400)
        check('"Aramaya dön" aramaya döndürür', await pg.input_value('#q') == 'ekmek' and not await pg.evaluate('location.hash') and await pg.locator('main .grid .cat').count() > 0)
        await ileri(pg)
        check('ileri: kategori yeniden', await pg.evaluate("location.hash.startsWith('#k-')"))
        await pg.click('#geri'); await pg.wait_for_timeout(400)
        check('kategoriden ← doğrudan ana sayfa (aramayı da kapatır)', await ana_mi(pg))
        await ara(pg, 'pinar')
        check('← iki adımı birden kapattı: yeni arama yine tek adım', await adim(pg) == L0 + 1, await adim(pg))

        # ---- C) "Yeni arama"
        await bitti(pg)
        await pg.evaluate("toast('Deneme bildirimi')"); await pg.wait_for_timeout(300)
        t = await pg.evaluate("(() => [document.querySelector('#toast').getBoundingClientRect().bottom, document.querySelector('#yeni').getBoundingClientRect().top])()")
        check('bildirim "Yeni arama"nın üstünde çıkar', t[0] <= t[1], t)
        await pg.click('#yeni'); await pg.wait_for_timeout(400)
        check('"Yeni arama": ana sayfa ve kutu odakta (klavye açılır)', await ana_mi(pg) and await odak(pg) == 'q')
        await pg.evaluate('document.activeElement.blur()'); await pg.wait_for_timeout(300)
        await pg.evaluate('scrollTo(0, 900)'); await pg.wait_for_timeout(300)
        check('ana sayfa aşağı kaydırılınca "Yeni arama" görünür', await gorunur(pg, '#yeni'))
        await pg.evaluate('scrollTo(0, 0)'); await pg.wait_for_timeout(300)
        check('ana sayfanın başında gizli', not await gorunur(pg, '#yeni'))
        await pg.evaluate('scrollTo(0, document.body.scrollHeight)'); await pg.wait_for_timeout(300)
        o = await pg.evaluate("(() => { const k = [...document.querySelectorAll('main > *')].pop().getBoundingClientRect(), y = document.querySelector('#yeni').getBoundingClientRect(); return [k.bottom, y.top]; })()")
        check('sayfanın sonu "Yeni arama"nın altında kalmaz', o[0] <= o[1], o)

        # ---- D) uygulamaya dönüş
        await pg.evaluate('scrollTo(0, 0)')
        await ara(pg, 'pinar'); await bitti(pg)
        await uzakta(pg, 30)
        check('kısa aradan sonra (30 sn) arama yerinde', await pg.input_value('#q') == 'pinar' and await pg.locator('article.card').count() > 0)
        await uzakta(pg, 180)
        check('uzun aradan sonra (3 dk) ana sayfa, en başta', await ana_mi(pg) and await pg.evaluate('scrollY') == 0)
        await pg.locator('main .grid .cat').nth(3).click(); await pg.wait_for_timeout(400)
        await uzakta(pg, 180)
        check('kategori sayfasındayken de uzun aradan sonra ana sayfa', await ana_mi(pg))
        await pg.evaluate('scrollTo(0, 1200)'); await pg.wait_for_timeout(250)
        await uzakta(pg, 180)
        check('ana sayfada aşağıdayken uzun aradan sonra en başa', await pg.evaluate('scrollY') == 0)
        await ara(pg, 'pinar'); await bitti(pg)
        v = await axe_ihlal(pg)
        check('erişilebilirlik: ← ve "Yeni arama" görünürken', not v, v)
        await ekran(pg, 'gezinti_arama')
        check('sayfa hatası yok', not pg.errs, pg.errs)
        await pg.context.close()
        pd = await telefon(b, scheme='dark')
        await ara(pd, 'pinar'); await bitti(pd)
        v = await axe_ihlal(pd, '#bar'); v2 = await axe_ihlal(pd, '#yeni')
        check('koyu temada ← ve "Yeni arama" okunur', not v and not v2, (v, v2))
        await ekran(pd, 'gezinti_koyu')
        await pd.context.close()

        # ---- E) ana ekrandan açılan uygulama yeniden başlatılırsa (iPhone arka planda kapatabilir)
        async def ac(pg, kat, gecen):  # son gizlenmeden bu yana gecen saniye; sayfa sıfırdan yüklenir
            await pg.goto(SITE + '/manifest.webmanifest')  # aynı köken, uygulama çalışmıyor: kaydı bozmaz
            await pg.evaluate("s => localStorage.setItem('gk-gizli', String(Date.now() - s * 1000))", gecen)
            await pg.goto(U + '#k-' + kat); await pg.wait_for_selector('main h2, main .grid'); await pg.wait_for_timeout(500)
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, service_workers='block', is_mobile=True, has_touch=True)
        await ctx.add_init_script("Object.defineProperty(navigator, 'standalone', {configurable: true, get: () => true})")
        ps = await ctx.new_page(); ps.errs = []; ps.on('pageerror', lambda e: ps.errs.append(str(e)))
        await ps.goto(U); await ps.wait_for_selector('.grid')
        kat = await ps.get_attribute('main .grid .cat', 'data-cat')
        await ac(ps, kat, 600)
        check('uygulama 10 dk sonra yeniden açılınca son ekran değil ana sayfa', await ana_mi(ps))
        await ac(ps, kat, 30)
        check('kısa sürede yeniden açılırsa kaldığı yerde', await ps.evaluate('location.hash') == '#k-' + kat and await ps.locator('main .back').count() == 1)
        check('sayfa hatası yok (ana ekran uygulaması)', not ps.errs, ps.errs)
        await ctx.close()
        pt = await telefon(b)
        await ac(pt, kat, 600)
        check('tarayıcıda açılan kategori bağlantısı korunur', await pt.evaluate('location.hash') == '#k-' + kat and await pt.locator('main .back').count() == 1)
        await pt.context.close()

        # ---- F) açık pencere (şifreli telefon: ürüne dokununca tepki penceresi)
        a = await telefon(b, A, 'mayildiz')
        await ara(a, 'pinar'); await bitti(a)
        satir = a.locator('.li[data-ln] .tx').first
        await satir.click(); await a.wait_for_selector(DLG + '[open]')
        await geri(a)
        check('pencere açıkken geri: yalnızca pencere kapanır, arama yerinde', not await a.locator(DLG + '[open]').count() and
              await a.input_value('#q') == 'pinar' and (await durum(a)).get('gk') == 'ara')
        await geri(a)
        check('ikinci geri: ana sayfa', await ana_mi(a))
        await ileri(a)
        await satir.click(); await a.wait_for_selector(DLG + '[open]')
        await a.click(DLG + ' .tpb[data-v=begen]')
        await geri(a)
        check('pencerede seçim yapıldıysa geri hareketi pencereyi kapatmaz', await a.locator(DLG + '[open]').count() == 1 and await a.input_value('#q') == 'pinar')
        await uzakta(a, 180)
        check('kaydedilmemiş seçim uzun aradan sonra da korunur', await a.locator(DLG + '[open]').count() == 1 and await a.input_value('#q') == 'pinar')
        await a.click(DLG + ' [data-kapat]'); await a.wait_for_timeout(300)
        await satir.click(); await a.wait_for_selector(DLG + '[open]')
        await uzakta(a, 180)
        check('boş açık duran pencere uzun aradan sonra kapanır, ana sayfa', not await a.locator(DLG + '[open]').count() and await ana_mi(a))
        await ara(a, 'pinar'); await bitti(a)
        await satir.click(); await a.wait_for_selector(DLG + '[open]')
        await a.click(DLG + ' .tpb[data-v=yeni]')
        await uzakta(a, 180)
        check('"Bize dokundu" formu açıldıysa uzun aradan sonra korunur', await a.locator(DLG + '[open]').count() == 1)
        await a.click(DLG + ' [data-kapat]'); await a.wait_for_timeout(300)
        check('sayfa hatası yok (şifreli telefon)', not a.errs, a.errs)
        await a.context.close()
        await b.close()
    bitir()

asyncio.run(main())
