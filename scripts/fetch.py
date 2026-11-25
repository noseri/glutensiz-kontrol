#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Glutensiz Kontrol — dernek listelerini WordPress veri arayüzünden (REST) çeker.

Kullanım:  python3 -I scripts/fetch.py <çıktı_klasörü>
Çıktı:     <klasör>/ank.json  -> [sayfa]
           <klasör>/ist.json  -> {"ist_gida": [sayfa], "ist_ilac": [...], ...}  (alınamayan anahtar yazılmaz)
           <klasör>/fetch_report.json -> her sayfa için durum, süre, deneme sayısı
Alınamayan sayfa çıkışı bozmaz: update.py o sayfa için önceki sürümü kullanır ve durumu raporlar.
İstanbul sitesi yavaş (istek başına 30-60 sn): uzun zaman aşımı, sıralı istek ve tekrar deneme.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

FIELDS = 'id,modified,modified_gmt,slug,link,title,content'
SOURCES = {
    'ist_gida': ('https://colyak.org.tr', 8644, 'glutensiz-urunler'),
    'ist_ilac': ('https://colyak.org.tr', 8646, 'glutensiz-ilaclar'),
    'ist_kozmetik': ('https://colyak.org.tr', 9136,
                     'glutensiz-sabun-sampuan-cilt-agiz-bakim-dis-macunlari-makyaj-urunleri-vb'),
    'ist_takviye': ('https://colyak.org.tr', 8787, 'tibbi-gida-destekleri'),
    'ank': ('https://www.colyakankara.org.tr', 2278, 'glutensiz-ilac-ve-yiyecek-listesi'),
}
TIMEOUT = 150
ATTEMPTS = 3
UA = 'Mozilla/5.0 (compatible; GlutensizKontrol/1.0; haftalik liste kontrolu)'


def get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = r.read()
    return json.loads(body.decode('utf-8'))


def valid(page):
    return isinstance(page, dict) and isinstance(page.get('content'), dict) and \
        isinstance(page['content'].get('rendered'), str) and page.get('modified')


def fetch_one(base, pid, slug):
    """Önce sayfa kimliğiyle, olmazsa kısa adıyla (sayfa yeniden oluşturulmuşsa) dener."""
    urls = [f'{base}/wp-json/wp/v2/pages/{pid}?_fields={FIELDS}',
            f'{base}/wp-json/wp/v2/pages?slug={slug}&_fields={FIELDS}',
            f'{base}/?rest_route=/wp/v2/pages/{pid}&_fields={FIELDS}']
    errors = []
    for attempt in range(1, ATTEMPTS + 1):
        for url in urls:
            t0 = time.time()
            try:
                v = get_json(url)
                if isinstance(v, list):
                    v = v[0] if v else None
                if valid(v):
                    return v, {'ok': True, 'url': url, 'attempt': attempt, 'seconds': round(time.time() - t0, 1),
                               'length': len(v['content']['rendered']), 'modified': v['modified']}
                errors.append(f'{url}: geçersiz yanıt')
            except urllib.error.HTTPError as e:
                errors.append(f'{url}: HTTP {e.code} ({round(time.time() - t0, 1)} sn)')
            except Exception as e:   # zaman aşımı, bağlantı, JSON
                errors.append(f'{url}: {type(e).__name__}: {e} ({round(time.time() - t0, 1)} sn)')
        if attempt < ATTEMPTS:
            time.sleep(30 * attempt)
    return None, {'ok': False, 'errors': errors[-6:]}


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    ist, report = {}, {}
    ank = None
    for key, (base, pid, slug) in SOURCES.items():
        page, rep = fetch_one(base, pid, slug)
        report[key] = rep
        state = f"tamam  {rep['seconds']:>6} sn  {rep['length']:>7} karakter  düzenleme {rep['modified']}" if rep['ok'] \
            else 'ALINAMADI  ' + ' | '.join(rep['errors'][-2:])
        print(f'{key:13} {state}', flush=True)
        if page:
            if key == 'ank':
                ank = [page]
            else:
                ist[key] = [page]
    with open(os.path.join(out, 'ist.json'), 'w', encoding='utf-8') as f:
        json.dump(ist, f, ensure_ascii=False)
    with open(os.path.join(out, 'ank.json'), 'w', encoding='utf-8') as f:
        json.dump(ank if ank else [], f, ensure_ascii=False)
    with open(os.path.join(out, 'fetch_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    ok = sum(1 for r in report.values() if r['ok'])
    print(f'{ok}/{len(report)} sayfa alındı')


if __name__ == '__main__':
    main()
