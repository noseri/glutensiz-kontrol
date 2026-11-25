#!/usr/bin/env python3
"""Sunucu (Worker + D1) testleri: boş veritabanıyla başlar."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import api, check, bitir, A, H

KOKEN = 'http://localhost:8765'
# --- kimlik ve gizlilik
s, j, h, _ = api('GET', '/'); check('açık uç: çalışıyor', s == 200 and j['durum'] == 'çalışıyor', j)
s, j, h, dt = api('GET', '/veri'); check('şifresiz kişisel veri → 401 + gecikme', s == 401 and dt >= 0.6, (s, j, dt))
s, j, h, _ = api('GET', '/liste'); check('eski açık liste adresi kapalı (404)', s == 404, (s, j))
s, j, h, _ = api('GET', '/tepkiler', key=A); check('eski tepkiler adresi kapalı (404)', s == 404, (s, j))
s, j, h, _ = api('GET', '/ben', key='yanlis-sifre-000'); check('yanlış şifre → 401', s == 401 and j['hata'] == 'Şifre tanınmadı.', j)
s, j, h, _ = api('GET', '/ben', key='kisa'); check('kısa şifre → 401', s == 401, j)
s, j, h, _ = api('GET', '/ben', key=A); check('şifre 1 → mayildiz', s == 200 and j == {'ad': 'mayildiz'}, j)
s, j, h, _ = api('GET', '/ben', key='  ' + H + '  '); check('Türkçe harfli şifre 2 (boşluklu) → heyybenbus', s == 200 and j == {'ad': 'heyybenbus'}, j)
s, j, h, _ = api('GET', '/veri', key=A); check('boş veri: dört liste', s == 200 and all(j[k] == [] for k in ('urunler', 'cikarilanlar', 'tepkiler', 'dokunmalar')), j)

# --- Bizim listemiz: ekle, çıkar
s, j, h, _ = api('POST', '/ekle', {'alan': 'kozmetik', 'marka': ' Elidor ', 'urun': 'Şampuan  Onarıcı', 'kategori': 'Şampuan', 'dayanak': 'paket', 'notu': 'Paketin‮arkasında yazıyor​', 'ekleyen': 'Sahte', 'eklendi': '2020-01-01T00:00:00Z', 'id': 999}, A)
u = (j or {}).get('urun') or {}
check('ekle → 201', s == 201, (s, j))
check('ekleyen, tarih ve id sunucudan', u.get('ekleyen') == 'mayildiz' and u.get('eklendi', '').endswith('Z') and not u['eklendi'].startswith('2020') and u.get('id') == 1, u)
check('boşluk temizliği ve görünmez/yön karakterleri', u.get('marka') == 'Elidor' and u.get('urun') == 'Şampuan Onarıcı' and u.get('notu') == 'Paketin arkasında yazıyor', u)
check('esas dışarı verilmiyor', 'esas' not in u, u)
s, j, h, _ = api('POST', '/ekle', {'alan': 'kozmetik', 'marka': 'ELİDOR', 'urun': 'sampuan onarici', 'dayanak': 'deneyim'}, H)
check('aynı ürün (harf farklı) → 409, kim eklemiş', s == 409 and j['urun']['ekleyen'] == 'mayildiz', (s, j))
for ad, body, code in [
    ('alan yok', {'marka': 'A', 'urun': 'B', 'dayanak': 'paket'}, 400),
    ('dayanak yanlış', {'alan': 'gida', 'marka': 'A', 'urun': 'B', 'dayanak': 'x'}, 400),
    ('marka uzun', {'alan': 'gida', 'marka': 'A' * 61, 'urun': 'B', 'dayanak': 'paket'}, 400),
    ('yalnız noktalama', {'alan': 'gida', 'marka': '!!!', 'urun': '...', 'dayanak': 'paket'}, 400),
    ('not uzun', {'alan': 'gida', 'marka': 'A', 'urun': 'B', 'dayanak': 'paket', 'notu': 'x' * 281}, 400)]:
    s, j, h, _ = api('POST', '/ekle', body, A); check(ad + ' → ' + str(code), s == code and 'hata' in j, (s, j))
s, j, h, _ = api('POST', '/ekle', {'alan': 'gida'}, A, ctype='text/plain'); check('JSON değil → 415', s == 415, (s, j))
s, j, h, _ = api('POST', '/ekle', None, A, raw=b'{"a":"' + b'x' * 5000 + b'"}'); check('büyük istek → 413', s == 413, (s, j))
s, j, h, _ = api('POST', '/ekle', {'alan': 'gida', 'marka': 'A', 'urun': 'B', 'dayanak': 'paket'}); check('şifresiz ekleme → 401', s == 401, (s, j))
s, j, h, _ = api('POST', '/cikar', {'id': 1}, H)
check('çıkar → 200, çıkaran heyybenbus', s == 200 and j['urun']['cikaran'] == 'heyybenbus' and j['urun']['cikarildi'].endswith('Z'), (s, j))
s, j, h, _ = api('POST', '/cikar', {'id': 1}, A); check('ikinci çıkarma → 404', s == 404, (s, j))
s, j, h, _ = api('GET', '/veri', key=H)
check('veri: 0 listede, 1 geçmişte (ekleyen korunur)', len(j['urunler']) == 0 and len(j['cikarilanlar']) == 1 and j['cikarilanlar'][0]['ekleyen'] == 'mayildiz', j)

# --- düzelt
s, j, h, _ = api('POST', '/ekle', {'alan': 'kozmetik', 'marka': 'Elidr', 'urun': 'Sampuan', 'dayanak': 'paket'}, H); e1 = j['urun']
s, j, h, _ = api('POST', '/ekle', {'alan': 'kozmetik', 'marka': 'Nivea', 'urun': 'Krem', 'dayanak': 'paket'}, A)
s, j, h, _ = api('POST', '/duzelt', {'id': e1['id'], 'alan': 'kozmetik', 'marka': 'Elidor', 'urun': 'Şampuan', 'dayanak': 'paket'}, A)
check('düzelt → eski kapanır, yeni kayıt eskisine bağlı', s == 200 and j['eski']['cikaran'] == 'mayildiz' and j['eski']['ekleyen'] == 'heyybenbus' and j['yeni']['onceki'] == e1['id'] and j['yeni']['ekleyen'] == 'mayildiz', (s, j))
yid = j['yeni']['id']
s, j, h, _ = api('POST', '/duzelt', {'id': e1['id'], 'alan': 'kozmetik', 'marka': 'X', 'urun': 'Y', 'dayanak': 'paket'}, A); check('kapanmış kaydı düzeltme → 404', s == 404, (s, j))
s, j, h, _ = api('POST', '/duzelt', {'id': yid, 'alan': 'kozmetik', 'marka': 'Elidor', 'urun': 'Şampuan', 'dayanak': 'paket'}, H); check('değişiklik yoksa → 400', s == 400 and 'Değişiklik' in j['hata'], (s, j))
s, j, h, _ = api('POST', '/duzelt', {'id': yid, 'alan': 'kozmetik', 'marka': 'NIVEA', 'urun': 'krem', 'dayanak': 'paket'}, H); check('başka ürünün adına düzeltme → 409', s == 409 and j['urun']['ekleyen'] == 'mayildiz', (s, j))
s, j, h, _ = api('GET', '/veri', key=A); check('409 sonrası hiçbir şey değişmedi', len(j['urunler']) == 2 and any(u['id'] == yid for u in j['urunler']), j)

# --- tepkiler
B = {'anahtar': 'u|1784', 'alan': 'gida', 'marka': 'Poco Loco', 'urun': 'Poco Loco Crispy'}
s, j, h, _ = api('POST', '/tepki', dict(B, favori=True), A)
check('favori → beğeni sayılır', s == 200 and j['tepki']['favori'] == 1 and j['tepki']['tepki'] == 'begen' and j['tepki']['kisi'] == 'mayildiz', (s, j))
s, j, h, _ = api('POST', '/tepki', dict(B, tepki='begenme', neden='çok tuzlu'), H)
check('beğenmedi + neden', s == 200 and j['tepki']['tepki'] == 'begenme' and j['tepki']['neden'] == 'çok tuzlu', (s, j))
s, j, h, _ = api('POST', '/tepki', dict(B, tepki='begenme', favori=True, neden='x'), H)
check('favori + beğenmedi gelirse favori kazanır, neden silinir', j['tepki']['tepki'] == 'begen' and j['tepki']['favori'] == 1 and j['tepki']['neden'] is None, (s, j))
s, j, h, _ = api('POST', '/tepki', dict(B, tepki=None), H)
check('tepki kaldırılınca kayıt silinir', s == 200 and j['tepki'] is None, (s, j))
for ad, k in [('eski metin anahtarı', 'l|gida|eti|1a2b3c4d'), ('sıfır', 'u|0'), ('harf', 'u|abc'), ('başka tür', 'x|1'), ('çok uzun', 'u|1234567890'), ('boş', '')]:
    s, j, h, _ = api('POST', '/tepki', dict(B, anahtar=k, tepki='begen'), A); check('geçersiz anahtar (' + ad + ') → 400', s == 400, (s, j))
s, j, h, _ = api('POST', '/tepki', dict(B, tepki='harika'), A); check('geçersiz tepki → 400', s == 400, (s, j))
s, j, h, _ = api('POST', '/tepki', dict(B, marka='', tepki='begen'), A); check('marka boş → 400', s == 400, (s, j))
s, j, h, _ = api('POST', '/tepki', dict(B, tepki='begen')); check('şifresiz tepki → 401', s == 401, (s, j))
s, j, h, _ = api('POST', '/tepki', {'anahtar': 'b|3', 'alan': 'kozmetik', 'marka': 'Elidor', 'urun': 'Şampuan', 'tepki': 'begen'}, H)
check('Bizim listemiz ürününe tepki (b|id)', s == 200 and j['tepki']['anahtar'] == 'b|3', (s, j))

# --- "bize dokundu" günlüğü
from datetime import datetime, timedelta, timezone
bugun = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
s, j, h, _ = api('POST', '/dokunma', dict(B, notu='2 saat sonra karın ağrısı', parti='L2611'), H)
d1 = (j or {}).get('dokunma') or {}
check('dokunma → 201, tarih bugün (Türkiye), kim sunucudan', s == 201 and d1.get('tarih') == bugun.isoformat() and d1.get('kisi') == 'heyybenbus' and d1.get('parti') == 'L2611', (s, j))
s, j, h, _ = api('POST', '/dokunma', dict(B, tarih=(bugun - timedelta(days=40)).isoformat()), A); d2 = j['dokunma']
check('geçmiş tarihle dokunma', s == 201 and d2['tarih'] == (bugun - timedelta(days=40)).isoformat() and d2['notu'] is None, (s, j))
for ad, t in [('ileri tarih', (bugun + timedelta(days=2)).isoformat()), ('olmayan gün', '2026-02-30'), ('biçim', '26.11.2026'), ('çok eski', '1999-12-31')]:
    s, j, h, _ = api('POST', '/dokunma', dict(B, tarih=t), A); check('dokunma: ' + ad + ' → 400', s == 400, (s, j))
s, j, h, _ = api('POST', '/dokunma', dict(B, notu='x' * 201), A); check('dokunma notu uzun → 400', s == 400, (s, j))
s, j, h, _ = api('POST', '/dokunma', dict(B)); check('şifresiz dokunma → 401', s == 401, (s, j))
s, j, h, _ = api('GET', '/veri', key=A)
check('veride dokunmalar yeniden eskiye', [d['id'] for d in j['dokunmalar']] == [d1['id'], d2['id']], j['dokunmalar'])
s, j, h, _ = api('POST', '/dokunma-sil', {'id': d1['id']}, A); check('başkasının kaydını silme → 403', s == 403, (s, j))
s, j, h, _ = api('POST', '/dokunma-sil', {'id': 999}, A); check('olmayan kayıt → 404', s == 404, (s, j))
s, j, h, _ = api('POST', '/dokunma-sil', {'id': 'abc'}, A); check('geçersiz id → 400', s == 400, (s, j))
s, j, h, _ = api('POST', '/dokunma-sil', {'id': d1['id']}, H); check('kendi kaydını silme → 200', s == 200 and j['silindi'] == d1['id'], (s, j))
s, j, h, _ = api('GET', '/veri', key=H); check('silinen kayıt yok, diğeri duruyor', [d['id'] for d in j['dokunmalar']] == [d2['id']], j['dokunmalar'])

# --- dokunmanın olası nedeni ve paket bilgisi
s, j, h, _ = api('POST', '/dokunma', dict(B, neden='bulasma', parti='L2611 · SKT 03.2027 · Üretici: Örnek Gıda A.Ş.'), H)
check('olası neden ve uzun paket bilgisi kaydedilir', s == 201 and j['dokunma']['neden'] == 'bulasma' and j['dokunma']['parti'].startswith('L2611 · SKT'), (s, j))
s, j, h, _ = api('POST', '/dokunma', dict(B, neden='uydurma'), H); check('geçersiz neden → 400', s == 400, (s, j))
s, j, h, _ = api('POST', '/dokunma', dict(B, parti='x' * 81), H); check('paket bilgisi 80 karakteri aşarsa → 400', s == 400, (s, j))
s, j, h, _ = api('POST', '/dokunma', dict(B), H); check('neden boş bırakılabilir', s == 201 and j['dokunma']['neden'] is None, (s, j))

# --- Bizim listemiz: "kontrol ettim"
s, j, h, _ = api('GET', '/veri', key=A); aktif = j['urunler'][0]['id']; kapali = j['cikarilanlar'][0]['id']
s, j, h, _ = api('POST', '/kontrol', {'id': aktif}, H)
check('kontrol ettim → 201, kim ve ne zaman sunucudan', s == 201 and j['kontrol']['urun'] == aktif and j['kontrol']['kisi'] == 'heyybenbus' and j['kontrol']['zaman'].endswith('Z'), (s, j))
s, j, h, _ = api('POST', '/kontrol', {'id': kapali}, A); check('listeden çıkmış ürün kontrol edilemez → 404', s == 404, (s, j))
s, j, h, _ = api('POST', '/kontrol', {'id': 'abc'}, A); check('geçersiz id → 400', s == 400, (s, j))
s, j, h, _ = api('POST', '/kontrol', {'id': aktif}); check('şifresiz kontrol → 401', s == 401, (s, j))
s, j, h, _ = api('POST', '/kontrol', {'id': aktif}, A)
s, j, h, _ = api('GET', '/veri', key=A)
check('veride kontroller yeniden eskiye, iki kişi ayrı', [(k['urun'], k['kisi']) for k in j['kontroller']] == [(aktif, 'mayildiz'), (aktif, 'heyybenbus')], j.get('kontroller'))

# --- CORS
s, j, h, _ = api('OPTIONS', '/veri', origin=KOKEN)
check('CORS ön kontrol (izinli köken)', s == 204 and h.get('Access-Control-Allow-Origin') == KOKEN and 'Authorization' in h.get('Access-Control-Allow-Headers', ''), h)
s, j, h, _ = api('OPTIONS', '/veri', origin='https://kotu.example'); check('CORS ön kontrol (izinsiz köken)', 'Access-Control-Allow-Origin' not in h, h)
s, j, h, _ = api('GET', '/veri', key=A, origin=KOKEN); check('veri: CORS ve önbelleğe alınmaz', h.get('Access-Control-Allow-Origin') == KOKEN and h.get('Cache-Control') == 'no-store', h)
s, j, h, _ = api('GET', '/yok', key=A); check('bilinmeyen adres → 404', s == 404, (s, j))
bitir()
