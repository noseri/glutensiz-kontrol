# -*- coding: utf-8 -*-
"""Satırları sınıflandırma, marka atama ve ürün tanımlayıcıları (eşleştirmenin hazırlığı)."""
import difflib
import re

from .metin import compact, norm, stem
from .kategoriler import CAT, CAT_WORDS, CAUTION_RX, GENERIC_WORDS, WARN_RX
from .markalar import BRAND_NAME, detect_brand
from .ortak import ALL_FREE_RX, DESC_NOISE, INVENTORY, NOTE_START


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
