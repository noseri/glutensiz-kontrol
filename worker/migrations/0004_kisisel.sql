-- 0004: Kişisel kısım (26 Kasım 2026)
-- Tepki anahtarları kalıcı ürün numarasına geçti ('u|<numara>'); "bize dokundu" aç/kapa işaret yerine
-- tarihli bir günlük oldu (dokunmalar). Tepkiler tablosu yayından birkaç dakika sonra, henüz boşken
-- yeniden kuruldu; taşınacak kayıt yoktu.
DROP TABLE IF EXISTS tepkiler;
-- Tepkiler: her kişinin bir ürüne tepkisi (beğendi / beğenmedi, favori) ve isteğe bağlı beğenmeme nedeni.
-- Değişebilen tercihlerdir (denetim kaydı değil): kişi tepkisini değiştirebilir ya da kaldırabilir.
-- Ürün anahtarı: 'u|<numara>' dernek satırı (haftalık derlemenin kalıcı numarası) ya da 'b|<ilk kaydın id'si>'.
-- Kişisel bilgi: yalnızca şifreyle okunur; herkese açık hiçbir yere yazılmaz.
CREATE TABLE IF NOT EXISTS tepkiler (
  anahtar TEXT NOT NULL,
  kisi    TEXT NOT NULL,              -- görünen ad (şifreden)
  tepki   TEXT NOT NULL CHECK (tepki IN ('begen', 'begenme')),
  favori  INTEGER NOT NULL DEFAULT 0 CHECK (favori IN (0, 1)),
  neden   TEXT,                       -- beğenmeme nedeni
  alan    TEXT NOT NULL CHECK (alan IN ('gida', 'ilac', 'kozmetik', 'takviye')),
  marka   TEXT NOT NULL,              -- tepki anındaki ad: liste değişse de ne olduğu bilinsin
  urun    TEXT NOT NULL,
  zaman   TEXT NOT NULL,              -- son değişiklik (sunucu saati)
  PRIMARY KEY (anahtar, kisi),
  CHECK (favori = 0 OR tepki = 'begen')
);

-- "Bize dokundu" günlüğü: her olay ayrı kayıt (ne zaman, kim, ne oldu, parti no).
-- Kişi yalnızca kendi kaydını silebilir.
CREATE TABLE IF NOT EXISTS dokunmalar (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  anahtar TEXT NOT NULL,
  kisi    TEXT NOT NULL,
  tarih   TEXT NOT NULL,              -- olayın günü (YYYY-AA-GG, Türkiye saati)
  notu    TEXT,
  parti   TEXT,                       -- parti / seri no
  alan    TEXT NOT NULL CHECK (alan IN ('gida', 'ilac', 'kozmetik', 'takviye')),
  marka   TEXT NOT NULL,
  urun    TEXT NOT NULL,
  zaman   TEXT NOT NULL               -- kaydedildiği an (sunucu saati)
);
CREATE INDEX IF NOT EXISTS dokunmalar_anahtar ON dokunmalar (anahtar);
