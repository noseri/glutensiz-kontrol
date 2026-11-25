"""“Bizim listemiz”in haftalık yedeği: sunucudaki listeyi site/bizim.json dosyasına yazar.

Kullanım: python3 -I scripts/bizim_yedek.py <sunucu_adresi> site/bizim.json

- Sunucuya ulaşılamazsa ya da yanıt beklenen biçimde değilse dosyaya dokunmaz.
- Liste değişmediyse dosyayı yeniden yazmaz (yanıttaki "zaman" karşılaştırmaya girmez).
- Kayıtlar sunucuda hiç silinmediği için toplam kayıt sayısı azalamaz; birden yarıdan fazla
  azaldıysa (ör. veritabanı boş geldiyse) eski yedeği korur.
"""
import json
import sys
import urllib.request

ALANLAR = ['id', 'alan', 'marka', 'urun', 'kategori', 'dayanak', 'notu', 'ekleyen', 'eklendi', 'cikaran', 'cikarildi']


def temiz(satirlar):
    return [{k: s.get(k) for k in ALANLAR} for s in satirlar if isinstance(s, dict) and s.get('id') is not None]


def main():
    api, yol = sys.argv[1].rstrip('/'), sys.argv[2]
    try:
        istek = urllib.request.Request(api + '/liste', headers={'User-Agent': 'glutensiz-kontrol-yedek'})
        with urllib.request.urlopen(istek, timeout=20) as r:
            j = json.load(r)
    except Exception as e:  # ağ hatası, zaman aşımı, bozuk JSON
        print('Bizim listemiz yedeği alınamadı:', e)
        return
    if not isinstance(j, dict) or not isinstance(j.get('urunler'), list) or not isinstance(j.get('cikarilanlar'), list):
        print('Beklenmeyen yanıt; yedek güncellenmedi.')
        return
    yeni = {'urunler': temiz(j['urunler']), 'cikarilanlar': temiz(j['cikarilanlar'])}
    try:
        with open(yol, encoding='utf-8') as f:
            eski = json.load(f)
    except Exception:
        eski = {}
    if {'urunler': eski.get('urunler'), 'cikarilanlar': eski.get('cikarilanlar')} == yeni:
        print('Bizim listemiz değişmemiş.')
        return
    eski_n = len(eski.get('urunler') or []) + len(eski.get('cikarilanlar') or [])
    yeni_n = len(yeni['urunler']) + len(yeni['cikarilanlar'])
    if eski_n >= 3 and yeni_n < eski_n // 2:
        print(f'Kayıt sayısı {eski_n} → {yeni_n} düştü; olağan değil, yedek korunuyor.')
        return
    with open(yol, 'w', encoding='utf-8') as f:
        json.dump({'zaman': j.get('zaman'), **yeni}, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(f"Bizim listemiz yedeği güncellendi: {len(yeni['urunler'])} ürün, {len(yeni['cikarilanlar'])} çıkarılmış.")


if __name__ == '__main__':
    main()
