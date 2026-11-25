# Glutensiz Kontrol

İstanbul ve Ankara çölyak derneklerinin glutensiz onay listelerini tek aramada birleştiren, telefonda internetsiz de çalışan sayfa.

**Sayfa:** https://noseri.github.io/glutensiz-kontrol/

Her ürün satırı için iki listeye bakar:

- **Yeşil:** ürün iki listede de var.
- **Sarı:** yalnızca bir listede; paketi inceleyerek alın.
- **Kırmızı:** hiçbir listede yok.
- **Mavi (Bizim listemiz):** sizin eklediğiniz ürün. Dernek onayı değildir; kimin, ne zaman eklediği yazılıdır.

İki listede olup “hariç, sadece, etiketi okunmalı” gibi bir şart taşıyan markalar **Şartlı** olarak işaretlenir.

## Bizim listemiz (kendi eklediğimiz ürünler)

Derneklerde olmayan ama güvendiğiniz ürünleri uygulamadan ekleyebilirsiniz. Eklenen ürün mavi “Bizim listemiz” etiketiyle görünür; yeşil/sarı/kırmızı kararı değiştirmez.

- **Kim:** her kişinin kendi ekleme şifresi vardır. Hangi adın yazılacağını şifre belirler; uygulamadan ad gönderilmez.
- **Ne zaman:** tarih ve saat sunucunun saatidir.
- **Değiştirilemez kayıt:** satırlar silinmez. “Listeden çıkar” ürünü listeden kaldırır ama kaydı “Geçmiş” bölümünde, kimin ne zaman çıkardığıyla birlikte saklar. Veritabanındaki tetikleyiciler eklenme ve çıkarma kaydının sonradan düzenlenmesini engeller (`worker/schema.sql`).
- **Nerede:** Cloudflare Workers + D1 (ücretsiz katman), kodu `worker/`. Liste herkese açık olarak okunabilir; ekleme ve çıkarma şifre ister. Haftalık kontrol listenin bir yedeğini `site/bizim.json` olarak depoya da yazar.

### Bir kerelik kurulum

1. Cloudflare panelinde **Workers & Pages** sayfasını bir kez açın (hesabın `workers.dev` adresi böylece oluşur).
2. **My Profile → API Tokens → Create Token → “Edit Cloudflare Workers”** şablonu. *Account Resources* bölümünde yalnızca kendi hesabınızı seçin, oluşturun ve jetonu kopyalayın.
3. Depo → **Settings → Secrets and variables → Actions → New repository secret** ile üç gizli değer ekleyin:
   - `CLOUDFLARE_API_TOKEN`: 2. adımdaki jeton
   - `ANAHTAR_1`: birinci kişinin ekleme şifresi (en az 8 karakter; 3–4 kelimelik bir cümle iyi olur)
   - `ANAHTAR_2`: ikinci kişinin ekleme şifresi
4. **Actions → Bizim listemiz sunucusu → Run workflow.** Şifre değiştirmek için gizli değeri güncelleyip bu iş akışını yeniden çalıştırmak yeterli.

Görünen adlar `worker/wrangler.toml` içindeki `KISILER` satırındadır.

## Telefona ekleme

- **iPhone:** Safari’de açın → Paylaş → *Ana Ekrana Ekle*
- **Android:** Chrome’da açın → menü → *Ana ekrana ekle* / *Uygulamayı yükle*

Bir kez açıldıktan sonra liste telefona kaydedilir ve sonraki açılışlarda beklemeden telefondan gelir; internet varsa yenisi arka planda alınır, değiştiyse sayfa kendiliğinden yenilenir. İnternet yoksa başlıkta “çevrimdışı” yazar. Arama kutusu boşken son aramalar tek dokunuşla tekrarlanabilir.

## Güncelleme

Her pazartesi 10:33’te (Türkiye saati) GitHub Actions şunları yapar:

1. `scripts/fetch.py`: dernek sayfalarını WordPress veri arayüzünden çeker.
2. `scripts/update.py` + `scripts/pipeline.py`: satırları ayrıştırır, ürün düzeyinde eşleştirir, önceki listeyle karşılaştırır.
3. `scripts/apply.sh`: değişiklik varsa `site/data.json` dosyasını günceller, sayfayı yeniden yayınlar ve **degisiklik** etiketli bir issue açar. GitHub bunu e-postayla bildirir.

Bir kaynak alınamazsa ya da veri şüpheli görünürse sayfa olduğu gibi kalır ve issue açılır. “Son kontrol” tarihi yalnızca bütün kaynaklar alındığında ilerler.

Elle çalıştırmak için: **Actions → Haftalık liste kontrolü → Run workflow**.

## Telegram ya da anlık bildirim (isteğe bağlı)

E-posta bildirimi kendiliğinden çalışır. Değişiklikleri Telegram'dan da almak için:

1. Telegram'da **@BotFather** → `/newbot` ile bir bot oluşturun; size bir jeton (token) verir.
2. Bota bir mesaj yazın (ya da ikinizin olduğu bir gruba ekleyin). Sonra tarayıcıda `https://api.telegram.org/bot<JETON>/getUpdates` adresini açıp `"chat":{"id": …}` değerini not edin.
3. Depo → **Settings → Secrets and variables → Actions → New repository secret**: `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID`.
4. **Actions → Haftalık liste kontrolü → Run workflow** → “bildirim testi” kutusunu işaretleyip çalıştırın.

Telegram yerine ya da yanında `NOTIFY_WEBHOOK_URL` tanımlanabilir: mesaj bu adrese düz metin olarak gönderilir (ör. telefonda ntfy uygulamasıyla `https://ntfy.sh/<tahmin-edilmesi-zor-bir-ad>`).

## Kaynaklar

- Çölyakla Yaşam Derneği (İstanbul): [Glutensiz Gıdalar](https://colyak.org.tr/glutensiz-urunler/), [Glutensiz İlaçlar](https://colyak.org.tr/glutensiz-ilaclar/), [Makyaj ve Bakım](https://colyak.org.tr/glutensiz-sabun-sampuan-cilt-agiz-bakim-dis-macunlari-makyaj-urunleri-vb/), [Tıbbi Gıda Destekleri](https://colyak.org.tr/tibbi-gida-destekleri/)
- Çölyak Derneği (Ankara): [Glutensiz Yiyecek, İçecek ve İlaç Listesi](https://www.colyakankara.org.tr/glutensiz-ilac-ve-yiyecek-listesi)

Liste metinleri derneklere aittir ve sayfada olduğu gibi gösterilir. Bu sayfa onay vermez, yalnızca listeleri birleştirir. Dernekler, listede olsa bile ambalajdaki alerjen bilgisinin okunmasını önerir.

Sayfa arama motorlarına kapalıdır (`noindex`). Yazı tipi: Manrope (SIL Open Font License, `site/fonts/OFL.txt`).
