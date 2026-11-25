# -*- coding: utf-8 -*-
"""Ayrıştırma ve zenginleştirmenin ortak yardımcıları ve derleme boyunca paylaşılan durum (INVENTORY, BY_ID)."""
import re

from .metin import clean, norm
from .kategoriler import _CAT_RX
from .markalar import detect_brand


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
