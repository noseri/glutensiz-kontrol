#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Glutensiz Liste Birleştirici — işleme hattının giriş noktası

Kullanım:
  python3 -I pipeline.py pages.json data.json [onceki_data.json]

pages.json biçimi (WordPress REST API sayfa nesneleri):
  {"ist_gida": [page], "ist_ilac": [page], "ist_kozmetik": [page],
   "ist_takviye": [page], "ank": [page]}

Çıktı: ön yüzün okuduğu data.json

Kod scripts/derle/ paketindedir; her katman yalnızca kendinden öncekileri kullanır:
  metin → kategoriler → markalar → ortak → ayristir → zenginlestir → esles → cikti
update.py, reports.py ve testler bu dosyayı yükler; aşağıdaki adlar onlar içindir.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # "python3 -I" ile çalışınca da derle/ bulunsun
from derle.cikti import PIPELINE_VERSION, build, assign_uids, diff_changes  # noqa: E402,F401
from derle.metin import clean, norm, compact, fuzzkey, tr_lower, tr_title, stem  # noqa: E402,F401


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
