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
