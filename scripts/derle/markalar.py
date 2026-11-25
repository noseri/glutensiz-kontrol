# -*- coding: utf-8 -*-
"""Marka listesi, takma adlar ve metinden marka bulma."""
import re

from .metin import compact


# ----------------------------------------------------------------- markalar ----
# (görünen ad, [yazım varyantları]) — varyantlar norm+compact ile karşılaştırılır
BRANDS = [
    ('Atatürk Orman Çiftliği', ['ataturk orman ciftligi', 'aoc', 'a o c']),
    ('Dr. Oetker', ['dr oetker', 'droetker', 'dr outker']),
    ('Dr. Gluten', ['dr gluten', 'drgluten', 'dr gluen']),
    ('Dr. Ekmek', ['dr ekmek']),
    ('Dr. C. Tuna', ['dr c tun', 'dr c tuna']),
    ('Elisa Gold', ['elisa gold', 'eliza gold', 'elize gold', 'elze gold']),
    ('Schär', ['schar', 'schaer']),
    ('Glutensiz Fabrika', ['glutensiz fabrika']),
    ('Glutensiz Ada', ['glutensiz ada']),
    ('Glutensiz Mutfak', ['glutensiz mutfak']),
    ('Glutensiz Nokta', ['glutensiz nokta']),
    ('Ege Glutensiz', ['ege glutensiz', 'ege']),
    ('Ali Kasap', ['ege fermente', 'ege ali kasap', 'ali kasap']),
    ('Green Dream', ['green dream']),
    ('Crunch Wavy', ['crunch wavy']),
    ('Crunch Stick', ['crunch stick']),
    ('Poco Loco', ['poco loco', 'poco loko']),
    ('Rocky Rice', ['rocky rice']),
    ('Thin Think', ['thin think']),
    ('Simon Levelt', ['simon levelt']),
    ('Trakya Agro', ['trakya agro']),
    ('Trakya Birlik', ['trakya birlik']),
    ('Trakya Çiftliği', ['trakya ciftligi']),
    ('Tire Süt', ['tire sut']),
    ('Saklı Cennet', ['sakli cennet']),
    ('Ton Ton', ['ton ton']),
    ('Kaptan Memo', ['kaptan memo']),
    ('Bolulu Hasan Usta', ['bolulu hasan usta', 'bolulu hasan ustada', 'bolulu']),
    ('Abdurrahman Tatlıcı', ['abdurrahman tatlici']),
    ('Ambar Evim', ['ambar evim']),
    ('Babamın Bahçesi', ['babamin bahcesi']),
    ('Olive Farm', ['olive farm', 'olive form']),
    ('Sade Organik', ['sade organik']),
    ('Nar Gourmet', ['nar gourmet']),
    ('Lütfiye Amasra', ['lutfiye amasra']),
    ('Kurukahveci Mehmet Efendi', ['kurukahveci mehmet efendi', 'kuru kahveci mehmet efendi']),
    ('Rani Çiftliği', ['rani ciftligi', 'raini ciftligi', 'rani cifligi']),
    ('Tam Tarım', ['tam tarim']),
    ('Organik Bahçe', ['organik bahce', 'organic bahce']),
    ('Organic Garden', ['organic garden']),
    ('Güzel Gıda', ['guzel gida', 'guzel ada gida', 'guzel ada pharma']),
    ('İngro', ['ingro gida', 'ingro']),
    ('Doğaçlama Gıda', ['dogaclama gida']),
    ('Agromica', ['agromica gida', 'agromica']),
    ('Mor Gıda', ['mor gida', 'mor gurme']),
    ('Ladin Organics', ['ladin organics']),
    ('Le Pain des Fleurs', ['le pain des fleurs']),
    ('Isola Bio', ['isola bio']),
    ('Nocciolata', ['nocciolata']),
    ('Fiordifrutta', ['fiordifrutta', 'fiordi frutta']),
    ('Big Babol', ['big babol']),
    ('Peyman Bahçeden', ['peyman bahceden']),
    ('Peyman Dorleo', ['peyman dorleo']),
    ('Peyman Çitliyo', ['peyman citliyo', 'kara simsek']),
    ('Saray Muhallebicisi', ['saray muhallebicisi']),
    ('Eyüp Sabri Tuncer', ['eyup sabri tuncer']),
    ('Bonny Tiny', ['bonny tiny', 'bonny tinny']),
    ('DK Dent', ['dk dent']),
    ('The Balm', ['the balm']),
    ('Jack N’Jill', ['jack njill', 'jack n jill']),
    ('Dove', ['dove man care', 'dove']),
    ('Evyap', ['evyap']),
    ('Mutlu Beslen Kooperatifi', ['mutlu beslen kooperatifi', 'mutlu beslen']),
    ('Sevgi Fırını (Love and Bakes)', ['sevgi firini', 'sevgi firininda', 'love and bakes', 'love bakes',
                                       'love &bakes', 'love & bakes', 'love and']),
    ('Mayalıhane', ['mayalihane', 'mayali hane']),
    ('EatReal', ['eatreal', 'eat real']),
    ('La Fiesta', ['lafiesta', 'la fiesta']),
    ('Casa Fiesta', ['nachos chips casa fiesta', 'casa fiesta']),
    ('Santa Maria', ['santa maria']),
    ('St. Dalfour', ['st dalfour']),
    ('Carte d’Or', ['carte dor', 'carte d or']),
    ('Tarım Kredi', ['tarim kredi birligi', 'tarim kredi']),
    ('Halk Ekmek (Ankara)', ['ankara halk ekmek', 'ankara buyuksehir belediyesi', 'met vak', 'metvak',
                             'ankara baskent market', 'baskent market', 'ankara halk ekmek baskent market']),
    ('Halk Ekmek (İstanbul)', ['istanbul halk ekmek', 'istanbul buyuksehir belediyesi']),
    ('Kent Ekmek (İzmir)', ['izmir buyuksehir belediyesi']),
    ('Kınalıeller Halk Ekmek', ['kinalieller halk ekmek']),
    ('Denizli Ata Fırın', ['denizli ata firin']),
    ('Polmak Gold', ['polmak gold', 'gold']),
    ('Back Home', ['back home', 'backhome', 'bake home']),
    ('Nature’s', ['natures']),
    ('Good Cops', ['good cops', 'goodcops']),
    ('Herbalife', ['herbalife', 'herbal life']),
    ('MF Foods', ['mf foods']),
    ('Tomru Foods', ['tomru foods']),
    ('Talya Foods', ['talya foods']),
    ('Nuhun Ankara', ['nuhun ankara']),
    ('Most Natura', ['most natura']),
    ('Gurme Lezzetler', ['gurme lezzetler']),
    ('Macaron Kafe', ['macaron kafe', 'macoron kafe']),
    ('Cemali Kafe', ['cemali kafe', 'cemali cafe']),
    ('Pakmaya', ['pakmaya', 'pak maya']),
    ('Pak Şeker', ['pak seker']),
    ('Şeker Dünyası', ['seker dunyasi']),
    ('Fiero', ['arolez fiero', 'fiero']),
    ('Nespresso', ['nestle nespresso', 'nespresso']),
    ('Selamlique', ['cezbeli selamlique', 'cebeli selamlique', 'selamlique', 'cezbeli']),
    ('Kikkoman', ['tamari kikkoman', 'kikkoman']),
    ('Dovido', ['temel gida dovido', 'dovido']),
    ('Karper', ['bel karper', 'karper']),
    ('M Life (Migros)', ['migros m life', 'm life', 'mlife']),
    ('Marks & Spencer', ['m&s marks&spencer', 'm & s marks & spencer', 'marks spencer']),
    ('Ta!da!', ['tada', 'ta da']),
    ('Sin Gluten', ['sin gluten']),
    ('Çerez Tabağı', ['cereztabagi', 'cerez tabagi']),
    ('Arzu Kuruyemiş', ['arzu kuruyemis']),
    ('Ahmet İpek', ['ahmet ipek']),
    ('Kemal Kükrer', ['kemal kukrer']),
    ('Seres Foods', ['seres foods']),
    ('Bizim Vatan', ['bizim vatan']),
    ('Büyük Usta', ['buyuk usta']),
    ('Wai Wai', ['wai wai']),
    ('Ramazan Keyfi', ['ramazan keyfi']),
    ('Şefik Usta', ['sefik usta']),
    ('Ayaş Şakir Efendi', ['ayas sakir efendi']),
    ('Hasan Çavuş', ['hasan cavus']),
    ('By Moching', ['by moching']),
    ('Dondurmacı Amca', ['dondurmaci amca']),
    ('Gönül Kahvesi', ['gonul kahvesi']),
    ('Sweet Heaven Cakes', ['sweet heaven cakes']),
    ('Chocolat Stella', ['chocolat stella']),
    ('Kinder', ['kinder']),
    ('Coca-Cola', ['coca cola']),
    ('Lipton', ['lipton ice tea', 'lipton']),
    ('Didi', ['didi ice tea', 'didi icetea', 'didi']),
    ('Unilever Food Solutions', ['unilever food solutions', 'unileverfoodsolutions']),
    ('Bez-Gluten', ['bezgluten', 'bez gluten']),
    ('Bi-Aglut', ['biaglut', 'bi aglut']),
    ('Ay-Pop', ['aypop', 'ay pop']),
    ('Dum Dums', ['dum dums', 'dumdums']),
    ('Patisswiss', ['patisswiss', 'patiswiss']),
    ('Rawsome', ['rawsome', 'r awsome', 'rowsome']),
    ('Snickers', ['snickers', 'sneckers']),
    ('Canderel', ['canderel', 'candarel']),
    ('Sensodyne', ['sensodyn', 'sensodyne']),
    ('Gökkuşağı', ['gokkusagi']),
    ('Özsüt', ['ozsut', 'ozsut firmasi', 'karaorman']),
    ('İKEA', ['ikea']),
    ('Starbucks', ['starbucks']),
    ('Nestlé', ['nestle']),
    ('Mondelez / Kent', ['kent urunleri', 'kent firmasinin', 'kent seker', 'kent gida', 'kent modelez',
                         'mondalez', 'mondelez']),
    ('Abdi İbrahim', ['abdi ibrahim']),
    ('Koçak Farma', ['kocak farma']),
    ('Santa Farma', ['santa farma']),
    ('Berko', ['berko']),
    ('Bilim İlaç', ['bilim ilac']),
    ('NBL Probiotic', ['nbl probiotic', 'nbl probiyotic', 'nbl']),
    ('New Life (Sifar)', ['sifar']),
    ('Möller’s', ['mollers']),
    ('RC Farma', ['rc farma']),
    ('Forever Living', ['forever living', 'forever']),
    ('Wellcare', ['wellcare']),
    ('Vitabiotics', ['vitabiotics']),
    ('Atavit', ['atavit']),
    ('Bakso Sandoz', ['bakso sandoz']),
    ('Sandoz', ['sandoz']),
    ('Tukaş', ['tukas']),
    ('Pınar', ['pinar']),
    ('Bal Kaymak', ['balkaymak']),
    ('Mader', ['mader', 'madercous']),
    ('Yörsan', ['yorsan']),
    ('İçim', ['icim']),
    ('Gürsoy', ['gursoy']),
    ('Cipsaş', ['cipsas']),
    ('Fo', ['fo']),
    ('IR', ['ir']),
    ('Nk', ['nk']),
    ('Bol Bol', ['bol bol', 'bolbol']),
    ('Canbis (Burch)', ['canbis', 'burch']),
    ('Pernigotti', ['pernigotti']),
    ('Vie Life', ['vie life']),
    ('Dias Special', ['dias special']),
    ('Saffet Abdullah', ['saffet abdullah']),
    ('Çayırova', ['cayirova']), ('İtimat', ['itimat']), ('Sakıpağa', ['sakipaga']), ('Dalgıçlar', ['dalgiclar']),
    ('PopTip', ['poptip']), ('Sütaş', ['sutas']), ('Yörükoğlu', ['yorukoglu']), ('Özgüllü', ['ozgullu']),
    ('Baltalı', ['baltali']), ('Gürsüt', ['gursut']), ('Bakraç', ['bakrac']), ('Erpiliç', ['erpilic']),
    ('Chupa Chups', ['chupa chups']),
    ('Etala', ['etala', 'et ala']),
    ('Elite Naturel', ['elite naturel', 'elit naturel']),
    ('Has Tavuk', ['has tavuk', 'hastavuk']),
    ('Sante01', ['sante01', 'sante 01']),
    ('Vak-Mak', ['vak mak', 'vakmak']),
    ('Muratbey', ['murat bey', 'muratbey']),
    ('Rice Up', ['rice up']),
    ('Meyveli Tatlı Kinoa', ['meyveli tatli kinoa']),
    ('Unilever', ['unilever']),
    ('Oranca', ['oranca']),
]
_BRAND_ALIAS = {}
BRAND_NAME = {}
for disp, variants in BRANDS:
    key = compact(disp)
    BRAND_NAME[key] = disp
    _BRAND_ALIAS[key] = key
    for v in variants:
        _BRAND_ALIAS[compact(v)] = key
