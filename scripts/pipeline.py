#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Glutensiz Liste Birleştirici — işleme hattı (pipeline)

Kullanım:
  python3 -I pipeline.py pages.json data.json [onceki_data.json]

pages.json biçimi (WordPress REST API sayfa nesneleri):
  {"ist_gida": [page], "ist_ilac": [page], "ist_kozmetik": [page],
   "ist_takviye": [page], "ank": [page]}

Çıktı: ön yüzün okuduğu data.json
"""
import datetime
import difflib
import json
import re
import sys
import unicodedata

from bs4 import BeautifulSoup

PIPELINE_VERSION = 3

# ---------------------------------------------------------------- metin ----
_TR_UP = {'I': 'ı', 'İ': 'i'}
_FOLD = str.maketrans({'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
                       'â': 'a', 'î': 'i', 'û': 'u', 'ª': 's'})
_APOS = "’'`´‘ʼ"
_SUFFIX_AFTER_APOS = re.compile(
    "[" + _APOS + "](?:nın|nin|nun|nün|ın|in|un|ün|ı|i|u|ü|a|e|da|de|ta|te|dan|den|tan|ten|yla|yle|la|le)\\b")


def clean(s):
    """Görünen metni sadeleştir (boşluk, görünmez karakter)."""
    s = unicodedata.normalize('NFC', s or '')
    s = s.replace('\u200d', '').replace('\u200b', '').replace('\xa0', ' ').replace('\ufeff', '')
    s = re.sub(r'[ \t\r\f\v]+', ' ', s)
    return s.strip()


def norm(s):
    """Arama/eşleştirme için: Türkçe küçük harf, aksan yok, noktalama yok."""
    s = clean(s)
    s = ''.join(_TR_UP.get(c, c) for c in s).lower()
    s = _SUFFIX_AFTER_APOS.sub('', s)
    s = re.sub('[' + _APOS + ']', '', s)
    s = s.translate(_FOLD)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('&', ' & ')
    s = re.sub(r'[^a-z0-9%&+]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    # "i r m i k" -> "irmik", "a o c" -> "aoc"
    s = re.sub(r'\b(?:[a-z0-9] ){2,}[a-z0-9]\b', lambda m: m.group(0).replace(' ', ''), s)
    return s


def tr_lower(s):
    return ''.join(_TR_UP.get(c, c) for c in s).lower()


def tr_title(w):
    if not w:
        return w
    first = {'i': 'İ', 'ı': 'I'}.get(w[0], w[0].upper())
    return first + tr_lower(w[1:])


def compact(s):
    return norm(s).replace(' ', '')


def fuzzkey(k):
    return re.sub(r'(.)\1+', r'\1', k)


def stem(t):
    for suf in ('lari', 'leri', 'lar', 'ler', 'lik', 'luk', 'li', 'lu', 'si', 'su', 'i', 'u', 'a', 'e'):
        if t.endswith(suf):
            rest = t[:-len(suf)]
            if len(rest) >= 4 or (len(rest) == 3 and suf in ('lari', 'leri', 'lar', 'ler', 'li', 'lu', 'i', 'u')):
                return rest
    return t


# ------------------------------------------------------------ kategoriler ----
# (id, görünen ad, alan, aile, desenler) — sıra önemli: özel olan önce
CATS = [
    ('etiket-oku', 'Etiketi okunarak alınacak firmalar', 'gida', 'etiket',
     [r'okunarak alinmasi', r'uzeri okunarak', r'uzerini okuyacagimiz unilever gida', r'^unilever',
      r'^kent firmasi', r'^nestle firmasi', r'allerjen uyarisi uygulamasi']),
    ('atistirmalik', 'Atıştırmalık', 'gida', 'atistirmalik', [r'^atistirmalik']),
    ('ayran', 'Ayran', 'gida', 'ayran', [r'^ayran']),
    ('badem-unu', 'Badem unu', 'gida', 'un', [r'^badem unu']),
    ('baharat', 'Baharat', 'gida', 'baharat', [r'^baharat']),
    ('bal', 'Bal', 'gida', 'bal', [r'^bal\b']),
    ('balik', 'Balık', 'gida', 'et', [r'^balik']),
    ('alkollu', 'Alkollü içkiler (bira, rakı, votka, cin)', 'gida', 'alkol',
     [r'^bira\b', r'^raki\b', r'^ickiler', r'^raki votka']),
    ('sarap', 'Şarap', 'gida', 'alkol', [r'^sarap']),
    ('boza', 'Boza', 'gida', 'boza', [r'^boza']),
    ('bulgur', 'Bulgur (mısır bulguru)', 'gida', 'un', [r'^bulgur']),
    ('chia', 'Chia tohumu', 'gida', 'un', [r'^chia']),
    ('cips', 'Cips', 'gida', 'atistirmalik', [r'^cips']),
    ('cay', 'Çay', 'gida', 'icecek', [r'^cay\b']),
    ('cikolata-sosu', 'Çikolata sosu', 'gida', 'cikolata', [r'^cikolata sosu']),
    ('damla-cikolata', 'Damla çikolata', 'gida', 'cikolata', [r'^damla cikolata']),
    ('sicak-cikolata', 'Sıcak çikolata', 'gida', 'cikolata', [r'^sicak cikolata']),
    ('ekmek-ustu', 'Ekmek üstü çikolata, ezme ve kremalar', 'gida', 'cikolata', [r'^ekmek ustu']),
    ('cikolata', 'Çikolata', 'gida', 'cikolata', [r'^cikolata']),
    ('tatlandirici', 'Tatlandırıcı', 'gida', 'seker', [r'tatlandirici', r'^diyabetikler']),
    ('domates', 'Domates ürünleri', 'gida', 'salca', [r'^domates urun']),
    ('dondurma-kulahi', 'Dondurma külahı', 'gida', 'dondurma', [r'^dondurma kulah']),
    ('dondurulmus-sebze', 'Dondurulmuş sebze', 'gida', 'sebze', [r'^dondurulmus']),
    ('dondurma', 'Dondurma', 'gida', 'dondurma', [r'^dondurma', r'^glutensiz dondurma']),
    ('doner', 'Döner', 'gida', 'et', [r'^doner']),
    ('hamburger', 'Hamburger köftesi', 'gida', 'et', [r'^hamburger']),
    ('ekmek', 'Ekmek', 'gida', 'ekmek', [r'^ekmek']),
    ('lor', 'Lor', 'gida', 'sut', [r'^lor\b']),
    ('lokum', 'Lokum', 'gida', 'seker', [r'^lokum']),
    ('maca', 'Maca tozu', 'gida', 'un', [r'^maca\b']),
    ('makarna-sosu', 'Makarna sosu', 'gida', 'sos', [r'^makarna sos']),
    ('makarna', 'Makarna', 'gida', 'makarna', [r'^makarna', r'^kuskus', r'^noddle', r'^noodle']),
    ('manti', 'Mantı', 'gida', 'makarna', [r'^manti\b']),
    ('margarin', 'Margarin', 'gida', 'yag', [r'^margarin']),
    ('yogurt-mayasi', 'Yoğurt ve kefir mayası', 'gida', 'maya', [r'^yogurt ve kefir mayasi']),
    ('maya', 'Maya', 'gida', 'maya', [r'^maya\b']),
    ('mayonez', 'Mayonez', 'gida', 'sos', [r'^mayonez']),
    ('meyve-suyu', 'Meyve suyu', 'gida', 'icecek', [r'^meyve sulari', r'^meyve suyu']),
    ('aromali-sut', 'Meyve aromalı süt', 'gida', 'sut', [r'^meyve aromali sut']),
    ('bitkisel-icecek', 'Gazlı ve bitkisel içecekler', 'gida', 'icecek', [r'^gazli', r'^badem sutu']),
    ('maden-suyu', 'Maden suyu', 'gida', 'icecek', [r'^maden suyu']),
    ('misir-gevregi', 'Mısır gevreği', 'gida', 'atistirmalik', [r'^misir gevreg']),
    ('misir-nisastasi', 'Mısır nişastası', 'gida', 'un', [r'^misir nisasta']),
    ('misir-unu', 'Mısır unu', 'gida', 'un', [r'^misir unu']),
    ('hindistan-cevizi', 'Hindistan cevizi (un, yağ)', 'gida', 'un', [r'^hindistan ?cevizi']),
    ('irmik', 'İrmik (mısır irmiği)', 'gida', 'un', [r'^irmik']),
    ('jambon', 'Jambon, kavurma, füme et', 'gida', 'et', [r'^jambon', r'^kavurma']),
    ('kabartma-tozu', 'Kabartma tozu', 'gida', 'pasta-malz', [r'^kabartma']),
    ('kadayif', 'Kadayıf', 'gida', 'tatli', [r'^kadayif']),
    ('kahve', 'Kahve', 'gida', 'kahve', [r'^kahve', r'^granul kahve', r'^turk kahvesi', r'^nescafe$']),
    ('kinoa', 'Kinoa', 'gida', 'un', [r'^kinoa']),
    ('kakao', 'Kakao', 'gida', 'kahve', [r'^kakao']),
    ('karabugday', 'Karabuğday (greçka) ve unu', 'gida', 'un', [r'^karabugday']),
    ('karbonat', 'Karbonat', 'gida', 'pasta-malz', [r'^karbonat']),
    ('karton-bardak', 'Karton bardak', 'gida', 'diger', [r'^karton bardak']),
    ('kaymak', 'Kaymak', 'gida', 'sut', [r'^kaymak']),
    ('keciboynuzu', 'Keçiboynuzu (un, öz)', 'gida', 'un', [r'^keciboynuzu']),
    ('kefir', 'Kefir', 'gida', 'sut', [r'^kefir']),
    ('kestane-sekeri', 'Kestane şekeri', 'gida', 'seker', [r'^kestane sekeri']),
    ('kestane-unu', 'Kestane unu', 'gida', 'un', [r'^kestane unu']),
    ('kesme-seker', 'Kesme şeker', 'gida', 'seker2', [r'^kesme seker']),
    ('ketcap', 'Ketçap', 'gida', 'sos', [r'^ketcap']),
    ('kokorec', 'Kokoreç', 'gida', 'et', [r'^kokorec']),
    ('konserve', 'Konserve', 'gida', 'konserve', [r'konserve']),
    ('krem-santi', 'Krem şanti', 'gida', 'pasta-malz', [r'^krem santi']),
    ('krema', 'Krema', 'gida', 'sut', [r'^krema']),
    ('kuruyemis', 'Kuruyemiş ve çerez', 'gida', 'atistirmalik', [r'^kuruyemis']),
    ('labne', 'Labne', 'gida', 'sut', [r'^labne']),
    ('lavas', 'Lavaş ve tortilla', 'gida', 'ekmek', [r'^lavas', r'^tortilla']),
    ('limon-sosu', 'Limon sosu', 'gida', 'sos', [r'^limon sosu']),
    ('limonata', 'Limonata', 'gida', 'icecek', [r'^limonata']),
    ('eriste', 'Erişte', 'gida', 'makarna', [r'^eriste']),
    ('galeta-unu', 'Galeta unu', 'gida', 'un', [r'^galeta']),
    ('baklagil-unu', 'Nohut, mercimek, fasulye unu', 'gida', 'un',
     [r'^fasulye', r'^nohut unu', r'mercimek nohut unu']),
    ('un', 'Glutensiz un ve karışımlar', 'gida', 'un', [r'^glutensiz un', r'^unlar$']),
    ('gullac', 'Güllaç ve yufka', 'gida', 'gullac', [r'^gullac', r'^yufka']),
    ('hardal', 'Hardal', 'gida', 'sos', [r'^hardal']),
    ('corba', 'Hazır çorba', 'gida', 'corba', [r'^hazir corba']),
    ('helva', 'Helva', 'gida', 'seker', [r'^helva']),
    ('hindi', 'Hindi', 'gida', 'et', [r'^hindi\b']),
    ('nar-eksisi', 'Nar ekşisi', 'gida', 'sos', [r'^nar eksisi']),
    ('sos', 'Soslar (soya sosu dahil)', 'gida', 'sos',
     [r'^nar aromali sos', r'^soslar', r'^sos\b', r'^soya sosu', r'^soyali']),
    ('pasta-malzemesi', 'Pasta malzemeleri ve şeker hamuru', 'gida', 'pasta-malz',
     [r'^pasta susleme', r'^pasta malzeme']),
    ('pasta', 'Pasta ve yaş pasta', 'gida', 'tatli', [r'^pasta\b', r'^yas pasta', r'^profiterol']),
    ('pastirma', 'Pastırma', 'gida', 'et', [r'^pastirma']),
    ('patates-unu', 'Patates unu', 'gida', 'un', [r'^patates unu']),
    ('patlamis-misir', 'Patlamış mısır', 'gida', 'atistirmalik', [r'^patlamis misir']),
    ('pamuk-seker', 'Pamuk şeker', 'gida', 'seker', [r'^pamuk seker']),
    ('pekmez-tahin', 'Pekmez ve tahin', 'gida', 'pekmez', [r'^pekmez']),
    ('pestil', 'Pestil ve köme', 'gida', 'atistirmalik', [r'^pestil']),
    ('peynir', 'Peynir', 'gida', 'sut', [r'^peynir']),
    ('pismaniye', 'Pişmaniye', 'gida', 'seker', [r'^pismaniye']),
    ('pirinc-unu', 'Pirinç unu', 'gida', 'un', [r'^pirinc unu']),
    ('puding', 'Puding', 'gida', 'tatli', [r'^puding']),
    ('pudra-sekeri', 'Pudra şekeri', 'gida', 'seker2', [r'^pudra seker']),
    ('recel', 'Reçel', 'gida', 'recel', [r'^recel']),
    ('sakiz', 'Sakız', 'gida', 'seker', [r'^sakiz']),
    ('salam', 'Salam', 'gida', 'et', [r'^salam']),
    ('salca', 'Salça', 'gida', 'salca', [r'^salca']),
    ('salep', 'Salep', 'gida', 'icecek', [r'^salep']),
    ('sirke', 'Sirke', 'gida', 'sos', [r'^sirke']),
    ('sosis', 'Sosis', 'gida', 'et', [r'^sosis']),
    ('spirulina', 'Spirulina', 'gida', 'un', [r'^spirulina']),
    ('sucuk', 'Sucuk', 'gida', 'et', [r'^sucuk']),
    ('sutlu-tatli', 'Sütlü tatlılar', 'gida', 'tatli', [r'^sutlu tatli']),
    ('sut', 'Süt', 'gida', 'sut', [r'^sutler', r'^sut\b']),
    ('salgam', 'Şalgam suyu', 'gida', 'icecek', [r'^salgam']),
    ('sehriye', 'Şehriye', 'gida', 'makarna', [r'^sehriye']),
    ('sekerleme', 'Şekerleme', 'gida', 'seker', [r'^sekerleme']),
    ('tatli', 'Tatlı', 'gida', 'tatli', [r'^tatli\b']),
    ('tarhana', 'Tarhana', 'gida', 'corba', [r'^tarhana']),
    ('tavuk-harci', 'Tavuk ve köfte harcı', 'gida', 'et', [r'^tavuk ve kofte']),
    ('tavuk-suyu', 'Tavuk suyu', 'gida', 'corba', [r'^tavuk suyu']),
    ('tavuk', 'Tavuk', 'gida', 'et', [r'^tavuk']),
    ('teff', 'Teff', 'gida', 'un', [r'^teff']),
    ('tereyagi', 'Tereyağı', 'gida', 'sut', [r'^tereyag']),
    ('toz-seker', 'Toz şeker', 'gida', 'seker2', [r'^toz seker']),
    ('tursu', 'Turşu', 'gida', 'tursu', [r'^tursu']),
    ('vanilya', 'Vanilya', 'gida', 'pasta-malz', [r'^vanilya']),
    ('yogurt', 'Yoğurt', 'gida', 'sut', [r'^yogurt']),
    ('yulaf', 'Yulaf', 'gida', 'un', [r'^yulaf']),
    # kozmetik / bakım
    ('kozmetik-oku', 'Etiketi okunacak bakım markaları', 'kozmetik', 'etiket',
     [r'kisisel bakim ve temizlik']),
    ('sampuan', 'Şampuan, sabun ve kişisel bakım', 'kozmetik', 'kozmetik', [r'sampuan']),
    ('makyaj', 'Makyaj malzemeleri', 'kozmetik', 'kozmetik', [r'^makyaj']),
    ('dis-macunu', 'Diş macunu', 'kozmetik', 'kozmetik', [r'dis macun']),
    ('deodorant', 'Deodorant', 'kozmetik', 'kozmetik', [r'deodorant']),
    ('krem-gunes', 'Krem, losyon ve güneş koruyucu', 'kozmetik', 'kozmetik',
     [r'gunes koruyucu', r'kremleri', r'losyon']),
    # ilaç ve takviye
    ('ilac-firma', 'İlaç firmaları (tüm ürünleri)', 'ilac', 'ilac', []),
    ('ilac', 'İlaçlar', 'ilac', 'ilac', []),
    ('takviye', 'Tıbbi gıda ve takviyeler', 'takviye', 'takviye', []),
]
CAT = {c[0]: {'id': c[0], 'name': c[1], 'domain': c[2], 'family': c[3]} for c in CATS}
_CAT_RX = [(c[0], c[2], [re.compile(p) for p in c[4]]) for c in CATS]

# Kategori adlarındaki kelimeler (ürün tarifinden çıkarılır)
CAT_WORDS = {
    'ayran': 'ayran ayrani', 'bal': 'bal bali', 'baharat': 'baharat baharatlar baharati',
    'sicak-cikolata': 'sicak', 'damla-cikolata': 'damla', 'cikolata-sosu': 'sos sosu', 'balik': 'balik ton', 'boza': 'boza bozasi',
    'cikolata': 'cikolata cikolatalar chocolate chocolat cikolatasi', 'cips': 'cips cipsi chips',
    'dondurma': 'dondurma dondurmasi dondurmalari', 'ekmek': 'ekmek ekmegi ekmekleri ekmekler',
    'lor': 'lor loru', 'lokum': 'lokum lokumu lokumlari', 'makarna': 'makarna makarnasi makarnalari',
    'margarin': 'margarin', 'maya': 'maya mayasi', 'mayonez': 'mayonez', 'kefir': 'kefir',
    'kaymak': 'kaymak kaymagi', 'krema': 'krema', 'labne': 'labne', 'peynir': 'peynir peyniri peynirleri',
    'sut': 'sut sutu sutleri', 'yogurt': 'yogurt yogurdu yogurtlari', 'tereyagi': 'tereyagi tereyag',
    'salca': 'salca salcasi', 'ketcap': 'ketcap', 'hardal': 'hardal', 'sirke': 'sirke sirkesi',
    'sucuk': 'sucuk sucugu', 'sosis': 'sosis', 'salam': 'salam salami', 'helva': 'helva helvasi helvalari',
    'recel': 'recel receli recelleri marmelat', 'tarhana': 'tarhana', 'sehriye': 'sehriye sehriyesi',
    'eriste': 'eriste', 'un': 'un unu unlari', 'kakao': 'kakao', 'kahve': 'kahve kahvesi kahveleri',
    'sakiz': 'sakiz sakizi', 'sekerleme': 'sekerleme seker sekerleri', 'puding': 'puding pudingi',
    'tursu': 'tursu tursulari', 'konserve': 'konserve konservesi konserveleri', 'boza2': '',
    'sarap': 'sarap sarabi saraplari', 'alkollu': 'bira', 'irmik': 'irmik irmigi',
    'bulgur': 'bulgur bulguru', 'misir-unu': 'misir unu', 'pirinc-unu': 'pirinc unu',
    'misir-nisastasi': 'misir nisastasi', 'kabartma-tozu': 'kabartma tozu', 'vanilya': 'vanilya',
    'krem-santi': 'krem santi', 'kestane-unu': 'kestane unu', 'patates-unu': 'patates unu',
    'galeta-unu': 'galeta unu', 'tavuk': 'tavuk', 'doner': 'doner', 'pastirma': 'pastirma',
    'salep': 'salep', 'meyve-suyu': 'meyve suyu sulari', 'limonata': 'limonata',
    'salgam': 'salgam suyu', 'nar-eksisi': 'nar eksisi', 'pekmez-tahin': 'pekmez tahin',
    'gullac': 'gullac', 'kadayif': 'kadayif', 'manti': 'manti', 'corba': 'corba corbalari',
    'kuruyemis': 'kuruyemis', 'misir-gevregi': 'misir gevregi', 'dis-macunu': 'dis macunu macunlari',
    'deodorant': 'deodorant', 'sampuan': 'sampuan sampuanlari', 'atistirmalik': 'atistirmalik atistirmaliklar',
    'karabugday': 'karabugday unu', 'keciboynuzu': 'keciboynuzu unu', 'hindistan-cevizi': 'hindistan cevizi',
    'jambon': 'jambon', 'pasta': 'pasta', 'sutlu-tatli': 'sutlu tatli tatlilari', 'pestil': 'pestil pestili kome',
}

GENERIC_WORDS = set('''
ve ile veya ya da de tum butun her hepsi hepsini tumu urun urunu urunleri urunler urunlerinin urunlerin
cesit cesitleri cesitler cesidi cesitlerimiz tur turleri turlu aroma aromalar aromalari aromali
glutensiz gluten free glutenfree organik dogal marka markali markalari markasi serbest serbesttir
firma firmasi firmanin www com tr net http https adet gr g kg ml lt l pcs paket kutu
tatlilar atistirmaliklar
'''.split())

CAUTION_RX = re.compile(
    r'\b(haric|disinda|disindaki|dikkat|okuyun|okuyunuz|okunmali|okunmalidir|okuyarak|okunarak|'
    r'etiket\w*|ibare\w*|yazan|yazanlar|yazili|sadece|icerebilir|glutenli|sorgula\w*|kosul\w*|'
    r'sartiyla|uyari\w*|logosu|amblem\w*)\b')
WARN_RX = re.compile(
    r'\b(gluten icer(?:ir|iyor|mektedir|ebilir)|glutenli|almayiniz|almamaliyiz|kullanmayiniz|'
    r'tuketmeyiniz|tuketilmemeli\w*|kullanilmamali\w*|yememeliyiz|tuketmemelerini|yasak|yasaktir)\b')

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


# ---------------------------------------------------------------- HTML ----
_BLOCK = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'blockquote', 'pre'}
_SHORTCODE = re.compile(r'\[/?vc_[^\]]*\]')


def html_rows(html):
    """Sayfa içeriğini satırlara çevir: [{'text', 'tag', 'bold'}]"""
    html = _SHORTCODE.sub('', html or '')
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.I)
    soup = BeautifulSoup(html, 'lxml')
    rows = []
    for el in soup.find_all(True):
        if el.name not in _BLOCK:
            continue
        if any(c.name in _BLOCK for c in el.find_all(True)):
            # içinde blok varsa: yalnızca doğrudan metin parçalarını al
            direct = ''.join(str(c) for c in el.children if getattr(c, 'name', None) not in _BLOCK)
            if not clean(BeautifulSoup(direct, 'lxml').get_text()):
                continue
            frag_soup = BeautifulSoup(direct, 'lxml')
        else:
            frag_soup = el
        full = frag_soup.get_text()
        strong = ''.join(s.get_text() for s in frag_soup.find_all(['strong', 'b']))
        letters = len(re.sub(r'\s', '', full)) or 1
        bold = min(1.0, len(re.sub(r'\s', '', strong)) / letters)
        for line in full.split('\n'):
            line = clean(line)
            if line:
                rows.append({'text': line, 'tag': el.name, 'bold': round(bold, 2)})
    return rows


# --------------------------------------------------------- yardımcılar ----
def canon_cat(text, domain=None):
    n = norm(text)
    n = re.sub(r'^[\s:–\-]+', '', n)
    for cid, dom, rxs in _CAT_RX:
        if domain and dom != domain:
            continue
        for rx in rxs:
            if rx.search(n):
                return cid
    return None


def canon_cat_strict(text, domain=None):
    """Satırın BAŞINDA kategori adı varsa kategori (paragraf içi ara başlıklar ve kalın satırlar için)."""
    n = norm(text)
    n = re.sub(r'^[\s:–\-]+', '', n)
    for cid, dom, rxs in _CAT_RX:
        if domain and dom != domain:
            continue
        for rx in rxs:
            if rx.match(n):
                return cid
    return None


def is_upperish(s):
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    up = sum(1 for c in letters if c.isupper())
    return up / len(letters) >= 0.7


NOTE_START = re.compile(
    r'^(not|notu|onemli|lutfen|dikkat bazi|bu firma\w*|firma\w*|asagida|uyari|ornegin|yukaridaki|'
    r've yukarida|gercek cikolata|cikolata urunlerinde|bizim fabrikamizda|urunlerimizi|gibi|butun|'
    r'genellikle|dokme|cekirdek halde|dondurulmus sossuz|konservelerin|acikta satilan|toz seker\w*|'
    r'press yontemiyle|satis noktalari|kent gida firmasi|kent seker urunleri|'
    r'nestle firmasinin ayrica|kent modelez firmasinin|bunlar da|okulda|tum markalar|bazi|'
    r'otel ekipmanlari|yukarida|sevgili|bir baska|uretici firmalar|derneğimize|dernegimize)\b')

ALL_FREE_RX = re.compile(r'\b(serbest\w*|kullanilabilir|kullanmasi uygundur|kullanilmasi uygundur)\b')
INVENTORY = {}
BY_ID = {}
ILAC_BRANDS = set()
DESC_NOISE = set('''mevcuttur mevcut belirtilmektedir belirtilmekted belirtilmistir oldugu olan olanlar urunlerin
uzerinde ambalaj ambalaji ambalajinda urunambalaji ibaresi ibare ibaresimevcuttur yazmaktadir yazilidir yazmali
vardir bulunur bulunmaktadir satilmaktadir ir dir tir icermez icermiyor icermemektedir bilgisi
harfinde nazar boncugu boncuk resmi olmak uzere iki uc urunu diger lar ler urettigi uretilen
adana adiyaman afyon amasya antalya artvin aydin balikesir bilecik bingol bitlis burdur bursa canakkale
cankiri corum denizli diyarbakir edirne elazig erzincan erzurum eskisehir gaziantep giresun hatay isparta
mersin istanbul izmir kastamonu kayseri kirklareli kirsehir kocaeli konya kutahya malatya manisa
kahramanmaras mardin mugla nevsehir sakarya samsun sinop sivas tekirdag tokat trabzon sanliurfa usak
yozgat zonguldak aksaray karaman kirikkale yalova karabuk duzce
etiketi kapali plastik kutuda kutu paketli ambalajli yazacak yazmali yazmalidir yazanlar'''.split())


def make_line(src, domain, cat, text, heading, ctx_brand=None, kind=None, order=0, force_ctx=False):
    return {'src': src, 'domain': domain, 'cat': cat, 'text': text, 'h': heading,
            'ctx': ctx_brand, 'kind': kind, 'o': order, 'force_ctx': force_ctx}


_CAMEL = re.compile(r'([a-zçğıöşü])([A-ZÇĞİÖŞÜ])(?=[a-zçğıöşü])')


def camel_split(t):
    """'LiptonÇayları CalveÇorbaları' gibi bitişik yazılmış satırları aç (en az 3 bitişik kelime varsa)."""
    if len(_CAMEL.findall(t)) >= 3:
        return _CAMEL.sub(r'\1 \2', t)
    return t


_ADDR = re.compile(r'\b(cad|sok|mah|bulvar|bulvari|no)\b.*\d|\d.*\b(cad|sok|mah)\b')


def merge_continuations(lines):
    """Bir önceki satırın devamı olan satırları birleştir: '(Hindi Füme Eti, ...)', 'sosu, yaprak sarma.'"""
    out = []
    for ln in lines:
        t = ln['text']
        n = norm(t)
        prev = out[-1] if out else None
        can = prev is not None and prev['src'] == ln['src'] and prev['cat'] == ln['cat'] and \
            prev['kind'] in (None, 'ok', 'read') and ln['kind'] in (None, 'ok', 'read')
        cont = False
        if can and not NOTE_START.match(n) and not ALL_FREE_RX.search(n):
            unfinished = prev['text'].count('(') > prev['text'].count(')') or prev['text'].rstrip().endswith((',', '-', '–'))
            if t.startswith('(') and len(n.split()) <= 25:
                cont = True
            elif unfinished and t[:1].islower() and len(n.split()) <= 25:
                cont = True
            elif _ADDR.search(n) and len(n.split()) <= 12 and detect_brand(n)[0] in (None,) + tuple(
                    n.split()[:1]) and re.search(r'\b(cad|sok|mah)\b', n):
                cont = True
        if cont:
            prev['text'] = clean(prev['text'] + ' ' + t)
            continue
        out.append(ln)
    return out


# ---------------------------------------------------- İstanbul: gıda ----
IST_BRAND_HEADINGS = {
    'starbucks': ('Starbucks', None), 'nestle nespresso': ('Nespresso', None),
    'tukas konserveler': ('Tukaş', 'konserve'), 'peyman bahceden': ('Peyman Bahçeden', None),
    'peyman dorleo': ('Peyman Dorleo', None), 'peyman citliyo': ('Peyman Çitliyo', None),
    'saray muhallebicisi': ('Saray Muhallebicisi', None),
    'saray muhallebicisi subeleri': ('Saray Muhallebicisi', None, 'info'),
}
IST_SKIP_HEADINGS = {'dikkat onemli', '', 'kolay menu'}


def inline_subheading(line, domain):
    """Paragraf içindeki ara başlıklar: 'PROFİTEROL :', 'YOGURT', 'HiNDi : (...)'"""
    n = norm(line)
    words = n.split()
    if not words or len(words) > 8:
        return None
    looks = line.rstrip().endswith(':') or re.search(r'\s:\s*\(', line) or is_upperish(line) or \
        (len(words) <= 3 and detect_brand(n)[0] is None) or n in ('raki votka cin',)
    if not looks:
        return None
    cid = canon_cat_strict(line, domain)
    if cid:
        return cid
    return None


def parse_ist_gida(page):
    rows = html_rows(page['content']['rendered'])
    lines, cat, heading, ctx, section = [], None, '', None, 'ok'
    force = False
    for i, r in enumerate(rows):
        t = r['text']
        n = norm(t)
        if r['tag'] in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            nn = re.sub(r'\s+', ' ', n.replace(':', ' ')).strip()
            if nn in IST_SKIP_HEADINGS or not nn:
                section = 'skip' if nn == 'dikkat onemli' else section
                continue
            heading = t
            force = False
            if nn.startswith('mabel firmasinin aciklamasi'):
                section, ctx = 'warn', compact('Mabel')
                continue
            cid = canon_cat(t, 'gida')
            if cid == 'etiket-oku':
                cat, section = 'etiket-oku', 'read'
                ctx = None
                for k, b in (('unilever', 'unilever'), ('kent', 'mondelezkent'), ('nestle', 'nestle')):
                    if k in nn:
                        ctx = b
                continue
            bh = IST_BRAND_HEADINGS.get(nn)
            if bh:
                ctx = compact(bh[0])
                if bh[1]:
                    cat = bh[1]
                force = len(bh) > 2 and bool(bh[2])
                section = 'info' if (len(bh) > 2 and bh[2] == 'info') else 'ok'
                continue
            if cid:
                cat, ctx, section = cid, None, 'ok'
            else:
                # tanınmayan başlık: marka başlığı say
                ctx, section = detect_brand(n)[0], 'ok'
            continue
        if section == 'skip' or cat is None:
            continue
        t2 = re.sub(r'^[·•\-–]\s*', '', t).strip()
        if not t2:
            continue
        sub = inline_subheading(t2, 'gida')
        if sub and section != 'read':
            cat, heading, ctx = sub, t2, None
            continue
        kind = None
        n2 = norm(t2)
        if section == 'warn':
            kind = 'warn' if re.search(r'kodlu|cesit numarasi', n2) else 'note'
        elif section == 'read':
            kind = 'note' if (len(n2.split()) > 8 or NOTE_START.match(n2)) else 'read'
        elif section == 'info':
            kind = 'info'
        lines.append(make_line('ist', 'gida', cat, t2, heading, ctx, kind, i, force))
    return merge_continuations(lines)


def parse_ist_simple(page, domain, default_cat):
    rows = html_rows(page['content']['rendered'])
    lines, cat, heading, ctx, section = [], default_cat, '', None, 'ok'
    started = domain == 'kozmetik'
    for i, r in enumerate(rows):
        t = r['text']
        n = norm(t)
        if r['tag'] in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            nn = n.replace(':', ' ').strip()
            if nn in IST_SKIP_HEADINGS:
                started = False
                continue
            heading = t
            started = True
            if domain == 'kozmetik':
                cid = canon_cat(t, 'kozmetik')
                if cid:
                    cat = cid
                    section = 'read' if cid == 'kozmetik-oku' else 'ok'
            continue
        if not started:
            if domain == 'takviye' and n.startswith('glutensiz tibbi gida destekleri'):
                started, heading = True, t
            continue
        if domain == 'kozmetik':
            cid = canon_cat(t, 'kozmetik') if (r['bold'] > 0.6 or t.rstrip().endswith(':')) else None
            if cid:
                cat, heading = cid, t
                section = 'read' if cid == 'kozmetik-oku' else 'ok'
                continue
            if r['bold'] > 0.6 and len(n.split()) > 4:
                lines.append(make_line('ist', domain, cat, t, heading, None, 'note', i))
                continue
            lines.append(make_line('ist', domain, cat, t, heading, None, 'read' if section == 'read' else None, i))
            continue
        if domain == 'ilac':
            if n.startswith('onemli not') or n.startswith('glutensiz ilaclar'):
                if n.startswith('onemli not'):
                    lines.append(make_line('ist', domain, 'ilac', t, 'Glutensiz İlaçlar', None, 'note', i))
                continue
            cat_i = 'ilac-firma' if is_company_statement(n) else 'ilac'
            lines.append(make_line('ist', domain, cat_i, t, 'Glutensiz İlaçlar', None, None, i))
            continue
        # takviye
        if n.startswith('glutensiz tibbi gida destekleri'):
            heading = t
            continue
        m = re.match(r'^([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü\- ]{1,30}):\s*$', t)
        if m and is_upperish(m.group(1)):
            ctx = compact(m.group(1))
            heading = t
            continue
        lines.append(make_line('ist', domain, 'takviye', t, heading or 'Tıbbi Gıda Destekleri', ctx, None, i))
    if domain == 'ilac':
        lines = merge_ilac_company_rows(lines)
    else:
        merged = []
        for ln in lines:
            if merged and re.match(r'^ve\s', ln['text']) and len(ln['text'].split()) <= 6 and \
                    not merged[-1]['text'].rstrip().endswith('.'):
                merged[-1]['text'] = clean(merged[-1]['text'] + ' ' + ln['text'])
                continue
            merged.append(ln)
        lines = merged
    return lines


def is_company_statement(n):
    return bool(re.search(r'\bfirma\w*\b', n) and re.search(
        r'glutensiz|gluten icermemektedir|icermemektedir|tum ilaclari|hicbir urunu', n))


def merge_ilac_company_rows(lines):
    """'ADEKA' + ': Firmanın tüm ilaçları glutensizdir.' satırlarını birleştir, firma kategorisine al."""
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        t = ln['text']
        nxt = lines[i + 1]['text'] if i + 1 < len(lines) else ''
        cont = re.match(r'^\s*[:I]?\s*:', nxt) or re.match(r'^(firma|firmanin|firmasinin)\b', norm(nxt))
        if is_upperish(t) and len(t) < 45 and nxt and cont and not re.search(r'\d', t):
            merged = clean(t + ' ' + nxt)
            merged = re.sub(r'\s+:', ':', merged)
            nl = dict(ln, text=merged, cat='ilac-firma')
            out.append(nl)
            i += 2
            continue
        out.append(ln)
        i += 1
    return out


# ------------------------------------------------------------- Ankara ----
ANK_GROUP_BRANDS = {compact('Peyman Bahçeden'), compact('Peyman Dorleo'), compact('Peyman Çitliyo')}
ANK_BRAND_HEADINGS = {
    'bolulu hasan usta': 'Bolulu Hasan Usta', 'mado': 'Mado', 'saray muhallebicisi': 'Saray Muhallebicisi',
    'ikea': 'İKEA', 'nescafe': None,
}


def parse_ank(page):
    rows = html_rows(page['content']['rendered'])
    lines, extras = [], {'mekan': [], 'otel': [], 'universite': []}
    section, domain, cat, heading, ctx = 'intro', 'gida', None, '', None
    cur_venue = None
    for i, r in enumerate(rows):
        t = camel_split(r['text'])
        n = norm(t)
        if not n or re.fullmatch(r'[*\-—–_x ]+', n) or re.fullmatch(r'[*\-—–_xX ]+', t):
            continue
        bold = r['bold'] > 0.6
        semibold = r['bold'] >= 0.3
        nz = n.replace(' ', '')
        # ---- bölüm sınırları
        if section == 'intro' and n.startswith('atistirmalik'):
            section, domain, cat, heading, ctx = 'food', 'gida', 'atistirmalik', t, None
            continue
        if section == 'intro':
            continue
        if n.startswith('okunarak alinmasi gereken'):
            section, domain, cat, heading, ctx = 'read', 'gida', 'etiket-oku', t, None
            continue
        if n.startswith('bazi colyaklilara ciltte'):
            section, domain, cat, heading, ctx = 'kozmetik', 'kozmetik', 'sampuan', t, None
            lines.append(make_line('ank', 'kozmetik', 'sampuan', t, t, None, 'note', i))
            continue
        if n.startswith('ambalaj uzerinde allerjen uyarisi'):
            section, domain, cat, heading, ctx = 'read', 'gida', 'etiket-oku', t, None
            continue
        if n.startswith('glutensiz urun hizmeti veren isletmeler'):
            section = 'mekan'
            continue
        if n.startswith('ilaclar'):
            section, domain, cat, heading, ctx = 'ilac', 'ilac', 'ilac-firma', 'Glutensiz İlaçlar', None
            rest = re.sub(r'^\s*İ\s*L\s*A\s*Ç\s*L\s*A\s*R\s*', '', t)
            for part in split_company_statements(rest):
                lines.append(make_line('ank', 'ilac', 'ilac-firma', part, heading, None, None, i))
            continue
        if n == 'glutensiz' and section in ('mekan', 'read', 'kozmetik', 'food'):
            continue
        if n.startswith('glutensiz tibbi gida destekleri'):
            section, domain, cat, heading, ctx = 'takviye', 'takviye', 'takviye', t, None
            continue
        if nz.startswith('glutensizoteller'):
            section = 'otel'
            continue
        if n.startswith('glutensiz menusu olan universiteler'):
            section = 'universite'
            continue

        # ---- bölüm içerikleri
        if section == 'mekan':
            if n in ('ankara',):
                continue
            head2 = ' '.join(re.split(r'\s*-\s*Sadece|\(', t)[0].split()[:3])
            is_detail = (not bold) or n.startswith('tel') or re.match(r'^[\d(]', n) or \
                re.search(r'\b(cad|sok|mah|no|bulvar|avm|sube|www)\b', norm(head2)) or not is_upperish(head2)
            if bold and not is_detail:
                cur_venue = {'name': t, 'details': []}
                extras['mekan'].append(cur_venue)
            elif cur_venue:
                cur_venue['details'].append(t)
            continue
        if section == 'otel':
            if n.startswith('otel ekipmanlari'):
                extras['otel_note'] = t
                continue
            if bold and is_upperish(t) and not n.startswith('tel'):
                cur_venue = {'name': t, 'details': []}
                extras['otel'].append(cur_venue)
            elif cur_venue:
                cur_venue['details'].append(t)
            continue
        if section == 'universite':
            extras['universite'].append(t)
            continue
        if section == 'ilac':
            if re.match(r'^[A-ZÇĞİÖŞÜ .\-]+(?:İLAÇ|FARMA|FİRMASI)?\s*:', t) and \
                    re.search(r'firma|ilac', n) and len(t) < 260 and not canon_ilac_heading(t):
                for part in split_company_statements(t):
                    lines.append(make_line('ank', 'ilac', 'ilac-firma', part, heading, None, None, i))
                continue
            th = canon_ilac_heading(t)
            if th:
                label, rest = th
                heading = label
                if rest:
                    for item in split_drug_list(rest):
                        lines.append(make_line('ank', 'ilac', 'ilac', item, label, None, None, i))
                continue
            for item in split_drug_list(t):
                lines.append(make_line('ank', 'ilac', 'ilac', item, heading, None, None, i))
            continue
        if section == 'takviye':
            lines.append(make_line('ank', 'takviye', 'takviye', t, heading, None, None, i))
            continue
        if section == 'kozmetik':
            cid = canon_cat(t, 'kozmetik') if bold else None
            if cid:
                cat, heading, ctx = cid, t, None
                continue
            lines.append(make_line('ank', 'kozmetik', cat, t, heading, None, None, i))
            continue
        if section == 'read':
            if bold:
                cid = canon_cat(t, 'gida')
                nn = n
                if cid == 'etiket-oku':
                    heading = t
                    ctx = 'unilever' if 'unilever' in nn else ('mondelezkent' if 'kent' in nn else (
                        'nestle' if 'nestle' in nn else ctx))
                    continue
            kind = 'read'
            if WARN_RX.search(n) and n.startswith('dikkat'):
                kind = 'warn'
            elif NOTE_START.match(n) or (len(n.split()) > 22 and camel_split(r['text']) == r['text']):
                kind = 'note'
            force_c = bool(ctx) and camel_split(r['text']) != r['text']
            lines.append(make_line('ank', 'gida', 'etiket-oku', t, heading, ctx, kind, i, force_c))
            continue
        # ---- gıda
        if bold and len(nz) <= 2:
            continue  # alfabe ayırıcı: B, C-Ç, S- Ş
        nn = n.replace(':', ' ').strip()
        if bold and nn in ANK_BRAND_HEADINGS:
            b = ANK_BRAND_HEADINGS[nn]
            if b:
                ctx, heading = compact(b), t
            else:
                heading = t
            continue
        head_part = re.split(r'[(\-–]', t)[0]
        short_head = len(norm(head_part).split()) <= 7 or ':' in head_part
        if ':' not in t[:40] and t.rstrip().endswith(('.', '…', '!')) and len(norm(t).split()) >= 3:
            short_head = False   # cümle: başlık değil, not satırı ("YOĞURT : (...)." gibi başlıklar hariç)
        if short_head and (bold or semibold or (is_upperish(head_part) and len(norm(head_part).split()) <= 6)):
            cid = canon_cat_strict(t, 'gida')
            if cid and cid != 'etiket-oku' and (bold or semibold or head_part.rstrip().endswith(':')
                                                 or len(norm(head_part).split()) <= 3):
                cat, ctx = cid, None
                heading = t
                # başlıktaki koşul/açıklama: parantez içi
                m = re.search(r'\((.+)', t)
                if m:
                    lines.append(make_line('ank', 'gida', cat, clean(m.group(1).rstrip(')')), t, None, 'note', i))
                continue
        # marka grubu satırı: "Peyman Bahçeden" ardından ürünler
        key_g, k_g = find_alias(n.split(), 0)
        if key_g in ANK_GROUP_BRANDS and k_g == len(n.split()):
            ctx = key_g
            continue
        if key_g in ANK_GROUP_BRANDS:
            ctx = key_g
        lines.append(make_line('ank', 'gida', cat, t, heading, ctx, None, i))
    return merge_continuations(lines), extras


ILAC_HEADINGS = ['ANALJEZİK', 'ÜST-ALT SOLUNUM', 'ANTİHİSTAMİNİK', 'DAHİLİYE', 'TANSİYON', 'KALP DAMAR',
                 'KANSIZLIK', 'VİT. D3', 'ENDOKRİNOLOJİ', 'DERMOTOLOJİ', 'GÖZ', 'DİABET', 'JİNEKOLOJİ', 'ASTIM',
                 'PSİKOLOJİK', 'EPİLEPSİ', 'ORAL VE DİŞETİ', 'ALZHEİMER', 'PARKİNSON', 'KANSER', 'ANESTEZİ',
                 'ÇEŞİTLİ İLAÇLAR']


def canon_ilac_heading(t):
    for h in ILAC_HEADINGS:
        if t.upper().startswith(h) or t.startswith(h):
            m = re.match(r'^([^:]+):?\s*(.*)$', t)
            label, rest = clean(m.group(1)), clean(m.group(2))
            if rest and ':' not in t:
                # "TANSİYON Hyzaar, ..." biçimi
                parts = t.split(' ', 1)
                label, rest = parts[0], parts[1] if len(parts) > 1 else ''
            return label.title(), rest
    return None


def split_drug_list(t):
    if t.count(',') >= 2:
        return [clean(x) for x in re.split(r'[,;]', t) if clean(x) and len(clean(x)) > 1]
    return [t]


def split_company_statements(t):
    """'BİLİM İLAÇ : ... PFİZER : ...' -> ayrı ifadeler"""
    t = clean(t)
    parts = re.split(r'(?<=[.…])\s+(?=[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ .\-]{2,}\s*:)', t)
    return [clean(p) for p in parts if clean(p)]


# ------------------------------------------------------- zenginleştirme ----
def classify(ln):
    n = norm(ln['text'])
    ln['n'] = n
    caution = bool(CAUTION_RX.search(n)) or bool(WARN_RX.search(n))
    ln['caution'] = caution
    if ln['kind'] in ('warn', 'note', 'read', 'info'):
        return
    if re.search(r'\bkodlu\b.*\bkodlu\b|cesit numarasi|icin uyaridir', n):
        ln['kind'] = 'warn'
        return
    if re.search(r'firmasinin aciklamasi', n):
        ln['kind'] = 'note'
        return
    if ln['domain'] == 'ilac':
        ln['kind'] = 'ok'
        return
    if n.startswith('dikkat') and WARN_RX.search(n) and not re.search(r'\bglutensiz\b', n.split('icer')[0]):
        ln['kind'] = 'warn'
        return
    if NOTE_START.match(n):
        ln['kind'] = 'note'
        return
    ln['kind'] = 'ok'


def assign_brand(ln):
    if ln['domain'] == 'ilac':
        if ln['cat'] == 'ilac-firma':
            name = re.split(r'\s*:|\s+[Ff]irma', ln['text'])[0]
            name = re.sub(r'(?i)\b(i̇laç|ilaç|ilac|iLAÇ|firması|firmasi|firmas|firmasının)\b', '', name)
            key, span = detect_brand(norm(name))
            ln['brand'] = key or compact(name)
            ln['span'] = None
        else:
            toks = ln['n'].split()
            ln['brand'] = toks[0] if toks else None
            ln['span'] = (0, 1) if toks else None
        return
    if ln['kind'] == 'note':
        ln['brand'], ln['span'] = None, None
        return
    key, span = detect_brand(ln['n'])
    ctx = ln.get('ctx')
    if ctx and ln.get('force_ctx'):
        key, span = ctx, None
    elif ctx and not key:
        key, span = ctx, None
    elif ctx and key and key != ctx:
        # bağlam markası altındaki ürün satırı mı? (örn. Mado > "Muhterika")
        # Satırın kendi markası iki listede de / birden çok satırda geçiyorsa kendi markasıdır.
        known = key in BRAND_NAME or INVENTORY.get(key, 0) >= 2 or ln['kind'] in ('read', 'warn')
        if not known:
            key, span = ctx, None
    ln['brand'], ln['span'] = key, span
    if key is None and ln['kind'] == 'ok':
        # markasız ürün satırı: not say
        if len(ln['n'].split()) > 6 or ALL_FREE_RX.search(ln['n']):
            ln['kind'] = 'note'


def family_words(cat):
    fam = CAT[cat]['family'] if cat in CAT else cat
    words = set()
    for cid, c in CAT.items():
        if c['family'] == fam:
            words.update(CAT_WORDS.get(cid, '').split())
    return words


def family_words(cat):
    fam = CAT[cat]['family'] if cat in CAT else cat
    words = set()
    for cid, c in CAT.items():
        if c['family'] == fam:
            words.update(CAT_WORDS.get(cid, '').split())
    return words


_DESC_SKIP = set('''haric disinda disindaki olmayan olmayanlar okuyarak okunarak okuyun okuyunuz etiketine edin
edilsin dikkat lutfen uzerini uzeri var satilan bulunuyor satiliyor de da lerde larda migroslarda carrefour a101
bim expreslerde sadece yazan yazili bunyesinde subelerinde cafede cafe kafe ilkerim ankara'''.split())


def strip_urls(n):
    """normalize metinden web adreslerini çıkar: "www kaleshop com tr" """
    n = re.sub(r'\bwww [a-z0-9]+( [a-z0-9]+){0,3}', ' ', n)
    n = re.sub(r'\b[a-z0-9]+ (com|net|org)( tr)?\b', ' ', n)
    return re.sub(r'\s+', ' ', n).strip()


# Adı birden çok ürün biçimi sayan kategoriler: bu biçim kelimeleri ürünü ayırt eder
# ("Keçiboynuzu Unu" yalnız unu onaylar, özünü değil)
MULTI_FORM = {
    'keciboynuzu': {'un', 'unu', 'oz', 'ozu'},
    'hindistan-cevizi': {'un', 'unu', 'yag', 'yagi'},
    'karabugday': {'un', 'unu'},
}

def desc_tokens(n, cat, brand, strip_cat=True):
    cw = (family_words(cat) - MULTI_FORM.get(cat, set())) if strip_cat else set()
    if brand:
        cw.update(norm(BRAND_NAME.get(brand, '')).split())
        cw.add(brand)
    n = strip_urls(n)
    bwords = [w for w in cw if len(w) >= 4]
    out = []
    for t in n.split():
        if t in GENERIC_WORDS or t in cw or re.match(r'^\d', t) or len(t) < 2:
            continue
        if brand and any(t.startswith(w) and len(t) - len(w) <= 3 for w in bwords if w in
                         norm(BRAND_NAME.get(brand, '')).split() + [brand]):
            continue
        if t in DESC_NOISE or t in _DESC_SKIP or CAUTION_RX.fullmatch(t):
            continue
        out.append(stem(t))
    return out


def descriptor(ln, strip_cat=True):
    toks = ln['n'].split()
    if ln.get('span'):
        a, b = ln['span']
        toks = toks[:a] + toks[b:]
    return desc_tokens(' '.join(toks), ln['cat'], ln['brand'], strip_cat)


def elements(ln, strip_cat=True):
    """Liste biçimli satırları ürünlere böl: virgül, 've', tire ve tekrar eden marka adı."""
    t = ln['text']
    seps = len(re.findall(r'[,;]|\s[–-]\s|–|\s(?:ve|ile)\s', t, flags=re.I))
    bname = norm(BRAND_NAME.get(ln['brand'], '')) or ln['brand'] or ''
    nb = len(re.findall(r'\b' + re.escape(bname) + r'\b', ln['n'])) if bname else 0
    if seps < 1 and nb < 2:
        return []
    parts = re.split(r'\s*(?:[,;(]|\)|\s[–-]\s|–|\s(?:ve|ile)\s)\s*', t, flags=re.I)
    out = []
    for prt in parts:
        pn = norm(prt)
        if bname and nb >= 2:
            sub = [x for x in re.split(r'\b' + re.escape(bname) + r'\b', pn) if x.strip()]
        else:
            sub = [pn]
        for x in sub:
            d = desc_tokens(x, ln['cat'], ln['brand'], strip_cat)
            if d:
                out.append(d)
    return out if len(out) >= 2 else []


EXCL_RX = re.compile(r'\b(haric|disinda|disindaki|disindakiler|olmayan|olmayanlar|olmamasi)\b')


def is_generic(ln, desc):
    if not desc:
        return True
    n = ln['n']
    if re.search(r'\b(tum|butun|hepsi|tumu)\b', n) and len(desc) <= 2:
        return True
    if re.search(r'\bhepsi serbest|\btumu serbest|\bhepsi glutensiz|\btum cesit(leri)? ve aroma', n):
        return True
    if re.search(r'\btatli ve tuzlu\b', n) and len(desc) <= 4:
        return True
    if EXCL_RX.search(n) and len(desc) <= 6:
        return True   # "X (karışımlar hariç)": hariç tutulanlar dışında tüm ürünler
    return False


def tok_eq(a, b):
    if a == b:
        return True
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) >= 4 and long_.startswith(short) and len(long_) - len(short) <= 2:
        return True
    if len(a) >= 5 and len(b) >= 5:
        return difflib.SequenceMatcher(None, a, b).ratio() >= 0.85
    return False


FLAVOR = set(stem(w) for w in '''
sade sutlu sut bitter beyaz kakao kakaolu cilek cilekli portakal portakalli limon limonlu nane naneli visne vis
muz muzlu karamel karamelli vanilya vanilyali vanilin findik findikli fistik fistikli antep badem bademli ceviz
cevizli hindistancevizi hindistan kestane kestaneli kinoa kinoali karabugday karabugdayli pirinc misir nohut
mercimek fasulye chia teff yulaf amarant keciboynuzu hurma incir erik kayisi uzum bogurtlen ahududu frambuaz
yaban mersin mersinli kizilcik nar elma elmali armut seftali mango ananas papaya kavun karpuz karadut dut kiraz
cranberry goji gojiberry tarcin tarcinli zencefil zencefilli zerdecal zerdecalli kekik zeytin zeytinli peynir
peynirli sogan soganli sarimsak domates domatesli biber biberli aci acili tuzlu tuzsuz sekersiz seker sekerli
bal balli stevia light laktozsuz laktozlu susam susamli hashas keten corek barbeku sirke ketcap spicy avokado
yogurt mevsim yesillik dereotu dereotlu ispanak ispanakli pizza hardal kahve kahveli cappuccino espresso tiramisu
dolgulu kirmizi sari yesil siyah kara esmer basmati deniz kaya orman meyve meyveli vegan prebiyotik protein keci
inek manda koyun tam yagli yagsiz pancar pancarli bezelye bezelyeli kabak kinoali bulgur irmik nisasta tavuk
hindi dana pilic koftelik pilavlik mini maxi buyuk kucuk cocuk bebek diyet stone klasik benekli kavrulmus
kabuklu ic cig kuru tatli tuzlu fume
'''.split())
FORM = set(stem(w) for w in '''
draje gofret biskuvi kurabiye kraker kek bar cips gevrek gevregi patlagi patlak toplar top cubuk krema krem
ezme ezmesi sos un unu tane tozu toz tablet kup kase kulah kornet pasta tart ekmek simit grissini granola musli
cornflakes flakes sut lokum helva recel marmelat sakiz seker sekerleme ekmegi makarna sehriye eriste pure rende
suyu icecek icecegi konserve salca sucuk salam sosis jambon kavurma fume dondurma puding kup tohum tohumu
tahil tahili gevrek pul oz ozu
'''.split())


def _sub(small, big):
    """small'daki her kelime big'de var mı? -> (hepsi var mı, eşleşmeyen big kelimeleri)"""
    used = set()
    for x in small:
        hit = None
        for j, y in enumerate(big):
            if j not in used and tok_eq(x, y):
                hit = j
                break
        if hit is None:
            # aynı kelime birden fazla geçebilir
            if not any(tok_eq(x, y) for y in big):
                return False, []
        else:
            used.add(hit)
    extras = [y for j, y in enumerate(big) if j not in used and not any(tok_eq(y, x) for x in small)]
    return True, extras


def same_product(a, b, a_list=False, b_list=False):
    """İki ürün tarifi aynı ürünü mü anlatıyor? (temkinli)
    a_list/b_list: satır birden çok ürün sayan bir liste mi (o zaman fazlalık kelimeler başka ürün adıdır)"""
    if not a or not b:
        return False
    A, B = list(dict.fromkeys(a)), list(dict.fromkeys(b))
    if len(A) <= len(B):
        small, big, big_list = A, B, b_list
    else:
        small, big, big_list = B, A, a_list
    ok, extras = _sub(small, big)
    if ok and not extras:
        return True
    if ok and not big_list and not any(e in FLAVOR or e in FORM for e in extras):
        return True
    ja, jb = ''.join(small), ''.join(big)
    if len(ja) >= 6 and difflib.SequenceMatcher(None, ja, jb).ratio() >= 0.9:
        return True
    if ok and len(small) >= 4 and len(extras) <= 1 and not any(e in FLAVOR for e in extras):
        return True
    return False


def equalish(a, b):
    if not a or not b:
        return False
    ok1, ex1 = _sub(a, b)
    ok2, ex2 = _sub(b, a)
    return (ok1 and not ex1) or (ok2 and not ex2)


RANGE_RX = re.compile(r'\b(cesitleri|cesitler|cesit|tum|hepsi|tumu|urunleri|serisi)\b')

# (marka, aile, kaynak) -> kelime: kaç satırda geçiyor. Tek kelime ancak markanın o ailesinde
# tek bir ürüne aitse ürünü tanımlar ("baobab" evet, "filtre" hayır).
TOKDF = {}


def _distinct(tok, ln):
    fam = CAT[ln['cat']]['family']
    return all(TOKDF.get((ln['brand'], fam, s), {}).get(tok, 0) <= 1 for s in ('ist', 'ank'))


def elem_ok(x, y, xs, ys, ln):
    """Liste öğesi eşleşmesi (temkinli). x ∈ xs: ln tarafı, y ∈ ys: diğer satır tarafı."""
    if min(len(x), len(y)) >= 2:
        return equalish(x, y) or same_product(x, y)
    if equalish(x, y):
        return True
    small, big = (x, y) if len(x) <= len(y) else (y, x)
    ok, extras = _sub(small, big)
    if not ok:
        return False
    # 1) ayırt edici tek kelime: "Baobab" ~ "Baobab Fruit"
    if _distinct(small[0], ln) and not any(e in FLAVOR or e in FORM for e in extras):
        return True
    # 2) ortak niteleyici listenin ilk öğesinde bir kez yazılmış:
    #    "Közlenmiş Patlıcan ve Biber" -> "biber" öğesi = "közlenmiş biber"
    sibs = xs if small is x else ys
    if len(sibs) < 2 or sibs[0] is small or len(sibs[0]) < 2:
        return False
    mods = sibs[0][:-1]
    return all(any(tok_eq(e, t) for t in mods) for e in extras)


def lines_match(ln, m, same_fam):
    same_cat = ln['cat'] == m['cat']
    if same_cat:
        a, b = ln['desc'], m['desc']
        ea, eb = ln.get('elems') or [a], m.get('elems') or [b]
    else:
        # farklı kategoriler: kategori kelimeleri (un, salam, şehriye...) ayırt edici, çıkarma
        a, b = ln['desc_raw'], m['desc_raw']
        ea, eb = ln.get('elems_raw') or [a], m.get('elems_raw') or [b]
    if same_product(a, b, len(ea) > 1 and ln.get('elems') is not None and bool(ln.get('elems')),
                    len(eb) > 1 and bool(m.get('elems'))):
        return 'whole' if (same_fam or min(len(a), len(b)) >= 2) else None
    if not same_fam:
        return None
    # liste satırları: herhangi bir öğe birebir eşleşiyor mu?
    if len(ea) > 1 or len(eb) > 1:
        for x in ea:
            for y in eb:
                if elem_ok(x, y, ea, eb, ln):
                    return 'elem'
    # "X Kuru Üzüm Çeşitleri" gibi aralık ifadesi: daha genel satırın tüm kelimeleri diğerinde var
    for gen, spec in ((ln, m), (m, ln)):
        ga, sb = (gen['desc'], spec['desc']) if same_cat else (gen['desc_raw'], spec['desc_raw'])
        gn = strip_urls(gen['n'])
        plural_range = len(ga) <= 3 and re.search(r'(lari|leri)\W*$', gn)
        if (RANGE_RX.search(gn) or plural_range) and len(ga) >= 2:
            ok, _ = _sub(ga, sb)
            if ok:
                return 'whole'
    return None


def psim(a, b):
    """Geriye dönük uyumluluk: basit oran"""
    if not a or not b:
        return 0.0, 0
    ok, _ = _sub(a if len(a) <= len(b) else b, b if len(a) <= len(b) else a)
    return (1.0, min(len(a), len(b))) if ok else (0.0, 0)


# ------------------------------------------------------- marka birleştirme ----
def unify_brands(lines):
    """İki liste arasında yazım farkı olan aynı markaları birleştir."""
    keys = {}
    for ln in lines:
        if ln.get('brand'):
            keys.setdefault(ln['brand'], set()).add(ln['src'])
    remap = {}
    # 1) çift harf farkı: patisswiss/patiswiss
    by_fk = {}
    for k in keys:
        by_fk.setdefault(fuzzkey(k), []).append(k)
    for fk, ks in by_fk.items():
        if len(ks) > 1:
            target = sorted(ks, key=lambda k: (k not in BRAND_NAME, -len(keys[k]), k))[0]
            for k in ks:
                if k != target:
                    remap[k] = target
    # 2) aynı kategori ailesinde, yalnız bir listede görünen ve birbirine çok benzeyen markalar
    fam_src = {}
    for ln in lines:
        b = remap.get(ln.get('brand'), ln.get('brand'))
        if b and ln['kind'] in ('ok', 'read'):
            fam = CAT[ln['cat']]['family'] if ln['cat'] in CAT else ln['cat']
            fam_src.setdefault(fam, {}).setdefault(b, set()).add(ln['src'])
    for fam, bmap in fam_src.items():
        ist_only = [b for b, s in bmap.items() if s == {'ist'}]
        ank_only = [b for b, s in bmap.items() if s == {'ank'}]
        for a in ist_only:
            best, score = None, 0
            for b in ank_only:
                if len(a) < 5 or len(b) < 5 or a[0] != b[0]:
                    continue
                r = difflib.SequenceMatcher(None, a, b).ratio()
                if r > score:
                    best, score = b, r
            if best and score >= 0.86:
                target = a if a in BRAND_NAME else best
                other = best if target == a else a
                remap.setdefault(other, target)
    for ln in lines:
        if ln.get('brand') in remap:
            ln['brand'] = remap[ln['brand']]
    return remap


def brand_display(lines):
    """Her marka anahtarı için en uygun görünen ad."""
    forms = {}
    for ln in lines:
        b = ln.get('brand')
        if not b or b in BRAND_NAME:
            continue
        if ln.get('span'):
            a, z = ln['span']
            # orijinal metinden aynı kelime aralığını al
            words = re.findall(r"[^\s,;:()]+", ln['text'])
            nwords = [norm(w) for w in words]
            # normalize kelimeler ile hizala
            flat = []
            for w, nw in zip(words, nwords):
                for part in nw.split():
                    flat.append(w)
            if len(flat) >= z:
                seen, disp = set(), []
                for w in flat[a:z]:
                    if id(w) not in seen:
                        disp.append(w)
                        seen.add(id(w))
                form = ' '.join(disp).strip(' .,-')
                if form:
                    forms.setdefault(b, []).append(form)
    out = dict(BRAND_NAME)
    ILAC_BRANDS.clear()
    ILAC_BRANDS.update(ln['brand'] for ln in lines if ln.get('brand') and ln['domain'] == 'ilac' and ln['cat'] == 'ilac')
    for ln in lines:
        b = ln.get('brand')
        if b and ln.get('cat') == 'ilac-firma' and b not in BRAND_NAME and b not in forms:
            name = re.split(r'\s*:|\s+[Ff][İIi]rma', ln['text'])[0]
            name = re.sub(r'(?i)\s+(i̇laç|ilaç|ilac|iLAÇ)\b.*$', '', name).strip(' .:')
            forms.setdefault(b, []).append(' '.join(tr_title(tr_lower(w)) for w in name.split()))
    for b, fl in forms.items():
        def score(f):
            has_tr = any(c in f for c in 'çğıöşüÇĞİÖŞÜ')
            mixed = f[:1].isupper() and not f.isupper()
            return (fl.count(f), has_tr, mixed, -len(f))
        best = max(set(fl), key=score)
        if best.isupper() and len(best) > 3:
            if b in ILAC_BRANDS:   # ilaç adları uluslararası: I -> i
                best = ' '.join(w[:1] + w[1:].replace('İ', 'i').replace('I', 'i').lower() for w in best.split())
            else:
                best = ' '.join(tr_title(tr_lower(w)) for w in best.split())
        out[b] = best
    return out


# ------------------------------------------------------------- eşleştirme ----
# Genel ("marka X") onayın kategori dışına taşabileceği güvenli durumlar: metinde bu ifade geçiyorsa
ALT_CAT = [(re.compile(p), c) for p, c in [
    (r'\b(fasulye|mercimek|nohut) unu', 'baklagil-unu'), (r'\bsicak cikolata', 'sicak-cikolata'),
    (r'\bmisir unu', 'misir-unu'), (r'\bpirinc unu', 'pirinc-unu'), (r'\bmisir nisastasi', 'misir-nisastasi'),
    (r'\bmisir irmigi', 'irmik'), (r'\bmisir bulguru', 'bulgur'), (r'\bkarabugday unu', 'karabugday'),
    (r'\bkeci ?boynuzu (unu|ozu)', 'keciboynuzu'), (r'\bhindistan ?cevizi (unu|yagi)', 'hindistan-cevizi'),
    (r'\bkestane unu', 'kestane-unu'), (r'\bgaleta unu', 'galeta-unu'), (r'\bpatates unu', 'patates-unu'),
    (r'\bkabartma tozu', 'kabartma-tozu'), (r'\bkrem santi', 'krem-santi'), (r'\bpudra sekeri', 'pudra-sekeri'),
    (r'\bnar eksisi', 'nar-eksisi'), (r'\bkinoa unu', 'kinoa'), (r'\bteff unu', 'teff'),
    (r'\b(yogurt|kefir)\b.*\bmaya', 'yogurt-mayasi'), (r'\bpestil', 'pestil'),
]]


def coverage_cats(ln):
    cats = {ln['cat']}
    for rx, c in ALT_CAT:
        if rx.search(ln['n']) and CAT[c]['family'] == CAT[ln['cat']]['family']:
            cats.add(c)
    return cats


def product_words(ln):
    """Satırda marka adı dışında ürün kelimesi var mı? ("Danone" hayır, "Nachos Chips Casa Fiesta" evet)"""
    bw = set(norm(BRAND_NAME.get(ln['brand'], '')).split()) | {ln['brand']}
    return [t for t in strip_urls(ln['n']).split()
            if t not in bw and t not in GENERIC_WORDS and t not in DESC_NOISE and len(t) > 1 and not t[0].isdigit()]


def match_lines(lines):
    """Her onaylı satır için diğer listede karşılığını bul."""
    idx = {}
    for ln in lines:
        if ln['kind'] != 'ok' or not ln.get('brand') or ln['domain'] == 'ilac':
            continue
        idx.setdefault(ln['brand'], []).append(ln)
    for ln in lines:
        ln['st'] = None
        ln['pair'] = []
    TOKDF.clear()
    for brand, lst in idx.items():
        for ln in lst:
            c = TOKDF.setdefault((brand, CAT[ln['cat']]['family'], ln['src']), {})
            for t in set(ln['desc_raw']) | set(ln['desc']):
                c[t] = c.get(t, 0) + 1
    for brand, lst in idx.items():
        for ln in lst:
            other = [m for m in lst if m['src'] != ln['src'] and m['domain'] == ln['domain']]
            if not other:
                ln['st'] = 'one'
                continue
            fam = CAT[ln['cat']]['family']
            cov = coverage_cats(ln)
            pairs, covered = [], False
            for m in other:   # birebir aynı ürün metni, farklı başlık altında (yalnız marka adı değil)
                if m['cat'] != ln['cat'] and CAT[m['cat']]['family'] == fam and product_words(ln) and \
                        difflib.SequenceMatcher(None, ln['n'], m['n']).ratio() >= 0.95:
                    covered = True
                    pairs.append(m['id'])
            # 1) diğer listede bu kategoride marka geneli onay
            for m in other:
                if m['generic'] and (m['cat'] in cov or ln['cat'] in coverage_cats(m) and m['cat'] == ln['cat']):
                    covered = True
                    pairs.append(m['id'])
            if ln['generic']:
                # metni diğer listedeki bir ürün satırının içinde birebir geçiyorsa ("Kinder Chocolate")
                core = ' '.join(w for w in ln['n'].split() if not CAUTION_RX.fullmatch(w))
                for m in other:
                    if m['cat'] == ln['cat'] and not m['generic'] and len(core) >= 6 and core in m['n']:
                        covered = True
                        pairs.append(m['id'])
                if covered:
                    ln['st'] = 'both'
                else:
                    same = [m for m in other if CAT[m['cat']]['family'] == fam]
                    ln['st'] = 'part' if same else 'one'
                    pairs = [m['id'] for m in same if m['cat'] == ln['cat']] or [m['id'] for m in same]
                ln['pair'] = list(dict.fromkeys(pairs))[:12]
                continue
            # 2) ürün bazında eşleşme
            whole = False
            wpairs, epairs = [], []
            for m in other:
                if m['generic']:
                    continue
                mt = lines_match(ln, m, CAT[m['cat']]['family'] == fam)
                if mt:
                    (wpairs if mt == 'whole' else epairs).append(m['id'])
                    whole = whole or mt == 'whole'
            pairs += wpairs or epairs
            # liste satırı yalnızca öğe bazında eşleştiyse: öğelerinin hepsi karşılık buldu mu?
            if not covered and not whole and pairs and ln.get('elems'):
                found = 0
                for k, e in enumerate(ln['elems']):
                    for pid in pairs:
                        pm = BY_ID[pid]
                        if pm['cat'] == ln['cat']:
                            ee, ys = e, (pm.get('elems') or [pm['desc']])
                        else:
                            er = ln.get('elems_raw') or []
                            ee = er[k] if k < len(er) else e
                            ys = pm.get('elems_raw') or [pm['desc_raw']]
                        xs = ln['elems'] if pm['cat'] == ln['cat'] else (ln.get('elems_raw') or ln['elems'])
                        if any(elem_ok(ee, y, xs, ys, ln) for y in ys):
                            found += 1
                            break
                if found < len(ln['elems']):
                    ln['st'] = 'part'
                    ln['pair'] = list(dict.fromkeys(pairs))[:12]
                    continue
            if covered or pairs:
                ln['st'] = 'both'
            else:
                same = [m for m in other if CAT[m['cat']]['family'] == fam]
                ln['st'] = 'part' if same else 'one'
                pairs = [m['id'] for m in same if m['cat'] == ln['cat']] or [m['id'] for m in same]
            ln['pair'] = list(dict.fromkeys(pairs))[:12]


def match_ilac(lines):
    """İlaçlar: İstanbul'daki her ilacın ilk kelimesi Ankara metninde geçiyor mu? (ve tersi)"""
    ist = [ln for ln in lines if ln['domain'] == 'ilac' and ln['src'] == 'ist' and ln['kind'] == 'ok']
    ank = [ln for ln in lines if ln['domain'] == 'ilac' and ln['src'] == 'ank' and ln['kind'] == 'ok']
    ank_text = ' ' + ' '.join(ln['n'] for ln in ank) + ' '
    ist_text = ' ' + ' '.join(ln['n'] for ln in ist) + ' '
    for ln in ist + ank:
        ln['st'], ln['pair'] = 'one', []
    for ln in ist:
        if ln['cat'] == 'ilac-firma':
            for m in ank:
                if m['cat'] == 'ilac-firma' and m['brand'] and (m['brand'] == ln['brand'] or
                                                                fuzzkey(m['brand']) == fuzzkey(ln['brand'])):
                    ln['st'] = 'both'
                    ln['pair'].append(m['id'])
                    m['st'] = 'both'
                    m['pair'].append(ln['id'])
            continue
        key = ln['brand']
        if key and len(key) >= 3 and (' ' + key + ' ') in ank_text:
            ln['st'] = 'both'
    for m in ank:
        if m['cat'] == 'ilac' and m['st'] != 'both':
            # Ankara satırı uzun bir liste olabilir: içindeki adların İstanbul'da geçme oranı
            names = [x for x in re.split(r'[,;]', m['text']) if clean(x)]
            if len(names) <= 1:
                key = m['brand']
                if key and (' ' + key + ' ') in ist_text:
                    m['st'] = 'both'
            else:
                m['st'] = 'mixed'


