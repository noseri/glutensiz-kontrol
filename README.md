# Glutensiz Kontrol

İstanbul ve Ankara çölyak derneklerinin glutensiz onay listelerini tek aramada birleştiren, telefonda internetsiz de çalışan sayfa.

**Sayfa:** https://noseri.github.io/glutensiz-kontrol/

Her ürün satırı için iki listeye bakar:

- **Yeşil:** ürün iki listede de var.
- **Sarı:** yalnızca bir listede; paketi inceleyerek alın.
- **Kırmızı:** hiçbir listede yok.
- **Mavi (Bizim listemiz):** sizin eklediğiniz ürün. Dernek onayı değildir; kimin, ne zaman eklediği yazılıdır. Yalnızca giriş yapılmış telefonda görünür.

İki listede olup “hariç, sadece, etiketi okunmalı” gibi bir şart taşıyan markalar **Şartlı** olarak işaretlenir.

## Kişisel kısım: giriş

Bizim listemiz, tepkiler ve “bize dokundu” kayıtları kişiseldir; yalnızca şifresi girilmiş telefonda görünür. Herkese açık sayfada yalnızca dernek listeleri vardır: kişisel düğmeler, satırlara dokunma ve “Tepkilerimiz” şifresiz telefonda hiç görünmez.

- **Giriş:** ana sayfanın en altındaki “Bizim listemiz · giriş” bağlantısı. Şifre bir kez girilir, o telefonda saklanır.
- **Çıkış:** Bizim listemiz kartının altındaki “çıkış”. Şifre ve kişisel verilerin telefondaki kopyası silinir.
- Sunucu şifreyi tanımazsa (ör. şifre değiştirildiyse) telefon kendiliğinden çıkış yapar ve yeniden giriş ister.

## Bizim listemiz (kendi eklediğimiz ürünler)

Derneklerde olmayan ama güvendiğiniz ürünleri uygulamadan ekleyebilirsiniz. Eklenen ürün mavi “Bizim listemiz” etiketiyle görünür; yeşil/sarı/kırmızı kararı değiştirmez.

- **Kim:** her kişinin kendi ekleme şifresi vardır. Hangi adın yazılacağını şifre belirler; uygulamadan ad gönderilmez.
- **Ne zaman:** tarih ve saat sunucunun saatidir.
- **Düzeltme:** “Düzelt” ile yazım hatası ya da eksik bilgi tek adımda düzeltilir. Eski kayıt geçmişte “düzeltildi” olarak kalır; listede ilk ekleyen ve düzelten ayrı ayrı yazar.
- **Yeniden kontrol:** elle eklenen ürün 6 aydır kontrol edilmediyse yanında sarı “paketi yeniden okuyun” uyarısı çıkar, Bizim listemiz kartının başında da kaç ürünün zamanı geldiği yazar. Paketi okuyup **Kontrol ettim**’e dokununca kimin, ne zaman kontrol ettiği kaydedilir (bu kayıt da değiştirilemez); düzeltilen üründe eski hâline yapılan kontrol de sayılır.
- **Değiştirilemez kayıt:** satırlar silinmez. “Listeden çıkar” ürünü listeden kaldırır ama kaydı “Geçmiş” bölümünde, kimin ne zaman çıkardığıyla birlikte saklar. Veritabanındaki tetikleyiciler eklenme ve çıkarma kaydının sonradan düzenlenmesini engeller (`worker/schema.sql`).
- **Nerede:** Cloudflare Workers + D1 (ücretsiz katman), kodu `worker/`. Okuma da yazma da şifre ister.
- **Yedek:** haftalık kontrol kişisel kısmın tamamını (Bizim listemiz, tepkiler, dokunma kayıtları) **şifreleyerek** `yedek/kisisel.enc` dosyasına yazar; değişiklik yoksa dokunmaz. Dosya herkese açık depoda durur ama şifresiz okunamaz (scrypt + AES-256-GCM). Şifre mayildiz’in şifresidir (GitHub’daki `ANAHTAR_1`); şifre değişirse eski yedekleri açmak için eski şifre gerekir. Açmak için: `YEDEK_SIFRE='…' python3 scripts/yedek.py ac yedek/kisisel.enc > kisisel.json`

## Tepkiler (beğendim, beğenmedim, favori, bize dokundu)

Herhangi bir ürün satırına (dernek listesi ya da Bizim listemiz) dokununca küçük bir pencere açılır. Her kişi kendi tepkisini verir; satırda baş harfle görünür (♥ M · 👎 H), pencerede tam adla.

