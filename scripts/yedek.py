#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kişisel kısmın (Bizim listemiz, tepkiler, "bize dokundu" kayıtları) haftalık şifreli yedeği.

Kullanım:
  python3 -I scripts/yedek.py al <sunucu_adresi> yedek/kisisel.enc   sunucudan alır; değiştiyse şifreleyip yazar
  python3 -I scripts/yedek.py ac yedek/kisisel.enc > kisisel.json      şifreyi çözer (geri yüklemek için)

Şifre YEDEK_SIFRE ortam değişkeninden okunur. Haftalık iş akışında bu, mayildiz'in şifresidir
(GitHub'daki ANAHTAR_1); sunucudan okumak da aynı şifreyle yapılır. Şifre değişirse eski yedekleri
açmak için eski şifre gerekir.

Şifreleme: scrypt (n=2^15, r=8, p=1) ile türetilen anahtar ve AES-256-GCM (bozulma da fark edilir).
Dosya herkese açık depoda durur; şifresiz okunamaz.
Çıkış kodu: 0 yazıldı ya da değişiklik yok · 2 şifre tanımlı değil (atlandı) · 1 hata.
"""
import base64
import json
import os
import sys
import urllib.parse
import urllib.request

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

N, R, P = 2 ** 15, 8, 1
ALANLAR = ('urunler', 'cikarilanlar', 'tepkiler', 'dokunmalar')


def anahtar(sifre, tuz, n=N, r=R, p=P):
    return Scrypt(salt=tuz, length=32, n=n, r=r, p=p).derive(sifre.encode('utf-8'))


def sifrele(duz, sifre):
    tuz, nonce = os.urandom(16), os.urandom(12)
    ct = AESGCM(anahtar(sifre, tuz)).encrypt(nonce, duz, b'glutensiz-kontrol/yedek/1')
    b = lambda x: base64.b64encode(x).decode('ascii')
    return json.dumps({'v': 1, 'kdf': 'scrypt', 'n': N, 'r': R, 'p': P, 'tuz': b(tuz), 'nonce': b(nonce), 'veri': b(ct)}, indent=1) + '\n'


def coz(metin, sifre):
    d = json.loads(metin)
    if d.get('v') != 1 or d.get('kdf') != 'scrypt':
        raise ValueError('bilinmeyen yedek biçimi')
    b = base64.b64decode
    k = anahtar(sifre, b(d['tuz']), d['n'], d['r'], d['p'])
    return AESGCM(k).decrypt(b(d['nonce']), b(d['veri']), b'glutensiz-kontrol/yedek/1')


def duz_metin(veri):
    """Yalnızca kayıtlar (sunucunun o anki saati hariç): veri değişmediyse yedek de değişmez."""
    if not isinstance(veri, dict) or not all(isinstance(veri.get(k), list) for k in ALANLAR):
        raise ValueError('sunucu yanıtı beklenen biçimde değil')
    return json.dumps({k: veri[k] for k in ALANLAR}, ensure_ascii=False, sort_keys=True, indent=1).encode('utf-8')


def al(api, yol, sifre):
    req = urllib.request.Request(api.rstrip('/') + '/veri', headers={
        'Authorization': 'Bearer ' + urllib.parse.quote(sifre.strip(), safe=''), 'User-Agent': 'glutensiz-kontrol-yedek'})
    with urllib.request.urlopen(req, timeout=60) as r:
        duz = duz_metin(json.loads(r.read()))
    if os.path.exists(yol):
        try:
            if coz(open(yol, encoding='utf-8').read(), sifre) == duz:
                print('Yedek güncel; değişiklik yok.')
                return
        except Exception:
            pass  # şifre değişmiş ya da dosya bozuk: yenisi yazılır
    os.makedirs(os.path.dirname(yol) or '.', exist_ok=True)
    with open(yol, 'w', encoding='utf-8') as f:
        f.write(sifrele(duz, sifre))
    v = json.loads(duz)
    print('Yedek yazıldı:', ', '.join(f'{len(v[k])} {k}' for k in ALANLAR))


def main():
    sifre = os.environ.get('YEDEK_SIFRE', '')
    if len(sys.argv) < 3 or sys.argv[1] not in ('al', 'ac'):
        print(__doc__)
        return 1
    if len(sifre.strip()) < 8:
        print('YEDEK_SIFRE tanımlı değil; yedek atlandı.')
        return 2
    try:
        if sys.argv[1] == 'al':
            al(sys.argv[2], sys.argv[3], sifre.strip())
        else:
            sys.stdout.write(coz(open(sys.argv[2], encoding='utf-8').read(), sifre.strip()).decode('utf-8'))
        return 0
    except Exception as e:
        print('Yedek hatası:', type(e).__name__, e, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
