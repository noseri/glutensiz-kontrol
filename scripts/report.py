#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Haftalık kontrolün sonucunu GitHub bildirimi (issue) metnine çevirir.

Kullanım: python3 -I scripts/report.py <build_klasörü> <site_adresi>
Çıktı:    <build>/issue_title.txt, <build>/issue.md, <build>/kind.txt
kind: "degisiklik" (eklenen/çıkarılan satır var), "sessiz" (bildirim gerekmiyor),
      "kaynak-hatasi" (kaynak alınamadı), "supheli" (yayınlanmadı)
"""
import json
import os
import sys

AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
ADLAR = {'ist_gida': 'İstanbul gıda', 'ist_ilac': 'İstanbul ilaç', 'ist_kozmetik': 'İstanbul bakım-kozmetik',
         'ist_takviye': 'İstanbul takviye', 'ank': 'Ankara'}
SRC = {'ist': 'İST', 'ank': 'ANK'}


def tarih(iso):
    try:
        y, m, d = iso[:10].split('-')
        return f'{int(d)} {AYLAR[int(m) - 1]} {y}'
    except Exception:
        return iso


def main():
    b, site = sys.argv[1], sys.argv[2]
    s = json.load(open(os.path.join(b, 'summary.json'), encoding='utf-8'))
    action = s['action']
    missing = [ADLAR.get(k, k) for k in s.get('missing', [])]
    cats = {}
    data = None
    if os.path.exists(os.path.join(b, 'data.json')):
        data = json.load(open(os.path.join(b, 'data.json'), encoding='utf-8'))
        cats = {c['id']: c['n'] for c in data['cats']}
    kind, title, body = 'sessiz', '', []

    if action == 'publish' and data:
        ch = (data.get('changes') or [None])[0]
        today = data['generated'][:10]
        if ch and ch.get('date') == today and (ch['added'] or ch['removed']):
            kind = 'degisiklik'
            title = f"Listelerde değişiklik: {tarih(today)} (+{len(ch['added'])} / −{len(ch['removed'])})"
            body.append(f'Dernek listeleri kontrol edildi, aşağıdaki satırlar değişti. Sayfa güncellendi: {site}')
            for label, rows in (('Eklenen', ch['added']), ('Çıkarılan', ch['removed'])):
                if rows:
                    body.append(f'\n**{label} ({len(rows)})**')
                    for x in rows[:150]:
                        body.append(f"- {SRC.get(x['s'], x['s'])} · {cats.get(x['c'], x['c'])} — {x['t']}")
                    if len(rows) > 150:
                        body.append(f'- … ve {len(rows) - 150} satır daha (tamamı sayfadaki “Son değişiklikler” bölümünde)')
            src = s.get('sources', {})
            dates = [f"{ADLAR.get(k, k)}: {v.get('previous', '?')} → {v['modified']}" for k, v in src.items() if v.get('changed')]
            if dates:
                body.append('\nSayfası düzenlenen kaynaklar: ' + '; '.join(dates))
    elif action == 'abort':
        kind = 'supheli'
        title = 'Haftalık kontrol: şüpheli veri, yayınlanmadı'
        body.append(s.get('reason', ''))
        body.append('\nDerneklerden birinin sayfa yapısı değişmiş olabilir. Sayfadaki liste olduğu gibi kaldı; '
                    'ayrıştırıcının güncellenmesi gerekiyor.')
    elif action in ('partial', 'no_change'):
        kind = 'kaynak-hatasi'
        title = 'Haftalık kontrol: kaynak sayfa alınamadı'
        body.append('Alınamayan: ' + ', '.join(missing) + '.')
        body.append('Sayfadaki liste olduğu gibi kaldı; “Son kontrol” tarihi ilerletilmedi. Sonraki hafta yeniden denenecek.')

    if missing and kind == 'degisiklik':
        body.append('\nNot: ' + ', '.join(missing) + ' bu hafta alınamadı; o kaynaklar için önceki sürüm kullanıldı '
                    've “Son kontrol” tarihi ilerletilmedi.')
    if kind == 'sessiz' and missing:
        kind = 'kaynak-hatasi'
        title = 'Haftalık kontrol: kaynak sayfa alınamadı'
        body.append('Alınamayan: ' + ', '.join(missing) + '. Diğer kaynaklar işlendi.')
    open(os.path.join(b, 'kind.txt'), 'w').write(kind)
    open(os.path.join(b, 'issue_title.txt'), 'w', encoding='utf-8').write(title)
    open(os.path.join(b, 'issue.md'), 'w', encoding='utf-8').write('\n'.join(body) + '\n')
    print(kind, '|', title)


if __name__ == '__main__':
    main()