- **Beğendim / Beğenmedim / Favori:** beğendim ile beğenmedim birbirini dışlar; favori beğeni sayılır. Beğenmeme nedenine kısa bir not yazılabilir.
- **Bize dokundu (günlük):** listede olsa bile rahatsızlık yapan ürün için her olay ayrı kaydedilir: ne zaman, kim, ne oldu, **olası neden** (çapraz bulaşma şüphesi · gluten dışı bir şey ağır geldi: laktoz, gam, lif · aynı gün başka şüpheli bir şey yendi · bilmiyorum) ve **paket bilgisi** (parti no, son kullanma tarihi, üretici; market markalarını farklı fason firmalar üretebilir). Pencerede geçmiş listelenir (en yenisi üstte), herkes kendi kaydını silebilir. Ürünün satırında (“Dokundu 2 kez · …”) ve markanın kartında kırmızı uyarı olarak ikinizde de görünür.
- **Tat güvenlik değildir:** tepkiler yeşil/sarı/kırmızı kararı hiçbir zaman değiştirmez.
- **Ana sayfa:** “Tepkilerimiz” altında Dokunan, İkimiz de (ikinizin de beğendikleri, ortak alınacaklar için), Favori, Beğenilen ve Beğenilmeyen ürünler kimin ne dediğiyle listelenir. İki listedeki aynı ürüne verilen tepkiler tek satırda birleşir. Dernek listelerinden düşen bir ürün “Dernek listelerinde artık bu satır yok” uyarısıyla işaretlenir.
- **Kalıcı ürün numarası:** haftalık derleme her dernek satırına bir numara verir (`data.json` içinde `u`). Satırın yazımı değişirse (ör. gramaj eklenirse) numara korunur; tepkiler ve kayıtlar bu numaraya bağlıdır. Emin olunamayan değişikliklerde yeni numara verilir; numaralar hiç yeniden kullanılmaz (`scripts/pipeline.py` → `assign_uids`).

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

Bir kaynak alınamazsa ya da veri şüpheli görünürse sayfa olduğu gibi kalır ve issue açılır. “Son kontrol” tarihi yalnızca bütün kaynaklar alındığında ilerler. Telefondaki liste 2 haftadan eskiyse (uzun süre internetsiz kalındıysa ya da kontrol yapılamadıysa) başlıktaki tarih sarı görünür ve kaç gün olduğu yazar.

Elle çalıştırmak için: **Actions → Haftalık liste kontrolü → Run workflow**.

## Kod düzeni

- **Sayfa (`site/`):** `index.html` iskelet ve ilk açılışta görünen bölümler, `app.css` görünüm, `js/` altında konularına göre betikler. Betikler ortak bir kapsamda şu sırayla çalışır: `temel` (yardımcılar, durum) → `cevrimdisi` → `kisisel` (giriş, Bizim listemiz) → `ekle` (ekleme/düzeltme formu) → `veri` → `liste` (arama, marka kartları) → `tepki` → `gorunum` → `baslat`. Derleme adımı yoktur.
- **Sürüm damgası:** yayında `scripts/surum.sh` stil ve betik adreslerine sürüm ekler (`app.css?v=…`); `sw.js` her sürümün dosyalarını kendi önbelleğinde birlikte tutar, böylece telefonda eski ve yeni sürüm karışmaz.
- **Liste derleyici:** `scripts/pipeline.py` giriş noktasıdır; kod `scripts/derle/` paketindedir ve her katman yalnızca kendinden öncekileri kullanır: `metin` → `kategoriler` → `markalar` → `ortak` → `ayristir` (dernek sayfaları) → `zenginlestir` → `esles` (iki listeyi eşleştirme) → `cikti` (data.json, kalıcı numaralar).
- **Sunucu (`worker/`):** `src/index.js`, veritabanı şeması `schema.sql`, var olan veritabanı için sırayla uygulanan `migrations/`.

## Testler

Sayfa da sunucu da yayınlanmadan önce testlerden geçer (**Actions → Testler**); bir test bile kalırsa yayın yapılmaz, canlı sürüm olduğu gibi kalır. Haftalık güncelleme de bu kapıdan geçer.

- **Sunucu:** şifre ve gizlilik, ekleme/düzeltme/çıkarma, tepkiler, dokunma kayıtları, hatalı istekler.
- **İki telefon:** mayildiz ve heyybenbus aynı anda; giriş/çıkış, Bizim listemiz, tepkiler, dokunma günlüğü, çevrimdışı açılış, erişilebilirlik.
- **Kalıcı numara ve yedek:** yazımı değişen satırın numarasını koruması; şifreli yedeğin doğru açılması.
- Arayüz testleri sabit bir test verisiyle (`tests/veri/data.json`) çalışır, haftalık liste değişse de bozulmaz; gerçek liste ayrıca kısa bir duman testinden geçer.

Yerelde: `npm ci --prefix tests` ve `pip install playwright`, sonra `bash tests/calistir.sh` (tek bir test için adını ekleyin: `bash tests/calistir.sh test_tepki`).

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
