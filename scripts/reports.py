#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Glutensiz Kontrol — gluten analiz raporlarını (Doğa Evinizde) çeker ve marka anahtarlarımıza eşler.

Kullanım:  python3 -I scripts/reports.py <data.json> <reports.json> [--html yerel_sayfa.html]

Çıktı (site/reports.json):
  {"source": {...}, "checked": "...", "total": 80,
   "brands": {"droetker": {"name": "Dr. Oetker", "n": 5, "last": "2026-07", "url": "...#dr-oetker"}, ...},
   "unmatched": ["Kılınçarslan", ...]}

Bilgi amaçlıdır; onay mantığına girmez. Sayfa alınamazsa ya da şüpheli derecede az rapor çıkarsa
önceki reports.json olduğu gibi bırakılır (sağlam dosya ezilmez).
"""
import datetime
import importlib.util
import json
import os
import re
import sys
import time
import urllib.request

from bs4 import BeautifulSoup

URL = 'https://www.dogaevinizde.com/gluten-analiz-raporlari'
UA = 'Mozilla/5.0 (compatible; GlutensizKontrol/1.0; haftalik liste kontrolu)'
AYLAR = {'ocak': 1, 'subat': 2, 'mart': 3, 'nisan': 4, 'mayis': 5, 'haziran': 6, 'temmuz': 7,
         'agustos': 8, 'eylul': 9, 'ekim': 10, 'kasim': 11, 'aralik': 12}
MIN_BRANDS, MIN_REPORTS = 5, 20

_spec = importlib.util.spec_from_file_location('gk_pipeline', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pipeline.py'))
pl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pl)


def fetch(url):
    err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:   # bağlantı, zaman aşımı, HTTP hatası
            err = e
            time.sleep(15 * (attempt + 1))
    raise err


def parse(html):
    """Rapor tablosu: Marka | Belge | Yıl | PDF. Marka -> {name, slug, anchor, items}"""
    soup = BeautifulSoup(html, 'lxml')
    ids = {e.get('id') for e in soup.find_all(id=True)}
    table = None
    for t in soup.find_all('table'):
        heads = [pl.norm(th.get_text(' ')) for th in t.find_all('th')]
        if 'marka' in heads and 'belge' in heads:
            table = t
            break
    if table is None:
        return {}
    brands, seen = {}, set()
    body = table.find('tbody') or table
    for tr in body.find_all('tr'):
        tds = tr.find_all(['th', 'td'], recursive=False)   # ilk hücre (marka) satır başlığı <th>
        a = tr.find('a', href=re.compile(r'\.pdf', re.I))
        if len(tds) < 4 or not a:
            continue
        href = a['href']
        if href in seen:
            continue
        seen.add(href)
        name = tds[0].get_text(' ', strip=True)
        title = tds[1].get_text(' ', strip=True)
        year = tds[2].get_text(' ', strip=True)
        if not name:
            continue
        m = re.search(r'gluten-raporlari/([a-z0-9-]+)/', href)
        ym = None
        mm = re.search(r'([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(20\d\d)', title)
        if mm and pl.norm(mm.group(1)) in AYLAR:
            ym = f'{mm.group(2)}-{AYLAR[pl.norm(mm.group(1))]:02d}'
        elif re.fullmatch(r'20\d\d', year):
            ym = year
        b = brands.setdefault(name, {'name': name, 'slug': m.group(1) if m else None, 'items': []})
        b['items'].append({'t': title, 'u': href, 'd': ym})
    for b in brands.values():
        b['anchor'] = b['slug'] if b['slug'] in ids else None
    return brands


def match(name, data):
    """Rapor sayfasındaki marka adını dernek listelerindeki marka anahtarına eşle (temkinli)."""
    keys = data['brands']
    c = pl.compact(name)
    if c in keys:
        return c
    for k, disp in keys.items():
        if pl.fuzzkey(k) == pl.fuzzkey(c) or pl.compact(disp) == c:
            return k
    # "Sofra Glutensiz" -> sofra: yalnızca o markanın bir satırında tam ad geçiyorsa
    words = name.split()
    first = pl.compact(words[0]) if words else ''
    if first in keys and len(words) > 1:
        full = pl.norm(name)
        if any(full in pl.norm(l['t']) for l in data['lines'] if l.get('b') == first):
            return first
    return None


def build(brands, data):
    out, unmatched, total = {}, [], 0
    for name, b in sorted(brands.items(), key=lambda x: pl.norm(x[0])):
        total += len(b['items'])
        k = match(name, data)
        if not k:
            unmatched.append(name)
            continue
        dates = sorted(i['d'] for i in b['items'] if i['d'])
        url = URL + ('#' + b['anchor'] if b['anchor'] else '')
        prev = out.get(k)
        if prev:   # aynı markaya iki başlık eşlenirse birleştir
            prev['n'] += len(b['items'])
            prev['last'] = max(filter(None, [prev['last'], dates[-1] if dates else None]), default=None)
            continue
        out[k] = {'name': name, 'n': len(b['items']), 'last': dates[-1] if dates else None, 'url': url}
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat(timespec='minutes')
    return {'source': {'name': 'Doğa Evinizde', 'url': URL}, 'checked': now, 'total': total,
            'brands': out, 'unmatched': unmatched}


def main():
    data_p, out_p = sys.argv[1], sys.argv[2]
    html_p = sys.argv[sys.argv.index('--html') + 1] if '--html' in sys.argv else None
    data = json.load(open(data_p, encoding='utf-8'))
    prev = None
    if os.path.exists(out_p):
        try:
            prev = json.load(open(out_p, encoding='utf-8'))
        except Exception:
            prev = None
    try:
        html = open(html_p, encoding='utf-8').read() if html_p else fetch(URL)
    except Exception as e:
        print(f'Analiz raporu sayfası alınamadı ({type(e).__name__}: {e}); önceki dosya korunuyor.')
        return
    brands = parse(html)
    total = sum(len(b['items']) for b in brands.values())
    floor_b = max(MIN_BRANDS, int(0.5 * len((prev or {}).get('brands', {}))))
    if len(brands) < MIN_BRANDS or total < MIN_REPORTS or (prev and len(brands) < floor_b):
        print(f'Şüpheli sonuç ({len(brands)} marka, {total} rapor); sayfa yapısı değişmiş olabilir. Önceki dosya korunuyor.')
        return
    res = build(brands, data)
    if prev and {k: v for k, v in prev.items() if k != 'checked'} == {k: v for k, v in res.items() if k != 'checked'}:
        res['checked'] = prev.get('checked', res['checked'])   # içerik aynı: dosyayı değiştirme
    with open(out_p, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"{len(brands)} marka, {total} rapor; {len(res['brands'])} marka listelerimizle eşleşti. "
          f"Eşleşmeyen: {', '.join(res['unmatched']) or '-'}")


if __name__ == '__main__':
    main()
