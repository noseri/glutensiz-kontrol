#!/usr/bin/env python3
"""Kalıcı ürün numarası (u) testleri: python3 tests/test_kimlik.py"""
import copy, importlib.util, json, os, sys
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('gk', os.path.join(KOK, 'scripts', 'pipeline.py'))
gk = importlib.util.module_from_spec(spec); spec.loader.exec_module(gk)
ok = bad = 0
def check(n, c, i=''):
    global ok, bad
    if c: ok += 1; print('  ✓', n)
    else: bad += 1; print('  ✗', n, i)

BR = {'pocoloco': 'Poco Loco', 'eti': 'Eti'}
CD = {'cips': 'gida', 'atistirmalik': 'gida', 'biskuvi': 'gida', 'ilac': 'ilac'}
def L(s, t, b='pocoloco', c='cips'): return {'s': s, 't': t, 'b': b, 'c': c, 'k': 'ok'}
prev_lines = [L('ist', 'Poco Loco Nacho Cipsi'), L('ist', 'Poco Loco Tortilla Cipsi'), L('ank', 'Poco Loco Nacho Cips', c='atistirmalik'),
              L('ank', 'Poco Loco Crispy'), L('ist', 'Eti Glutensiz Kakaolu Kurabiye', 'eti', 'biskuvi'), L('ist', 'Eti Glutensiz Kakaolu Kurabiye', 'eti', 'biskuvi')]
son = gk.assign_uids(prev_lines, None, BR, CD)
prev = {'lines': prev_lines, 'son_u': son, 'brands': BR}
check('ilk sefer: sırayla 1..n', [l['u'] for l in prev_lines] == [1, 2, 3, 4, 5, 6] and son == 6)

new = [copy.deepcopy(l) for l in reversed(prev_lines)]
for l in new: l.pop('u')
son2 = gk.assign_uids(new, prev, BR, CD)
check('sıra değişse de aynı metin aynı numara', {(l['s'], l['t'], l['u']) for l in new} == {(l['s'], l['t'], l['u']) for l in prev_lines} and son2 == 6)
check('aynı metin iki kez geçiyorsa iki numara da korunur', sorted(l['u'] for l in new if l['b'] == 'eti') == [5, 6])

new = [L('ist', 'Poco Loco Nacho Cipsi 150 g'), L('ist', 'Poco Loco Tortilla Cipsi'), L('ank', 'Poco Loco Nacho Cips', c='atistirmalik'), L('ank', 'Poco Loco Crispy')]
son3 = gk.assign_uids(new, prev, BR, CD)
check('yazımı değişen satır numarasını devralır (gramaj eklendi)', new[0]['u'] == 1, new[0])
check('çıkarılan ürünlerin numarası yeniden kullanılmaz', son3 == 6)
new = [L('ist', 'Poco Loco Nacho Cipsi Acılı')]
gk.assign_uids(new, prev, BR, CD)
check('tek kelime eklenirse numara korunur (uyarılar kaybolmasın)', new[0]['u'] == 1, new[0])
new = [L('ist', 'Poco Loco Nacho Cipsi Acılı Peynirli')]
gk.assign_uids(new, prev, BR, CD)
check('ad çok değiştiyse yeni ürün sayılır', new[0]['u'] == 7, new[0])

new = [L('ank', 'Poco Loco Crispy 120 g')]
gk.assign_uids(new, prev, BR, CD)
check('kısa adda gramaj eklenmesi numarayı değiştirmez (gıda)', new[0]['u'] == 4, new[0])
pi = {'lines': [dict(L('ist', 'Parol 500 mg Tablet', b='parol', c='ilac'), u=20)], 'son_u': 20, 'brands': {'parol': 'Parol'}}
new = [L('ist', 'Parol 250 mg Tablet', b='parol', c='ilac')]
gk.assign_uids(new, pi, {'parol': 'Parol'}, CD)
check('ilaçta doz farkı ayrı ürün sayılır (numara devralınmaz)', new[0]['u'] == 21, new[0])
new = [L('ank', 'Poco Loco Sweet'), L('ank', 'Poco Loco Crispy')]
son4 = gk.assign_uids(new, prev, BR, CD)
check('benzemeyen yeni ürün yeni numara alır (eskisine bağlanmaz)', new[0]['u'] == 7 and new[1]['u'] == 4 and son4 == 7, new)

new = [L('ist', 'Poco Loco Nacho Cipsi', b='baskamarka')]
gk.assign_uids(new, prev, BR, CD)
check('metin aynıysa marka eşleşmesi değişse de numara korunur', new[0]['u'] == 1)

new = [L('ist', 'Poco Loco Tortilla')]
prev2 = {'lines': [dict(L('ist', 'Poco Loco Tortilla Cipsi'), u=2), dict(L('ist', 'Poco Loco Tortilla Dürüm'), u=9)], 'son_u': 9, 'brands': BR}
gk.assign_uids(new, prev2, BR, CD)
check('iki aday eşit benzerse devralmaz (emin değil)', new[0]['u'] == 10, new)

new = [L('ank', 'Poco Loco Nacho Cipsi')]
gk.assign_uids(new, prev, BR, CD)
check('başka listedeki aynı metin o listenin numarasını almaz', new[0]['u'] == 7, new)

# gerçek veri: derleme yeniden çalışınca bütün numaralar aynı kalmalı
d = json.load(open(os.path.join(KOK, 'site', 'data.json'), encoding='utf-8'))
if all('u' in l for l in d['lines']):
    pages = json.load(open(os.path.join(KOK, 'raw', 'pages.json'), encoding='utf-8'))
    data, _ = gk.build(pages, d)
    a = {(l['s'], l['t'], l['c']): l['u'] for l in d['lines']}
    b = {(l['s'], l['t'], l['c']): l['u'] for l in data['lines']}
    check('gerçek liste yeniden derlenince numaralar aynı', a == b, len(set(a.items()) ^ set(b.items())))
    check('numaralar benzersiz', len({l['u'] for l in data['lines']}) == len(data['lines']))
print(f'\n{ok} geçti, {bad} kaldı'); sys.exit(1 if bad else 0)
