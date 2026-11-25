#!/usr/bin/env python3
"""Şifreli haftalık yedek (scripts/yedek.py): boş veritabanıyla başlar."""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import api, check, bitir, A, H, API, KOK

T = tempfile.mkdtemp(); Y = os.path.join(T, 'yedek', 'kisisel.enc')
def calis(*args, sifre=A):
    env = dict(os.environ); env.pop('YEDEK_SIFRE', None)
    if sifre is not None: env['YEDEK_SIFRE'] = sifre
    r = subprocess.run([sys.executable, '-I', os.path.join(KOK, 'scripts', 'yedek.py')] + list(args), env=env, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr

api('POST', '/ekle', {'alan': 'kozmetik', 'marka': 'Elidor', 'urun': 'Şampuan', 'dayanak': 'paket'}, H)
api('POST', '/tepki', {'anahtar': 'u|1784', 'alan': 'gida', 'marka': 'Poco Loco', 'urun': 'Poco Loco Crispy', 'favori': True}, A)
api('POST', '/dokunma', {'anahtar': 'u|1784', 'alan': 'gida', 'marka': 'Poco Loco', 'urun': 'Poco Loco Crispy', 'notu': 'karın ağrısı', 'parti': 'L2611'}, H)

kod, out, err = calis('al', API, Y)
check('yedek alındı', kod == 0 and os.path.exists(Y) and 'Yedek yazıldı' in out, (kod, out, err))
icerik = open(Y, encoding='utf-8').read()
d = json.loads(icerik)
check('dosyada açık metin yok (şifreli)', all(x not in icerik for x in ('Elidor', 'karın', 'L2611', 'heyybenbus', 'mayildiz')) and d['v'] == 1 and d['kdf'] == 'scrypt', icerik[:200])
kod, out, err = calis('ac', Y)
v = json.loads(out) if kod == 0 else {}
s, j, _, _ = api('GET', '/veri', key=A)
check('açılan yedek sunucudaki kayıtların aynısı', kod == 0 and all(v.get(k) == j[k] for k in ('urunler', 'cikarilanlar', 'tepkiler', 'dokunmalar')), (kod, err, list(v)))
once = open(Y, 'rb').read()
kod, out, err = calis('al', API, Y)
check('değişiklik yoksa dosyaya dokunmaz', kod == 0 and 'değişiklik yok' in out and open(Y, 'rb').read() == once, (kod, out, err))
api('POST', '/tepki', {'anahtar': 'u|1784', 'alan': 'gida', 'marka': 'Poco Loco', 'urun': 'Poco Loco Crispy', 'tepki': 'begenme'}, H)
kod, out, err = calis('al', API, Y)
check('yeni kayıt olunca yedek yenilenir', kod == 0 and 'Yedek yazıldı' in out and open(Y, 'rb').read() != once, (kod, out))
kod, out, err = calis('ac', Y, sifre='baska-bir-sifre-123')
check('yanlış şifreyle açılmaz', kod == 1 and 'InvalidTag' in err, (kod, err))
kod, out, err = calis('al', API, Y, sifre=None)
check('şifre tanımlı değilse atlanır (2)', kod == 2 and 'atlandı' in out, (kod, out))
kod, out, err = calis('al', API, os.path.join(T, 'x.enc'), sifre='yanlis-sifre-000')
check('sunucu şifreyi tanımazsa hata (1), dosya yazılmaz', kod == 1 and not os.path.exists(os.path.join(T, 'x.enc')), (kod, err))
bitir()
