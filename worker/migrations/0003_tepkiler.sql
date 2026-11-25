-- 0003: Tepkiler (26 Kasım 2026)
-- Her kişinin bir ürüne tepkisi: beğendi / beğenmedi, favori, "bize dokundu" ve isteğe bağlı notlar.
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
