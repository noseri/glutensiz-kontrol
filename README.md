# Glutensiz Kontrol

İstanbul ve Ankara çölyak derneklerinin glutensiz onay listelerini tek aramada birleştiren, telefonda internetsiz de çalışan sayfa.

**Sayfa:** https://noseri.github.io/glutensiz-kontrol/

Her ürün satırı için iki listeye bakar:

- **Yeşil:** ürün iki listede de var.
- **Sarı:** yalnızca bir listede; paketi inceleyerek alın.
- **Kırmızı:** hiçbir listede yok.

İki listede olup “hariç, sadece, etiketi okunmalı” gibi bir şart taşıyan markalar **Şartlı** olarak işaretlenir.

## Telefona ekleme

- **iPhone:** Safari’de açın → Paylaş → *Ana Ekrana Ekle*
- **Android:** Chrome’da açın → menü → *Ana ekrana ekle* / *Uygulamayı yükle*

Bir kez açıldıktan sonra liste telefona kaydedilir. İnternet yoksa son kaydedilen liste gösterilir ve başlıkta “çevrimdışı” yazar.

## Güncelleme

Her pazartesi 10:33’te (Türkiye saati) GitHub Actions şunları yapar:

1. `scripts/fetch.py`: dernek sayfalarını WordPress veri arayüzünden çeker.
2. `scripts/update.py` + `scripts/pipeline.py`: satırları ayrıştırır, ürün düzeyinde eşleştirir, önceki listeyle karşılaştırır.
3. `scripts/apply.sh`: değişiklik varsa `site/data.json` dosyasını günceller, sayfayı yeniden yayınlar ve **degisiklik** etiketli bir issue açar. GitHub bunu e-postayla bildirir.

Bir kaynak alınamazsa ya da veri şüpheli görünürse sayfa olduğu gibi kalır ve issue açılır. “Son kontrol” tarihi yalnızca bütün kaynaklar alındığında ilerler.

Elle çalıştırmak için: **Actions → Haftalık liste kontrolü → Run workflow**.

## Kaynaklar

- Çölyakla Yaşam Derneği (İstanbul): [Glutensiz Gıdalar](https://colyak.org.tr/glutensiz-urunler/), [Glutensiz İlaçlar](https://colyak.org.tr/glutensiz-ilaclar/), [Makyaj ve Bakım](https://colyak.org.tr/glutensiz-sabun-sampuan-cilt-agiz-bakim-dis-macunlari-makyaj-urunleri-vb/), [Tıbbi Gıda Destekleri](https://colyak.org.tr/tibbi-gida-destekleri/)
- Çölyak Derneği (Ankara): [Glutensiz Yiyecek, İçecek ve İlaç Listesi](https://www.colyakankara.org.tr/glutensiz-ilac-ve-yiyecek-listesi)

Liste metinleri derneklere aittir ve sayfada olduğu gibi gösterilir. Bu sayfa onay vermez, yalnızca listeleri birleştirir. Dernekler, listede olsa bile ambalajdaki alerjen bilgisinin okunmasını önerir.

Sayfa arama motorlarına kapalıdır (`noindex`). Yazı tipi: Manrope (SIL Open Font License, `site/fonts/OFL.txt`).