# --------------------------------------------------------------- çıktı ----
def build(pages, prev=None):
    lines = []
    lines += parse_ist_gida(pages['ist_gida'][0])
    lines += parse_ist_simple(pages['ist_ilac'][0], 'ilac', 'ilac')
    lines += parse_ist_simple(pages['ist_kozmetik'][0], 'kozmetik', 'sampuan')
    lines += parse_ist_simple(pages['ist_takviye'][0], 'takviye', 'takviye')
    ank_lines, extras = parse_ank(pages['ank'][0])
    lines += ank_lines
    for i, ln in enumerate(lines):
        ln['id'] = i
        classify(ln)
    # 1. geçiş: bağlamsız marka envanteri (kaç satırda ilk kelime olarak geçiyor)
    INVENTORY.clear()
    for ln in lines:
        if ln['kind'] in ('ok', 'read') and ln['domain'] != 'ilac':
            k, _ = detect_brand(ln['n'])
            if k:
                INVENTORY[k] = INVENTORY.get(k, 0) + 1
    # 2. geçiş: bağlam markalarıyla birlikte ata
    for ln in lines:
        assign_brand(ln)
    for ln in lines:
        if ln['kind'] == 'note' and ALL_FREE_RX.search(ln['n']):
            ln['af'] = True
    unify_brands(lines)
    BY_ID.clear()
    for ln in lines:
        BY_ID[ln['id']] = ln
        if ln['kind'] == 'ok' and ln.get('brand') and ln['domain'] != 'ilac':
            ln['desc'] = descriptor(ln)
            ln['generic'] = is_generic(ln, ln['desc'])
            ln['elems'] = elements(ln) if not ln['generic'] else []
            ln['desc_raw'] = descriptor(ln, False)
            ln['elems_raw'] = elements(ln, False) if not ln['generic'] else []
        else:
            ln['desc'], ln['generic'], ln['elems'], ln['desc_raw'], ln['elems_raw'] = [], False, [], [], []
    match_lines(lines)
    match_ilac(lines)
    disp = brand_display(lines)

    # marka × kategori grupları
    groups = {}
    for ln in lines:
        if ln['kind'] not in ('ok', 'read', 'warn') or not ln.get('brand'):
            continue
        g = groups.setdefault((ln['brand'], ln['cat']), {'b': ln['brand'], 'c': ln['cat'], 'ist': [], 'ank': []})
        g[ln['src']].append(ln['id'])
    by_id = {ln['id']: ln for ln in lines}
    for g in groups.values():
        sts = [by_id[i]['st'] for i in g['ist'] + g['ank'] if by_id[i]['kind'] == 'ok']
        if 'both' in sts:
            g['st'] = 'both'
        elif 'part' in sts:
            g['st'] = 'part'
        elif g['ist'] and g['ank']:
            g['st'] = 'both' if CAT[g['c']]['domain'] == 'ilac' else 'part'
        elif g['ist']:
            g['st'] = 'ist'
        else:
            g['st'] = 'ank'

    srcs = {
        'ist': {'name': 'Çölyakla Yaşam Derneği', 'city': 'İstanbul', 'pages': []},
        'ank': {'name': 'Çölyak Derneği', 'city': 'Ankara', 'pages': []},
    }
    for key, title in (('ist_gida', 'Glutensiz Gıdalar'), ('ist_ilac', 'Glutensiz İlaçlar'),
                       ('ist_kozmetik', 'Makyaj ve Bakım'), ('ist_takviye', 'Tıbbi Gıda Destekleri'),
                       ('ank', 'Glutensiz Yiyecek, İçecek ve İlaç Listesi')):
        p = pages[key][0]
        srcs['ank' if key == 'ank' else 'ist']['pages'].append(
            {'title': title, 'url': p['link'], 'modified': p['modified'][:10]})

    out_lines = []
    heads, head_idx = [], {}
    for ln in lines:
        h = ln['h'] or ''
        if h not in head_idx:
            head_idx[h] = len(heads)
            heads.append(h)
        rec = {'i': ln['id'], 's': ln['src'], 'c': ln['cat'], 't': ln['text'], 'h': head_idx[h],
               'k': ln['kind']}
        if ln.get('brand'):
            rec['b'] = ln['brand']
        if ln.get('st'):
            rec['st'] = ln['st']
        if ln.get('pair'):
            rec['p'] = ln['pair']
        if ln.get('generic'):
            rec['g'] = 1
        if ln.get('caution'):
            rec['w'] = 1
        if ln.get('af'):
            rec['af'] = 1
        out_lines.append(rec)

    used_brands = {ln['brand'] for ln in lines if ln.get('brand')}
    data = {
        'v': PIPELINE_VERSION,
        'generated': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat(
            timespec='minutes'),
        'sources': srcs,
        'cats': [{'id': c['id'], 'n': c['name'], 'd': c['domain']} for c in CAT.values()],
        'brands': {b: disp.get(b, b) for b in sorted(used_brands)},
        'heads': heads,
        'lines': out_lines,
        'groups': sorted(groups.values(), key=lambda g: (g['b'], g['c'])),
        'extras': extras,
        'changes': [],
    }
    data['changes'] = diff_changes(data, prev)
    data['checked'] = data['generated']
    return data, lines


def diff_changes(new, prev):
    history = list(prev.get('changes', [])) if prev else []
    if not prev:
        return history
    def keyset(d):
        return {(l['s'], norm(l['t'])): l for l in d['lines'] if l['k'] in ('ok', 'read', 'warn')}
    a, b = keyset(prev), keyset(new)
    added = [b[k] for k in b.keys() - a.keys()]
    removed = [a[k] for k in a.keys() - b.keys()]
    if added or removed:
        entry = {'date': new['generated'][:10],
                 'added': [{'s': l['s'], 't': l['t'], 'c': l['c']} for l in added][:400],
                 'removed': [{'s': l['s'], 't': l['t'], 'c': l['c']} for l in removed][:400]}
        history = [entry] + history
    return history[:12]


def main():
    pages = json.load(open(sys.argv[1], encoding='utf-8'))
    prev = None
    if len(sys.argv) > 3:
        try:
            prev = json.load(open(sys.argv[3], encoding='utf-8'))
        except Exception:
            prev = None
    data, _ = build(pages, prev)
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    n = data['lines']
    print('satır:', len(n), ' grup:', len(data['groups']), ' marka:', len(data['brands']))


if __name__ == '__main__':
    main()
