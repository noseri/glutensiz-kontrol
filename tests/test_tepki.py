#!/usr/bin/env python3
"""Tepkiler ve "bize dokundu" günlüğü: iki telefon (mayildiz ve heyybenbus), sabit test verisi.
Poco Loco satırları (test verisinde): 200 İST Nacho ↔ 1689 ANK Nacho, 201 İST Tortilla ↔ 1690 ANK Tortilla,
1782 ANK Crispy, 1783 ANK Sweet. Kalıcı numara (u) = satır sırası + 1."""
import asyncio, os, sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from ortak import A, H, API, DLG, api, check, bitir, tarayici, telefon, ara, axe_ihlal, ekran

AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
BUGUN = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
gun = lambda d: f'{d.day} {AYLAR[d.month - 1]} {d.year}'

async def ac(pg, i):
    await pg.locator(f'.li[data-ln="{i}"] .tx').first.click(); await pg.wait_for_selector(DLG + '[open]')
async def bas(pg, v): await pg.click(f'{DLG} .tpb[data-v={v}]')
async def basili(pg):
    return {v: await pg.get_attribute(f'{DLG} .tpb[data-v={v}]', 'aria-pressed') == 'true' for v in ('begen', 'begenme', 'favori', 'yeni')}
async def kaydet(pg):
    await pg.click(f'{DLG} .btn'); await pg.wait_for_timeout(800)
async def has(pg, i, cls):
    # satır sayfada birden çok kez görünebilir (diğer listedeki başlık altında da); hepsinde aynı rozet olmalı
    n = await pg.locator(f'.li[data-ln="{i}"]').count()
    return n > 0 and await pg.locator(f'.li[data-ln="{i}"] .rx-i.{cls}').count() == n
async def yok(pg, i, cls=''):
    return await pg.locator(f'.li[data-ln="{i}"] .rx-i{"." + cls if cls else ""}').count() == 0
async def rozet(pg, i):
    loc = pg.locator(f'.li[data-ln="{i}"] .rx')
    if not await loc.count(): return []
    hep = {tuple(t.split('\n')) for t in await loc.all_inner_texts()}
    return list(hep.pop()) if len(hep) == 1 else ['FARKLI', hep]
async def yenile(pg, q=None):
    await pg.reload(); await pg.wait_for_selector('.grid'); await pg.wait_for_timeout(900)
    if q: await ara(pg, q)