_ALIAS_MAXTOK = 6

# satırın herhangi bir yerinde geçerse marka sayılır (dağıtıcı adıyla başlayan satırlar için)
ANYWHERE = [(re.compile(r'\b' + p + r'\b'), compact(d)) for p, d in [
    ('le pain des fleurs', 'Le Pain des Fleurs'), ('nocciolata', 'Nocciolata'),
    ('fiordi ?frutta', 'Fiordifrutta'), ('isola bio', 'Isola Bio'),
]]

# Tek başına marka olamayacak ilk kelimeler
STOP_FIRST = set('''
a b c ve ile de da bu su o ya not notu onemli dikkat lutfen gibi diger diger tum butun her hepsi hepsini tumu
genellikle sadece only yeni the an el la le des di sade organik glutensiz gluten free glutenfree
dondurma sutlu bitter beyaz kakaolu findikli cikolatali cikolata ic cig kuru kurutulmus kabuklu kavrulmus tuzlu
tuzsuz bol aci klasik taco tatli badem findik ceviz fistik kaju hurma cranberry dut erik kayisi uzum visne incir
leblebi benekli kabak misir bezelye sultani taze borulce enginar garnitur firin kazandibi keskul tavuk tavukgogsu
krem sakizli su muhallebi profiterol sutlac menudeki menuden yogurt yogurtlari peynir sut ayran kefir tereyagi
ekmek un unu bisküvi biskuvi meyveli sebze patates domates biber salca konserve konservesi makarna sehriye
eriste bulgur irmik kakao kahve cay seker sekeri sekerleme sakiz lokum helva tahin pekmez recel bal nar sirke
sos sosu ketcap mayonez hardal tursu zeytin yag yagi margarin maya kabartma vanilya pudra toz krema kaymak labne
lor kasar tulum hellim dil orgu mozzarella cheddar firmasi firmanin firma firmalar asagida ornegin uyari
yukaridaki yukarida gercek bizim urunlerimizi urunlerimiz cok cesit kodlu bunyesinde fasulye mercimek nohut
kirmizi sari yesil kara siyah light extra ekstra mini maxi buyuk kucuk tane tablet surup kapsul krem jel
toz granul sivi kati hazir tum cesitleri karisik karisim tahilli tam yarim yagli yagsiz laktozsuz laktozlu
kesme kup kase kutu paket tek cift agiz dogal bebek tel sube subeler gun raki votka cin bira
dondurmasi sicak kahvaltilik medikal uzerinde urunlerin
pirinc nisasta karabugday kestane keciboynuzu hindistan chia kinoa teff yulaf amarant sorgum galeta
tavuk hindi dana pilic et fume jambon kavurma salam sosis sucuk pastirma doner kofte harci
icecek icecegi icecekleri meyve suyu sulari limonata gazoz soda maden
'''.split())
STOP_FIRST.discard('')
NEED_SECOND = set('dr mr st la le el the m by big green poco rocky thin crunch saray tire sakli ton kaptan'.split())
LEAD_SKIP = set('organik ve glutensiz oranca orancaorganik temel tum butun migros bel arolez tamari jacobs dikkat not'.split())
LEAD_SKIP_UNLESS_NEXT = {'glutensiz': {'fabrika', 'ada', 'mutfak', 'nokta'}}


