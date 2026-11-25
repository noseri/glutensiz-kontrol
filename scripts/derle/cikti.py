# -*- coding: utf-8 -*-
"""Derleme: sayfalardan data.json'a; kalıcı ürün numaraları (u) ve haftalık değişiklik kaydı."""
import datetime
import re

from .metin import norm
from .kategoriler import CAT
from .markalar import detect_brand
from .ortak import ALL_FREE_RX, BY_ID, INVENTORY
from .ayristir import parse_ank, parse_ist_gida, parse_ist_simple
from .zenginlestir import assign_brand, classify, descriptor, elements, is_generic
from .esles import brand_display, match_ilac, match_lines, unify_brands


# --------------------------------------------------------------- çıktı ----
PIPELINE_VERSION = 4   # 4: her satırda kalıcı ürün numarası (u)

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
               'k': ln['kind']}   # 'u' (kalıcı ürün numarası) aşağıda assign_uids ile eklenir
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
    data['son_u'] = assign_uids(out_lines, prev, data['brands'], {c['id']: c['d'] for c in data['cats']})
    data['changes'] = diff_changes(data, prev)
    data['checked'] = data['generated']
    return data, lines


UID_STOP = {'ve', 'ile', 'mg', 'ml', 'gr', 'kg', 'lt', 'cl', 'iu'}
# gıda ve kozmetikte gramaj/hacim aynı ürünün farklı yazımıdır; ilaç ve takviyede doz ayrı üründür
UID_OLCU = re.compile(r'^\d+(?:[.,]\d+)?(?:g|gr|kg|ml|cl|lt|l|cc|adet)?$')


def assign_uids(out_lines, prev, brands, cat_domain):
    """Her satıra kalıcı ürün numarası (u) verir; tepkiler ve kişisel kayıtlar bu numaraya bağlanır.

    Önceki haftanın verisiyle eşleştirir:
      1) aynı kaynak ve aynı metin (önce aynı kategoride) → aynı numara;
      2) kalanlar: aynı kaynak, aynı marka ve aynı alanda metni en benzer satır → numarayı devralır
         (yazımı değişmiş satır; gıda ve kozmetikte gramaj farkı sayılmaz). Benzerlik en az 0.6 ve ikinci adaydan en az 0.15 fazla olmalı;
         emin değilse devralmaz, satır yeni ürün sayılır;
      3) kalanlara yeni numara. Numaralar hiçbir zaman yeniden kullanılmaz (son_u).
    Döndürür: şimdiye kadar verilmiş en büyük numara.
    """
    from collections import defaultdict, deque
    prev = prev or {}
    old = [l for l in prev.get('lines', []) if isinstance(l.get('u'), int)]
    son = max([int(prev.get('son_u') or 0)] + [l['u'] for l in old])
    allb = dict(prev.get('brands') or {}); allb.update(brands or {})
    used = set()

    def take(q):
        while q:
            u = q.popleft()
            if u not in used:
                used.add(u)
                return u
        return None
    by_text_cat, by_text = defaultdict(deque), defaultdict(deque)
    for l in old:
        k = (l['s'], norm(l['t']))
        by_text_cat[k + (l['c'],)].append(l['u'])
        by_text[k].append(l['u'])
    for l in out_lines:
        l.pop('u', None)
        u = take(by_text_cat[(l['s'], norm(l['t']), l['c'])])
        if u is not None:
            l['u'] = u
    for l in out_lines:
        if 'u' not in l:
            u = take(by_text[(l['s'], norm(l['t']))])
            if u is not None:
                l['u'] = u

    def toks(l):
        bw = set(norm(allb.get(l.get('b'), '') or '').split())
        olcu = cat_domain.get(l['c']) in ('gida', 'kozmetik')
        return {w for w in norm(l['t']).split()
                if len(w) > 1 and w not in UID_STOP and w not in bw and not (olcu and UID_OLCU.match(w))}
    bucket = defaultdict(list)
    for l in old:
        if l['u'] not in used:
            bucket[(l['s'], l.get('b') or '', cat_domain.get(l['c']))].append((l['u'], toks(l)))
    pairs = []
    for l in out_lines:
        if 'u' in l:
            continue
        a = toks(l)
        cands = bucket.get((l['s'], l.get('b') or '', cat_domain.get(l['c'])), [])
        if not a or not cands:
            continue
        scored = sorted(((len(a & b) / len(a | b), u) for u, b in cands if b), reverse=True)
        if not scored:
            continue
        best, u = scored[0]
        second = scored[1][0] if len(scored) > 1 else 0.0
        if best >= 0.6 and best - second >= 0.15:
            pairs.append((best, u, l))
    for best, u, l in sorted(pairs, key=lambda x: -x[0]):
        if u not in used and 'u' not in l:
            used.add(u)
            l['u'] = u
    for l in out_lines:
        if 'u' not in l:
            son += 1
            l['u'] = son
    return son


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