async def main():
    async with async_playwright() as p:
        b = await tarayici(p)
        a = await telefon(b, A, 'mayildiz')
        await ara(a, 'poco loco')
        v0 = await a.locator('article.card').first.get_attribute('class')
        ids = set(await a.eval_on_selector_all('.li[data-ln]', 'els => els.map(e => e.dataset.ln)'))
        check('poco loco: 6 ürün satırının hepsi dokunulabilir', ids == {'200', '201', '1689', '1690', '1782', '1783'}, ids)
        check('henüz tepki yok: rozet yok', await a.locator('.rx').count() == 0)
        # 1) mayildiz İstanbul satırını favoriye ekler
        await ac(a, 200)
        check('pencere: ürün adı + "iki listede de var"', await a.inner_text('#tpH') == 'Poco Loco Nacho Cipsi' and 'iki listede de var' in await a.inner_text('#tpSub'))
        check('kimin tepkisi olduğu yazıyor, odak başlıkta', await a.inner_text('#tpL') == 'Sizin tepkiniz (mayildiz)' and await a.evaluate("document.activeElement.id") == 'tpH')
        check('başta seçim yok; neden, yeni kayıt alanları ve geçmiş gizli', not any((await basili(a)).values()) and await a.locator(f'{DLG} [data-neden]').is_hidden() and await a.locator(f'{DLG} [data-yeni]').is_hidden() and await a.locator('#dkL').is_hidden())
        check('pencerede şifre alanı yok', await a.locator(f'{DLG} [name=sifre]').count() == 0)
        await bas(a, 'favori'); pr = await basili(a)
        check('favori seçilince beğendim de seçilir', pr['favori'] and pr['begen'] and not pr['begenme'], pr)
        await bas(a, 'begenme'); pr = await basili(a)
        check('beğenmedim favoriyi kaldırır, neden alanı açılır', pr['begenme'] and not pr['favori'] and not pr['begen'] and await a.locator(f'{DLG} [data-neden]').is_visible(), pr)
        await bas(a, 'favori'); pr = await basili(a)
        check('yeniden favori: beğenmedim kalkar, neden gizlenir', pr['favori'] and pr['begen'] and not pr['begenme'] and await a.locator(f'{DLG} [data-neden]').is_hidden(), pr)
        await kaydet(a)
        check('kaydedince kapanır, "Favorilere eklendi"', await a.locator(DLG + '[open]').count() == 0 and (await a.inner_text('#toast')).startswith('Favorilere eklendi'), await a.inner_text('#toast'))
        check('İstanbul satırında ♥ M', await rozet(a, 200) == ['M'] and await has(a, 200, 'fav'), await rozet(a, 200))
        check('eşi olan Ankara satırında da ♥ M', await has(a, 1689, 'fav'))
        check('başka ürünlerde rozet yok', await yok(a, 1782) and await yok(a, 201) and await yok(a, 1690))
        check('tat bilgisi güvenlik rengini değiştirmez', await a.locator('article.card').first.get_attribute('class') == v0, v0)
        s, j, _, _ = api('GET', '/veri', key=A)
        check('sunucuda anahtar kalıcı numara: u|201', [r['anahtar'] for r in j['tepkiler']] == ['u|201'], j['tepkiler'])
        # 2) heyybenbus görür, Ankara satırına "beğenmedim" der
        h = await telefon(b, H, 'heyybenbus')
        await ara(h, 'poco loco')
        check('heyybenbus telefonunda iki satırda da ♥ M', await has(h, 200, 'fav') and await has(h, 1689, 'fav'))
        await ac(h, 1689)
        check('pencerede diğer kişinin tepkisi: "mayildiz: Favori"', (await h.inner_text('#tpO')).strip() == 'mayildiz: Favori')
        await bas(h, 'begenme'); await h.fill(f'{DLG} [name=neden]', 'çok tuzlu'); await kaydet(h)
        bd = await rozet(h, 200)
        check('iki satırda ♥ M · 👎 H “çok tuzlu” (favori önce, beğenmedim gri)', bd == ['M', 'H', '“çok tuzlu”'] and await rozet(h, 1689) == bd and await has(h, 200, 'down'), bd)
        # 3) heyybenbus başka ürüne "bize dokundu" kaydı ekler
        await ac(h, 1782)
        check('düğme: "Bize dokundu ekle"', (await h.inner_text(f'{DLG} .tpb[data-v=yeni]')).strip() == 'Bize dokundu ekle')
        await bas(h, 'yeni')
        check('alanlar açılır; tarih bugün, ileri tarih seçilemez', await h.locator(f'{DLG} [data-yeni]').is_visible() and await h.input_value(f'{DLG} [name=dtarih]') == BUGUN.isoformat() and await h.get_attribute(f'{DLG} [name=dtarih]', 'max') == BUGUN.isoformat())
        nb = await h.locator(f'{DLG} .nb').all_inner_texts()
        check('olası neden: dört seçenek, hiçbiri seçili değil', [x.split('\n')[0] for x in nb] == ['Çapraz bulaşma şüphesi', 'Gluten dışı bir şey ağır geldi', 'Aynı gün başka şüpheli bir şey yendi', 'Bilmiyorum'] and await h.locator(f'{DLG} .nb[aria-pressed=true]').count() == 0, nb)
        await h.click(f'{DLG} .nb[data-dn=agir]'); await h.click(f'{DLG} .nb[data-dn=bulasma]')
        check('olası neden tek seçimli (son dokunulan seçili)', await h.locator(f'{DLG} .nb[aria-pressed=true]').count() == 1 and await h.get_attribute(f'{DLG} .nb[data-dn=bulasma]', 'aria-pressed') == 'true')
        check('paket bilgisi alanı: parti, SKT, üretici; 80 karakter', await h.get_attribute(f'{DLG} [name=dparti]', 'placeholder') == 'Parti no, son kullanma tarihi, üretici' and await h.get_attribute(f'{DLG} [name=dparti]', 'maxlength') == '80')
        await h.fill(f'{DLG} [name=dnotu]', '2 saat sonra karın ağrısı'); await h.fill(f'{DLG} [name=dparti]', 'L2611'); await kaydet(h)
        check('bildirim: ikinizde de uyarı', 'ikinizde de uyarı' in await h.inner_text('#toast'), await h.inner_text('#toast'))
        check('satırda kırmızı "Dokundu · heyybenbus"', await has(h, 1782, 'dok') and (await h.locator('.li[data-ln="1782"] .rx-i.dok').first.inner_text()).strip() == 'Dokundu · heyybenbus')
        check('marka kartında "Bu markanın 1 ürünü size dokundu"', 'Bu markanın 1 ürünü size dokundu' in await h.locator('article.card').first.inner_text())
        # 4) mayildiz görür, ikinci bir kayıt (10 gün önce) ekler, sonra kendi kaydını siler
        await yenile(a, 'poco loco')
        check('mayildiz: dokundu uyarısı da görünüyor', await has(a, 1782, 'dok') and 'size dokundu' in await a.locator('article.card').first.inner_text())
        await ac(a, 1782)
        li = await a.locator('#dkL li').all_inner_texts()
        check('pencerede kayıt: tarih · kim — not · parti; başkasınınki silinemez', li == [f'{gun(BUGUN)} · heyybenbus — “2 saat sonra karın ağrısı” · Çapraz bulaşma şüphesi · Paket: L2611'] and await a.locator('#dkL [data-dsil]').count() == 0, li)
        check('düğme: "Yeniden dokundu ekle"', (await a.inner_text(f'{DLG} .tpb[data-v=yeni]')).strip() == 'Yeniden dokundu ekle')
        await bas(a, 'yeni'); await a.fill(f'{DLG} [name=dtarih]', (BUGUN + timedelta(days=3)).isoformat()); await kaydet(a)
        check('ileri tarih: uyarı, kaydedilmez', 'İleri bir tarih' in await a.inner_text(f'{DLG} .err') and await a.locator(DLG + '[open]').count() == 1)
        on = BUGUN - timedelta(days=10)
        await a.fill(f'{DLG} [name=dtarih]', on.isoformat()); await kaydet(a)
        check('iki kayıt: "Dokundu 2 kez · heyybenbus, mayildiz"', (await a.locator('.li[data-ln="1782"] .rx-i.dok').first.inner_text()).strip() == 'Dokundu 2 kez · heyybenbus, mayildiz')
        await ac(a, 1782)
        li = await a.locator('#dkL li').all_inner_texts()
        check('geçmiş yeniden eskiye; kendi kaydında "Sil"', len(li) == 2 and li[0].startswith(gun(BUGUN) + ' · heyybenbus') and li[1].startswith(gun(on) + ' · mayildiz') and await a.locator('#dkL [data-dsil]').count() == 1, li)
        await a.click('#dkL [data-dsil]'); await a.wait_for_timeout(100)
        check('silmeden önce onay', await a.locator('#dkL .cf').count() == 1)
        await a.click('#dkL [data-dsilevet]'); await a.wait_for_timeout(800)
        check('silindi: bildirim, tek kayıt kaldı', (await a.inner_text('#toast')).startswith('Kayıt silindi') and len(await a.locator('#dkL li').all_inner_texts()) == 1)
        await a.keyboard.press('Escape'); await a.wait_for_timeout(150)
        check('rozet yeniden "Dokundu · heyybenbus"', (await a.locator('.li[data-ln="1782"] .rx-i.dok').first.inner_text()).strip() == 'Dokundu · heyybenbus')
        # 5) değişiklik yoksa Kaydet sunucuya gitmez
        gid = []
        a.on('request', lambda r: gid.append(r.url) if r.url.startswith(API) and r.method == 'POST' else None)
        await ac(a, 200); await kaydet(a)
        check('değişiklik yoksa pencere kapanır, istek gitmez', await a.locator(DLG + '[open]').count() == 0 and not gid, gid)
        # 6) ana sayfa: Tepkilerimiz
        await a.click('#clear'); await a.wait_for_timeout(300)
        sec = await a.locator('.sec', has_text='Tepkilerimiz').inner_text()
        check('ana sayfada "Tepkilerimiz 2"', ' '.join(sec.split()) == 'Tepkilerimiz 2', sec)
        tabs = [' '.join(t.split()) for t in await a.locator('.tp-tabs [data-tpt]').all_inner_texts()]
        check('sekmeler: Dokunan 1, Favori 1, Beğenilmeyen 1 (İkimiz de yok: biri beğenmedi); Dokunan açık', tabs == ['Dokunan 1', 'Favori 1', 'Beğenilmeyen 1'] and await a.get_attribute('.tp-tabs [data-tpt=dokundu]', 'aria-pressed') == 'true', tabs)
        d = await a.locator('.tp-row .tp-d').first.inner_text()
        check('dokunan satırında son kayıt', d == f'Son: {gun(BUGUN)} · heyybenbus — “2 saat sonra karın ağrısı” · Çapraz bulaşma şüphesi · Paket: L2611', d)
        cut = await a.evaluate("[...document.querySelectorAll('.tt span')].filter(e => e.scrollWidth > e.clientWidth).map(e => e.textContent)")
        check('sekme adları kesilmiyor (390 px)', not cut, cut)
        await a.click('.tp-tabs [data-tpt=favori]'); await a.wait_for_timeout(200)
        rows = await a.locator('.tp-row').all_inner_texts()
        check('iki listedeki aynı ürün tek satır, iki kişinin tepkisiyle', len(rows) == 1 and rows[0].startswith('Poco Loco Nacho Cips') and rows[0].split('\n')[1:] == ['M', 'H', '“çok tuzlu”'], rows)
        await a.locator('.tp-row').first.click(); await a.wait_for_timeout(400)
        check('satıra dokununca arama', (await a.input_value('#q')).startswith('Poco Loco Nacho Cips') and await a.locator('.li[data-ln="200"]').count() >= 1)
        await a.click('#clear'); await a.wait_for_timeout(300)
        tb = {'alan': 'gida', 'marka': 'Poco Loco'}
        api('POST', '/tepki', dict(tb, anahtar='u|202', urun='Poco Loco Tortilla Cipsi', tepki='begen'), H)
        api('POST', '/tepki', dict(tb, anahtar='u|1691', urun='Poco Loco Tortilla Cips', favori=True), A)
        await yenile(a)
        tabs = [' '.join(t.split()) for t in await a.locator('.tp-tabs [data-tpt]').all_inner_texts()]
        check('“İkimiz de” sekmesi: ikisinin de beğendiği ürün (iki listede ayrı satırlar, tek ürün)', 'İkimiz de 1' in tabs, tabs)
        await a.click('.tp-tabs [data-tpt=ikimiz]'); await a.wait_for_timeout(200)
        rows = await a.locator('.tp-row').all_inner_texts()
        check('“İkimiz de” satırı: Tortilla, ♥ M ve 👍 H', len(rows) == 1 and 'Tortilla' in rows[0] and rows[0].split('\n')[1:] == ['M', 'H'], rows)
        check('beğenilmeyen ürün “İkimiz de”de yok', not any('Nacho' in r for r in rows))
        # 7) Bizim listemiz ürünü: tepki düzeltmeden sonra da kalır
        it = a.locator('article.v-us > .us-it', has_text='Kakaolu Kurabiye').first
        await it.locator('.us-t').click(); await a.wait_for_selector(DLG + '[open]')
        check('Bizim listemiz ürününde pencere', (await a.inner_text('#tpSub')).startswith('Bizim listemiz') and await a.inner_text('#tpH') == 'Eti Glutensiz Kakaolu Kurabiye')
        await bas(a, 'begen'); await kaydet(a)
        await a.locator('article.v-us > .us-it', has_text='Kakaolu Kurabiye').first.locator('[data-duzelt]').click(); await a.wait_for_selector('dialog.sheet[open]')
        await a.fill('dialog [name=urun]', 'Glutensiz Kakaolu Kurabiye 150 g'); await a.click('dialog[open] .btn'); await a.wait_for_timeout(800)
        it = a.locator('article.v-us > .us-it', has_text='150 g').first
        check('düzeltilen üründe tepki duruyor (👍 M)', await it.count() == 1 and (await it.locator('.rx').inner_text()).strip() == 'M')
        # 8) tepkiyi kaldırma
        await ara(a, 'poco loco'); await ac(a, 1689)
        check('eşli satırda kendi tepkisi seçili gelir', (await basili(a))['favori'])
        await bas(a, 'begen'); await kaydet(a)
        check('"Tepki kaldırıldı", yalnız heyybenbus kaldı', (await a.inner_text('#toast')).startswith('Tepki kaldırıldı') and await rozet(a, 200) == ['H', '“çok tuzlu”'], await rozet(a, 200))
        # 9) aynı kişinin aynı üründe iki anahtarla kalmış kaydı: en yenisi görünür, kaydedince eskisi silinir
        base = {'alan': 'gida', 'marka': 'Poco Loco', 'urun': 'Poco Loco Nacho Cips'}
        api('POST', '/tepki', dict(base, anahtar='u|1690', tepki='begenme'), A); await asyncio.sleep(1.1)
        api('POST', '/tepki', dict(base, anahtar='u|201', tepki='begen', urun='Poco Loco Nacho Cipsi'), A)
        await yenile(a, 'poco loco')
        check('en yenisi görünür (👍 M, sonra 👎 H)', await rozet(a, 1689) == ['M', 'H', '“çok tuzlu”'], await rozet(a, 1689))
        await ac(a, 1689); await bas(a, 'favori'); await kaydet(a); await a.wait_for_timeout(500)
        s, j, _, _ = api('GET', '/veri', key=A)
        mine = [r for r in j['tepkiler'] if r['kisi'] == 'mayildiz' and r['anahtar'] in ('u|201', 'u|1690')]
        check('kaydedince eski anahtardaki kayıt silinir', len(mine) == 1 and mine[0]['anahtar'] == 'u|201' and mine[0]['favori'] == 1, mine)
        # 10) listeden düşen ürünler ana sayfada işaretli
        api('POST', '/tepki', {'anahtar': 'u|999999', 'alan': 'gida', 'marka': 'Poco Loco', 'urun': 'Poco Loco Eski Çeşit', 'favori': True}, H)
        await a.click('#clear'); await a.wait_for_timeout(200)
        await a.locator('article.v-us > .us-it', has_text='150 g').first.locator('[data-cikar]').click(); await a.wait_for_timeout(100)
        await a.locator('[data-cikarevet]').click(); await a.wait_for_timeout(800)
        await yenile(a)
        await a.click('.tp-tabs [data-tpt=favori]'); await a.wait_for_timeout(200)
        eski = a.locator('.tp-row', has_text='Eski Çeşit')
        check('dernek listesinden düşen favori: uyarı notu', await eski.count() == 1 and 'Dernek listelerinde artık bu satır yok' in await eski.inner_text())
        await a.click('.tp-tabs [data-tpt=begen]'); await a.wait_for_timeout(200)
        cik = a.locator('.tp-row', has_text='Kakaolu Kurabiye')
        check('Bizim listemiz’den çıkarılan ürün: not', await cik.count() == 1 and 'Bizim listemiz’den çıkarıldı' in await cik.inner_text())
        # 11) klavye, erişilebilirlik
        await ara(a, 'poco loco')
        await a.locator('.li[data-ln="1782"] .tpk').first.focus(); await a.keyboard.press('Enter'); await a.wait_for_timeout(200)
        check('klavyeyle Enter pencereyi açar', await a.locator(DLG + '[open]').count() == 1 and await a.inner_text('#tpH') == 'Poco Loco Crispy')
        await bas(a, 'yeni')
        v = await axe_ihlal(a, DLG); check('pencere erişilebilir (axe)', not v, v)
        await ekran(a, 'tepki_pencere'); await a.keyboard.press('Escape')
        v = await axe_ihlal(a); check('arama sonuçları erişilebilir (axe)', not v, v)
        await a.click('#clear'); await a.wait_for_timeout(300)
        v = await axe_ihlal(a); check('ana sayfa erişilebilir (axe)', not v, v)
        await a.locator('.sec', has_text='Tepkilerimiz').scroll_into_view_if_needed(); await ekran(a, 'tepki_ana')
        dk = await telefon(b, A, 'mayildiz', scheme='dark'); await ara(dk, 'poco loco'); await ekran(dk, 'tepki_koyu')
        await ac(dk, 1782); await bas(dk, 'yeni'); await dk.wait_for_timeout(200); await ekran(dk, 'tepki_pencere_koyu')
        for n, pg in (('mayildiz', a), ('heyybenbus', h), ('koyu', dk)):
            check(f'sayfa hatası yok ({n})', not pg.errs, pg.errs)
        await b.close()
    bitir()
asyncio.run(main())