def find_alias(toks, start):
    """toks[start:] başında bilinen bir marka varyantı var mı? (en uzun eşleşme)"""
    for k in range(min(_ALIAS_MAXTOK, len(toks) - start), 0, -1):
        key = ''.join(toks[start:start + k])
        if key in _BRAND_ALIAS:
            return _BRAND_ALIAS[key], k
    return None, 0


def detect_brand(text_norm):
    """Satır metninden marka anahtarı ve marka kelime aralığı. Bulunamazsa (None, None)."""
    toks = text_norm.split()
    if not toks:
        return None, None
    for rx, key in ANYWHERE:
        m = rx.search(text_norm)
        if m:
            # aralığı kelime indisine çevir
            pre = text_norm[:m.start()].split()
            return key, (len(pre), len(pre) + len(m.group(0).split()))
    start = 0
    # baştaki gürültü kelimelerini atla
    while start < len(toks) - 1:
        t = toks[start]
        if t in LEAD_SKIP_UNLESS_NEXT and toks[start + 1] in LEAD_SKIP_UNLESS_NEXT[t]:
            break
        if t in LEAD_SKIP:
            # atlamadan önce: burada bilinen bir marka başlıyor mu? (örn. "organik bahce")
            key, k = find_alias(toks, start)
            if key and k > 1:
                return key, (start, start + k)
            start += 1
            continue
        break
    key, k = find_alias(toks, start)
    if key:
        return key, (start, start + k)
    for s0 in ([start, 0] if start else [0]):
        t0 = toks[s0]
        if t0 in NEED_SECOND and s0 + 1 < len(toks):
            return t0 + toks[s0 + 1], (s0, s0 + 2)
        if t0 in STOP_FIRST or t0 in LEAD_SKIP or len(t0) < 2 or re.match(r'^\d', t0):
            if s0 == 0 and toks[0] in LEAD_SKIP and toks[0] not in STOP_FIRST:
                return toks[0], (0, 1)   # örn. "Oranca Filtre Kahve" -> Oranca
            continue
        return t0, (s0, s0 + 1)
    return None, None
