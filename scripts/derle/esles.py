# -*- coding: utf-8 -*-
"""Marka birleştirme ve iki listedeki aynı ürünlerin eşleştirilmesi."""
import difflib
import re

from .metin import clean, fuzzkey, norm, tr_lower, tr_title
from .kategoriler import CAT, CAUTION_RX, GENERIC_WORDS
from .markalar import BRAND_NAME
from .ortak import BY_ID, DESC_NOISE, ILAC_BRANDS
from .zenginlestir import TOKDF, elem_ok, lines_match, strip_urls


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
