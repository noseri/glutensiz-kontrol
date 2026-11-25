-- Bizim listemiz: kendi eklediğimiz ürünler (Cloudflare D1 / SQLite).
-- Kayıtlar silinmez. "Listeden çıkar" yalnızca cikaran ve cikarildi alanlarını doldurur;
-- kimin, ne zaman eklediği sonradan değiştirilemez.
-- "Düzelt": eski kayıt çıkarılmış gibi kapanır, düzeltilmiş hali yeni kayıt olur (onceki = eski kaydın id'si).
-- Yeni kurulum için bu dosya yeterli; var olan veritabanı için migrations/ altındaki dosyalar sırayla uygulanır.

CREATE TABLE IF NOT EXISTS urunler (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  alan      TEXT NOT NULL CHECK (alan IN ('gida', 'ilac', 'kozmetik', 'takviye')),
  marka     TEXT NOT NULL,
  urun      TEXT NOT NULL,
  kategori  TEXT,
  dayanak   TEXT NOT NULL CHECK (dayanak IN ('paket', 'uretici', 'analiz', 'deneyim', 'diger')),
  notu      TEXT,
  ekleyen   TEXT NOT NULL,
  eklendi   TEXT NOT NULL,
  cikaran   TEXT,
  cikarildi TEXT,
  esas      TEXT NOT NULL,
  onceki    INTEGER REFERENCES urunler(id)
);

-- Aynı ürün listede iki kez durmasın (çıkarılanlar hariç).
CREATE UNIQUE INDEX IF NOT EXISTS urunler_esas_aktif ON urunler (esas) WHERE cikarildi IS NULL;

-- Eklenme kaydı değişmez.
CREATE TRIGGER IF NOT EXISTS urunler_ekleme_degismez
BEFORE UPDATE OF alan, marka, urun, kategori, dayanak, notu, ekleyen, eklendi, esas, onceki ON urunler
BEGIN
  SELECT RAISE(ABORT, 'Eklenme kaydı değiştirilemez.');
END;

-- Çıkarma kaydı da bir kez yazılır.
CREATE TRIGGER IF NOT EXISTS urunler_cikarma_degismez
BEFORE UPDATE OF cikaran, cikarildi ON urunler
WHEN OLD.cikarildi IS NOT NULL
BEGIN
  SELECT RAISE(ABORT, 'Çıkarma kaydı değiştirilemez.');
END;

-- Satır silinmez; ürün listeden çıkarılır.
CREATE TRIGGER IF NOT EXISTS urunler_silinmez
BEFORE DELETE ON urunler
BEGIN
  SELECT RAISE(ABORT, 'Kayıtlar silinmez; ürünü listeden çıkarın.');
END;

-- Tepkiler: her kişinin bir ürüne tepkisi: beğendi / beğenmedi, favori, "bize dokundu" ve isteğe bağlı notlar.
-- Bunlar değişebilen tercihlerdir (denetim kaydı değil): kişi tepkisini değiştirebilir ya da kaldırabilir.
-- Yalnızca şifreyle okunur; haftalık açık yedeğe yazılmaz.
CREATE TABLE IF NOT EXISTS tepkiler (
  anahtar       TEXT NOT NULL,        -- ürün anahtarı: 'l|alan|marka|metin özeti' (dernek satırı) ya da 'b|ilk kaydın id'si'
  kisi          TEXT NOT NULL,        -- görünen ad (şifreden)
  tepki         TEXT CHECK (tepki IN ('begen', 'begenme')),
  favori        INTEGER NOT NULL DEFAULT 0 CHECK (favori IN (0, 1)),
  dokundu       INTEGER NOT NULL DEFAULT 0 CHECK (dokundu IN (0, 1)),
  neden         TEXT,                 -- beğenmeme nedeni
  dokundu_notu  TEXT,                 -- ne oldu
  dokundu_zaman TEXT,                 -- "bize dokundu" ilk işaretlendiğinde
  alan          TEXT NOT NULL CHECK (alan IN ('gida', 'ilac', 'kozmetik', 'takviye')),
  marka         TEXT NOT NULL,        -- tepki anındaki ad: liste değişse de ne olduğu bilinsin
  urun          TEXT NOT NULL,
  zaman         TEXT NOT NULL,        -- son değişiklik (sunucu saati)
  PRIMARY KEY (anahtar, kisi),
  CHECK (favori = 0 OR tepki = 'begen')
);
