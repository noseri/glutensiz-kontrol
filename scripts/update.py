#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Glutensiz Kontrol — haftalık güncelleme yardımcısı

Kullanım:
  python3 -I update.py <yeni_ank.json> <yeni_ist.json> <onceki_pages.json> <onceki_data.json> <pipeline.py> <cikti_klasoru>

<yeni_ank.json>  Tarayıcıdan alınan Ankara sayfası: WordPress REST yanıtı ([page] ya da {"body":[page]})
                 veya araç çıktısının kaydedildiği dosya ([{"type":"text","text":"..."}]). Yoksa "-" yazın.
<yeni_ist.json>  İstanbul sayfaları: {"ist_gida": [page], "ist_ilac": [page], "ist_kozmetik": [page],
                 "ist_takviye": [page]} (eksik anahtar olabilir) ya da araç çıktısı dosyası. Yoksa "-".

Çıkış: <cikti_klasoru>/data.json, pages.json, summary.json
summary.json["action"]: "publish" (değişiklik var: data.json + pages.json yayınlanır),
  "checked_only" (tüm kaynaklar alındı, değişiklik yok: yalnız "son kontrol" tarihi güncellenir),
  "partial" (bazı kaynaklar alınamadı, alınanlarda değişiklik yok; yayınlanmaz),
  "no_change" (hiçbir kaynak alınamadı; yayınlanmaz) ya da "abort" (şüpheli veri; yayınlanmaz).
Bazı kaynaklar alınamadığında değişiklik yine yayınlanır ama "son kontrol" tarihi ilerletilmez;
alınamayanlar summary["missing"] içinde listelenir.
"""
import datetime
import importlib.util
import json
import os
import sys

KEYS = ['ist_gida', 'ist_ilac', 'ist_kozmetik', 'ist_takviye', 'ank']
MIN_LEN = {'ist_gida': 20000, 'ist_ilac': 5000, 'ist_kozmetik': 800, 'ist_takviye': 1500, 'ank': 40000}


def unwrap(path):
    """Düz JSON, REST yanıtı veya araç çıktısı sarmalayıcısını aç."""
    if not path or path == '-' or not os.path.exists(path):
        return None
    raw = open(path, encoding='utf-8').read().strip()
    try:
        v = json.loads(raw)
    except Exception:
        return None
    for _ in range(4):
        if isinstance(v, list) and v and isinstance(v[0], dict) and v[0].get('type') == 'text' and 'text' in v[0]:
            t = v[0]['text']
            cut = t.rfind('\n\n(captured at origin')
            if cut != -1:
                t = t[:cut]
            try:
                v = json.loads(t)
            except Exception:
                return None
            continue
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                return None
            continue
        break
    return v


def as_page(v):
    """[page] / {"body":[page]} / page -> page dict ya da None"""
    if isinstance(v, dict) and 'body' in v:
        v = v['body']
    if isinstance(v, dict) and 'txt' in v:
        try:
            v = json.loads(v['txt'])
        except Exception:
            return None
    if isinstance(v, list):
        v = v[0] if v else None
    if isinstance(v, dict) and isinstance(v.get('content'), dict) and 'rendered' in v['content'] and v.get('modified'):
        return v
    return None


def main():
    ank_p, ist_p, prev_pages_p, prev_data_p, pipe_p, out_dir = sys.argv[1:7]
    os.makedirs(out_dir, exist_ok=True)
    prev_pages = json.load(open(prev_pages_p, encoding='utf-8'))
    prev_data = json.load(open(prev_data_p, encoding='utf-8'))

    fresh = {}
    a = as_page(unwrap(ank_p))
    if a:
        fresh['ank'] = a
    ist = unwrap(ist_p)
    if isinstance(ist, dict):
        for k in KEYS[:4]:
            pg = as_page(ist.get(k))
            if pg:
                fresh[k] = pg

    pages, report = {}, {}
    for k in KEYS:
        old = prev_pages[k][0]
        new = fresh.get(k)
        if new and len(new['content']['rendered']) >= MIN_LEN[k]:
            pages[k] = [new]
            changed = new['modified'] != old['modified'] or new['content']['rendered'] != old['content']['rendered']
            report[k] = {'fetched': True, 'changed': changed, 'modified': new['modified'][:10],
                         'previous': old['modified'][:10]}
        else:
            pages[k] = [old]
            report[k] = {'fetched': False, 'changed': False, 'modified': old['modified'][:10],
                         'note': 'alınamadı ya da çok kısa; önceki sürüm kullanıldı' if new is None else 'çok kısa yanıt; önceki sürüm kullanıldı'}

    summary = {'sources': report}
    summary['missing'] = [k for k in KEYS if not report[k]['fetched']]
    all_fetched = not summary['missing']
    any_change = any(r['changed'] for r in report.values())
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat(timespec='minutes')
    if not any_change:
        # içerik aynı: yalnızca "son kontrol" tarihini güncelle (sayfa listelerin güncel olduğunu göstersin)
        if all_fetched:
            summary['action'] = 'checked_only'
        else:
            summary['action'] = 'partial' if any(r['fetched'] for r in report.values()) else 'no_change'
        if summary['action'] == 'checked_only':
            prev_data['checked'] = now
            with open(os.path.join(out_dir, 'data.json'), 'w', encoding='utf-8') as f:
                json.dump(prev_data, f, ensure_ascii=False, separators=(',', ':'))
        json.dump(summary, open(os.path.join(out_dir, 'summary.json'), 'w'), ensure_ascii=False, indent=1)
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        return

    spec = importlib.util.spec_from_file_location('gk_pipeline', pipe_p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data, _ = mod.build(pages, prev_data)

    def ok_count(d, src):
        return sum(1 for l in d['lines'] if l['s'] == src and l['k'] == 'ok')
    counts = {s: (ok_count(prev_data, s), ok_count(data, s)) for s in ('ist', 'ank')}
    summary['ok_lines'] = {s: {'onceki': c[0], 'yeni': c[1]} for s, c in counts.items()}
    suspicious = [s for s, (o, n) in counts.items() if o and n < 0.6 * o]
    if suspicious:
        summary['action'] = 'abort'
        summary['reason'] = 'Onaylı satır sayısı %40\'tan fazla düştü: ' + ', '.join(suspicious) + \
                            ' — sayfa yapısı değişmiş olabilir; yayınlanmadı.'
    else:
        summary['action'] = 'publish'
        if not all_fetched:   # eksik kaynak varken "son kontrol" tarihini ilerletme
            data['checked'] = prev_data.get('checked') or prev_data.get('generated')
        ch = data.get('changes') or []
        if ch and ch[0].get('date') == data['generated'][:10]:
            summary['added'] = len(ch[0]['added'])
            summary['removed'] = len(ch[0]['removed'])
            summary['added_sample'] = [('İST ' if x['s'] == 'ist' else 'ANK ') + x['t'][:90] for x in ch[0]['added'][:15]]
            summary['removed_sample'] = [('İST ' if x['s'] == 'ist' else 'ANK ') + x['t'][:90] for x in ch[0]['removed'][:15]]
        else:
            summary['added'] = summary['removed'] = 0
        with open(os.path.join(out_dir, 'data.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        with open(os.path.join(out_dir, 'pages.json'), 'w', encoding='utf-8') as f:
            json.dump(pages, f, ensure_ascii=False)
    json.dump(summary, open(os.path.join(out_dir, 'summary.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
